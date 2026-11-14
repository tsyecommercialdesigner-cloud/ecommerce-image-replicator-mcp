"""Offline scheduling, artifact tampering and release replay regressions."""

import importlib.util
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ci_policy", ROOT / "scripts/ci_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


@pytest.mark.parametrize(
    ("paths", "diff", "mode"),
    [
        (["README.md"], "+release published", "docs"),
        (["MANUAL.md"], "+uv sync --locked", "full"),
        (["README.md"], "+```powershell", "full"),
        (["docs/hosts/codex.toml"], "", "full"),
        (["src/image_replicator/network.py"], "", "light"),
        (["tests/test_network.py"], "", "light"),
        (["uv.lock"], "", "full"),
        ([".github/workflows/ci.yml"], "", "full"),
        (["scripts/ci_policy.py"], "", "full"),
        (["unknown.bin"], "", "full"),
    ],
)
def test_scope(paths, diff, mode):
    assert policy.classify(paths, diff) == mode


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    folder = tmp_path / "bundle"
    folder.mkdir()
    names = [
        "ecommerce_image_replicator_mcp-0.1.8-py3-none-any.whl",
        "ecommerce_image_replicator_mcp-0.1.8.tar.gz",
    ]
    for name in names:
        (folder / name).write_bytes(b"tested package")
    policy.save(
        folder / "candidate.json",
        {
            "schema": 1,
            "version": "0.1.8",
            "repository": "owner/repo",
            "tree": "a" * 40,
            "source_commit": "b" * 40,
            "run_id": 11,
            "run_attempt": 1,
            "pr_number": 7,
            "head_commit": "c" * 40,
            "files": {n: policy.sha(folder / n) for n in names},
        },
    )
    return folder


def test_confirm_reuses_exact_bytes_despite_merge_sha(bundle, monkeypatch):
    before = {p.name: p.read_bytes() for p in bundle.glob("*.whl")}
    monkeypatch.setenv("GITHUB_SHA", "d" * 40)
    monkeypatch.setenv("GITHUB_RUN_ID", "22")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setattr(policy, "git", lambda *a: "a" * 40)
    policy.confirm(bundle)
    policy.verify_bundle(bundle, "a" * 40, confirmed=True)
    assert before == {p.name: p.read_bytes() for p in bundle.glob("*.whl")}
    assert (bundle / "SOURCE_COMMIT").read_text().strip() == "d" * 40


@pytest.mark.parametrize("fault", ["payload", "extra", "tree", "repository", "version", "symlink"])
def test_candidate_tampering_rejected(bundle, monkeypatch, fault):
    if fault == "payload":
        next(bundle.glob("*.whl")).write_bytes(b"different")
    elif fault == "extra":
        (bundle / "extra.py").write_text("untrusted")
    elif fault == "repository":
        monkeypatch.setenv("GITHUB_REPOSITORY", "different/repo")
    elif fault == "version":
        m = json.loads((bundle / "candidate.json").read_text())
        m["version"] = "../../outside"
        policy.save(bundle / "candidate.json", m)
    elif fault == "symlink":
        p = next(bundle.glob("*.whl"))
        monkeypatch.setattr(Path, "is_symlink", lambda self: self == p)
    with pytest.raises(ValueError):
        policy.verify_bundle(bundle, "e" * 40 if fault == "tree" else "a" * 40)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "folder/file", "back\\slash"])
def test_unsafe_archive(tmp_path, name):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(name, "x")
    with pytest.raises(ValueError):
        policy.safe_extract(archive, tmp_path / "unpacked")


@pytest.mark.parametrize("fault", ["failed", "fork", "workflow", "expired", "archive_digest"])
def test_download_provenance(tmp_path, monkeypatch, fault):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    record = {
        "repository": {"full_name": "owner/repo"},
        "path": ".github/workflows/ci.yml",
        "status": "completed",
        "conclusion": "success",
        "run_attempt": 1,
    }
    if fault == "failed":
        record["conclusion"] = "failure"
    if fault == "fork":
        record["repository"]["full_name"] = "fork/repo"
    if fault == "workflow":
        record["path"] = ".github/workflows/other.yml"
    asset = {
        "id": 1,
        "name": "release-candidate-1",
        "expired": fault == "expired",
        "digest": "sha256:wrong",
    }
    monkeypatch.setattr(
        policy, "api", lambda p: {"artifacts": [asset]} if "artifacts?" in p else record
    )

    def download(*args, **kwargs):
        kwargs["stdout"].write(b"bad digest")

    monkeypatch.setattr(policy.subprocess, "run", download)
    with pytest.raises(ValueError):
        policy.download(11, "release-candidate", tmp_path / "received")
    assert not (tmp_path / "received").exists()


def event_env(tmp_path, monkeypatch, target="dev", head="feature/network", labels=None):
    event = {
        "number": 7,
        "pull_request": {
            "base": {"ref": target, "sha": "0" * 40},
            "head": {"ref": head, "sha": "c" * 40, "repo": {"full_name": "owner/repo"}},
            "labels": [{"name": x} for x in labels or []],
        },
    }
    path = tmp_path / "event.json"
    path.write_text(json.dumps(event))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(path))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(policy, "git", lambda *a: "")
    result = {}
    monkeypatch.setattr(policy, "output", lambda **values: result.update(values))
    return result, event, path


@pytest.mark.parametrize(
    ("target", "head", "paths", "labels", "mode"),
    [
        ("dev", "feature/doc", ["README.md"], [], "docs"),
        ("dev", "feature/network", ["src/image_replicator/network.py"], [], "light"),
        ("main", "dev", ["README.md"], [], "full"),
        ("main", "dev", ["README.md"], ["delivery-docs"], "docs"),
        ("main", "dev", ["uv.lock"], ["delivery-docs"], "full"),
    ],
)
def test_pr_routes(tmp_path, monkeypatch, target, head, paths, labels, mode):
    result, _, _ = event_env(tmp_path, monkeypatch, target, head, labels)
    monkeypatch.setattr(policy, "changed", lambda *a: paths)
    policy.plan()
    assert result["mode"] == mode
    assert result["candidate"] == str(target == "main" and mode == "full").lower()


def test_feature_cannot_enter_main(tmp_path, monkeypatch):
    event_env(tmp_path, monkeypatch, "main", "feature/bypass")
    monkeypatch.setattr(policy, "changed", lambda *a: ["README.md"])
    with pytest.raises(ValueError, match="only accepts"):
        policy.plan()


def test_main_reuse_without_full_suite(tmp_path, monkeypatch):
    result, _, path = event_env(tmp_path, monkeypatch)
    path.write_text(json.dumps({"before": "b" * 40}))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setattr(policy, "find_candidate", lambda *a: True)
    policy.plan()
    assert result == {"mode": "reuse", "candidate": "true"}


def test_main_missing_candidate_falls_back_full(tmp_path, monkeypatch):
    result, _, path = event_env(tmp_path, monkeypatch)
    path.write_text(json.dumps({"before": "b" * 40}))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", "d" * 40)
    monkeypatch.setattr(policy, "find_candidate", lambda *a: False)
    monkeypatch.setattr(policy, "api", lambda *a: [])
    monkeypatch.setattr(policy, "changed", lambda *a: ["README.md"])
    policy.plan()
    assert result == {"mode": "full", "candidate": "true"}


def test_only_single_cd_entry_and_stable_gate():
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    release = (ROOT / ".github/workflows/release.yml").read_text()
    assert "branches: [main]" in ci and "branches: [main, dev]" not in ci
    assert "name: CI gate" in ci and "if: always()" in ci
    assert "workflow_dispatch:" in release
    assert "  push:" not in release and "  release:" not in release
    assert "uv build" not in release and "contents: write" in release
    assert "environment: release" in release and "cancel-in-progress: false" in release


def test_published_release_not_overwritten(bundle, monkeypatch):
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", "d" * 40)
    monkeypatch.setenv("GITHUB_RUN_ID", "22")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setattr(policy, "git", lambda *a: "a" * 40)
    policy.confirm(bundle)
    monkeypatch.setattr(
        policy,
        "download",
        lambda *a: {"event": "push", "head_branch": "main", "head_sha": "d" * 40, "run_attempt": 1},
    )
    monkeypatch.setattr(policy, "git", lambda *a: "a" * 40 if "rev-parse" in a else "")
    monkeypatch.setattr(policy, "api", lambda *a: [{"tag_name": "v0.1.8", "draft": False}])
    monkeypatch.setattr(policy, "run", lambda *a: pytest.fail("No mutation allowed"))
    with pytest.raises(ValueError, match="already published"):
        policy.publish(bundle, "v0.1.8", 22)


def test_non_main_dispatch_rejected(bundle, monkeypatch):
    monkeypatch.setenv("GITHUB_REF", "refs/heads/dev")
    with pytest.raises(ValueError, match="Dispatch"):
        policy.publish(bundle, "v0.1.8", 22)


@pytest.mark.parametrize("mismatch", [False, True])
def test_draft_resume_uploads_only_missing_verified_assets(bundle, monkeypatch, mismatch):
    monkeypatch.setattr(policy, "ROOT", bundle.parent)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", "d" * 40)
    monkeypatch.setenv("GITHUB_RUN_ID", "22")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setattr(policy, "git", lambda *a: "a" * 40)
    policy.confirm(bundle)
    monkeypatch.setattr(
        policy,
        "download",
        lambda *a: {"event": "push", "head_branch": "main", "head_sha": "d" * 40, "run_attempt": 1},
    )
    monkeypatch.setattr(policy, "git", lambda *a: "a" * 40 if "rev-parse" in a else "")
    wheel = next(bundle.glob("*.whl"))
    existing = {
        "tag_name": "v0.1.8",
        "draft": True,
        "target_commitish": "d" * 40,
        "assets": [
            {"name": wheel.name, "digest": "sha256:" + ("wrong" if mismatch else policy.sha(wheel))}
        ],
    }
    monkeypatch.setattr(policy, "api", lambda *a: [existing])
    commands = []

    def fake_run(*args):
        commands.append(args)
        if args[:3] == ("gh", "release", "upload"):
            path = Path(args[4])
            existing["assets"].append({"name": path.name, "digest": "sha256:" + policy.sha(path)})
        return ""

    monkeypatch.setattr(policy, "run", fake_run)
    if mismatch:
        with pytest.raises(ValueError, match="differs"):
            policy.publish(bundle, "v0.1.8", 22)
        assert commands == []
    else:
        policy.publish(bundle, "v0.1.8", 22)
        uploaded = [Path(c[4]).name for c in commands if c[2] == "upload"]
        assert wheel.name not in uploaded and len(uploaded) == 5
        assert commands[-1][:3] == ("gh", "release", "edit")
        assert all("--clobber" not in c for c in commands)


def test_main_delivery_docs_remains_light(tmp_path, monkeypatch):
    result, event, path = event_env(tmp_path, monkeypatch, "main", "dev", ["delivery-docs"])
    pr = event["pull_request"]
    pr.update(merged_at="2026-11-14", merge_commit_sha="d" * 40)
    path.write_text(json.dumps({"before": "b" * 40}))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", "d" * 40)
    monkeypatch.setattr(policy, "find_candidate", lambda *a: False)
    monkeypatch.setattr(policy, "api", lambda *a: [pr])
    monkeypatch.setattr(policy, "changed", lambda *a: ["README.md"])
    policy.plan()
    assert result == {"mode": "docs", "candidate": "false"}


@pytest.mark.parametrize("fault", [None, "tree", "pr", "head", "attempt", "foreign"])
def test_merged_pr_candidate_binding(bundle, monkeypatch, fault):
    monkeypatch.setenv("GITHUB_SHA", "d" * 40)
    pr = {
        "number": 7,
        "merged_at": "2026-11-14",
        "merge_commit_sha": "d" * 40,
        "base": {"ref": "main"},
        "head": {"ref": "dev", "sha": "c" * 40, "repo": {"full_name": "owner/repo"}},
    }
    record = {"id": 11, "run_attempt": 1, "head_repository": {"full_name": "owner/repo"}}
    if fault == "foreign":
        record["head_repository"]["full_name"] = "fork/repo"
    m = json.loads((bundle / "candidate.json").read_text())
    if fault in {"tree", "head"}:
        m["tree" if fault == "tree" else "head_commit"] = "e" * 40
    if fault in {"pr", "attempt"}:
        m["pr_number" if fault == "pr" else "run_attempt"] = 99
    policy.save(bundle / "candidate.json", m)
    monkeypatch.setattr(policy, "git", lambda *a: "a" * 40)
    monkeypatch.setattr(
        policy, "api", lambda p: {"workflow_runs": [record]} if "actions/" in p else [pr]
    )
    monkeypatch.setattr(policy, "download", lambda *a: record)
    assert policy.find_candidate({}, bundle) == (fault is None)


def test_confirmation_tampering(bundle, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "d" * 40)
    monkeypatch.setenv("GITHUB_RUN_ID", "22")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setattr(policy, "git", lambda *a: "a" * 40)
    policy.confirm(bundle)
    (bundle / "SOURCE_COMMIT").write_text("e" * 40)
    with pytest.raises(ValueError):
        policy.verify_bundle(bundle, confirmed=True)


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["src/image_replicator/network.py"], "tests/test_network.py"),
        (["src/image_replicator/workflow_v2.py"], "tests"),
        (["tests/conftest.py"], "tests"),
    ],
)
def test_related_tests_conservative(paths, expected):
    checks_spec = importlib.util.spec_from_file_location("ci_checks", ROOT / "scripts/ci_checks.py")
    checks = importlib.util.module_from_spec(checks_spec)
    checks_spec.loader.exec_module(checks)
    assert expected in checks.related(paths)


@pytest.mark.parametrize("content", ["[broken](absent.md)", "```json\n{bad}\n```", "```json\n{}"])
def test_document_failures(tmp_path, monkeypatch, content):
    checks_spec = importlib.util.spec_from_file_location("ci_checks", ROOT / "scripts/ci_checks.py")
    checks = importlib.util.module_from_spec(checks_spec)
    checks_spec.loader.exec_module(checks)
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    monkeypatch.setattr(checks, "command", lambda *a: None)
    (tmp_path / "example.md").write_text(content)
    with pytest.raises(ValueError):
        checks.documents(["example.md"])


def test_real_git_tree_reuse_across_distinct_commits(bundle, tmp_path, monkeypatch):
    repo = tmp_path / "git-fixture"
    repo.mkdir()

    def g(*args, input=None):
        return (
            subprocess.check_output(
                [
                    "git",
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    *args,
                ],
                cwd=repo,
                input=input,
            )
            .decode()
            .strip()
        )

    g("init", "--quiet")
    (repo / "source.txt").write_text("same verified inputs")
    g("add", "source.txt")
    tree = g("write-tree")
    first = g("commit-tree", tree, input=b"candidate\n")
    merged = g("commit-tree", tree, "-p", first, input=b"merge confirmation\n")
    assert first != merged
    g("update-ref", "HEAD", merged)
    monkeypatch.setattr(policy, "CHECKOUT", repo)
    manifest = json.loads((bundle / "candidate.json").read_text())
    manifest.update(tree=tree, source_commit=first)
    policy.save(bundle / "candidate.json", manifest)
    monkeypatch.setenv("GITHUB_SHA", merged)
    monkeypatch.setenv("GITHUB_RUN_ID", "22")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    policy.confirm(bundle)
    assert policy.verify_bundle(bundle, tree, confirmed=True)["source_commit"] == first
    (repo / "source.txt").write_text("changed input")
    g("add", "source.txt")
    different = g("write-tree")
    with pytest.raises(ValueError, match="content differs"):
        policy.verify_bundle(bundle, different, confirmed=True)
