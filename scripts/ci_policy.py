"""Content-based CI planning and fail-closed candidate provenance; no provider calls."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = ROOT


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd or CHECKOUT, timeout=120).decode().strip()


def git(*args):
    return run("git", *args)


def api(path):
    return json.loads(run("gh", "api", path))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def changed(base, head="HEAD"):
    return git("diff", "--name-only", "--no-renames", base, head).splitlines()


def classify(paths, diff=""):
    """Unknown inputs and shared build/security infrastructure receive full acceptance."""
    if not paths:
        return "docs"
    if all(p.endswith(".md") or p.startswith("docs/hosts/") for p in paths):
        if any(p.startswith("docs/hosts/") for p in paths) or re.search(
            r"(?im)^[+-].*(?:```(?:powershell|bash|zsh|python|shell)|\buv\s|\bpip\s|"
            r"\bnpm\s|--project-root|--workspace|mcpServers)",
            diff,
        ):
            return "full"
        return "docs"
    if any(
        p.startswith((".github/", "scripts/"))
        or p
        in {
            "pyproject.toml",
            "uv.lock",
            ".python-version",
            ".gitignore",
        }
        for p in paths
    ):
        return "full"
    if all(p.startswith(("src/image_replicator/", "tests/")) or p.endswith(".md") for p in paths):
        return "light"
    return "full"


def output(**values):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            for key, value in values.items():
                handle.write(f"{key}={value}\n")
    print(json.dumps(values))


def safe_extract(archive, destination):
    """Candidates contain only flat regular files; never extract links or executable code."""
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) > 8:
            raise ValueError("Invalid candidate archive entries")
        for item in z.infolist():
            p = PurePosixPath(item.filename)
            mode = item.external_attr >> 16
            if (
                len(p.parts) != 1
                or p.is_absolute()
                or "\\" in item.filename
                or (mode & 0o170000 == 0o120000)
                or item.file_size > 20_000_000
            ):
                raise ValueError("Unsafe candidate archive")
            (destination / item.filename).write_bytes(z.read(item))


def download(run_id, name, destination, *, completed=True):
    repo = os.environ["GITHUB_REPOSITORY"]
    record = api(f"repos/{repo}/actions/runs/{int(run_id)}")
    if record["repository"]["full_name"] != repo or record["path"] != ".github/workflows/ci.yml":
        raise ValueError("Untrusted candidate workflow")
    if completed and (record["status"] != "completed" or record["conclusion"] != "success"):
        raise ValueError("Candidate workflow did not pass")
    if not completed and str(run_id) != os.environ["GITHUB_RUN_ID"]:
        raise ValueError("Only current in-progress workflow is allowed")
    artifacts = api(f"repos/{repo}/actions/runs/{int(run_id)}/artifacts?per_page=100")
    artifact_name = f"{name}-{record['run_attempt']}"
    found = [a for a in artifacts["artifacts"] if a["name"] == artifact_name and not a["expired"]]
    if len(found) != 1:
        raise ValueError("Candidate missing, expired or ambiguous")
    archive = destination.with_suffix(".zip")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("wb") as handle:
        subprocess.run(
            ["gh", "api", f"repos/{repo}/actions/artifacts/{found[0]['id']}/zip"],
            stdout=handle,
            check=True,
            timeout=120,
        )
    try:
        digest = found[0].get("digest")
        if not digest or digest != "sha256:" + sha(archive):
            raise ValueError("Artifact archive digest mismatch")
        safe_extract(archive, destination)
    finally:
        archive.unlink(missing_ok=True)
    return record


def verify_bundle(directory, tree=None, confirmed=False):
    manifest = json.loads((directory / "candidate.json").read_text())
    if manifest["schema"] != 1 or manifest["repository"] != os.environ["GITHUB_REPOSITORY"]:
        raise ValueError("Candidate identity mismatch")
    if tree is not None and manifest["tree"] != tree:
        raise ValueError("Candidate content differs")
    version = manifest["version"]
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid candidate version")
    for key in ("tree", "source_commit"):
        if not re.fullmatch(r"[a-f0-9]{40}", manifest[key]):
            raise ValueError("Invalid candidate Git identity")
    expected = {
        f"ecommerce_image_replicator_mcp-{version}-py3-none-any.whl",
        f"ecommerce_image_replicator_mcp-{version}.tar.gz",
    }
    if set(manifest["files"]) != expected:
        raise ValueError("Unexpected candidate payload")
    for name, digest in manifest["files"].items():
        path = directory / name
        if path.is_symlink() or sha(path) != digest:
            raise ValueError("Candidate payload digest mismatch")
    names = expected | {"candidate.json"}
    if confirmed:
        names |= {"confirmation.json", "SHA256SUMS", "SOURCE_COMMIT"}
        c = json.loads((directory / "confirmation.json").read_text())
        if c["schema"] != 1 or not re.fullmatch(r"[a-f0-9]{40}", c["target"]):
            raise ValueError("Invalid confirmation identity")
        if (
            c["candidate_sha256"] != sha(directory / "candidate.json")
            or c["tree"] != manifest["tree"]
        ):
            raise ValueError("Confirmation mismatch")
        if (directory / "SOURCE_COMMIT").read_text().strip() != c["target"]:
            raise ValueError("Source target mismatch")
        sums = "".join(f"{sha(directory / n)}  {n}\n" for n in sorted(names - {"SHA256SUMS"}))
        if (directory / "SHA256SUMS").read_text() != sums:
            raise ValueError("Release checksum manifest differs")
    if {p.name for p in directory.iterdir()} != names:
        raise ValueError("Unexpected or missing bundle files")
    return manifest


def package(directory):
    files = list(directory.iterdir())
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    pr = event.get("pull_request", {})
    save(
        directory / "candidate.json",
        {
            "schema": 1,
            "repository": os.environ["GITHUB_REPOSITORY"],
            "source_commit": git("rev-parse", "HEAD"),
            "tree": git("rev-parse", "HEAD^{tree}"),
            "version": version,
            "run_id": int(os.environ["GITHUB_RUN_ID"]),
            "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
            "pr_number": event.get("number"),
            "head_commit": pr.get("head", {}).get("sha"),
            "python": sys.version,
            "uv": run("uv", "--version"),
            "lock_sha256": sha(ROOT / "uv.lock"),
            "files": {p.name: sha(p) for p in files},
        },
    )
    verify_bundle(directory, git("rev-parse", "HEAD^{tree}"))


def find_candidate(event, directory):
    """Only the just-merged, same-repository dev release PR can donate a candidate."""
    repo = os.environ["GITHUB_REPOSITORY"]
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    hatch = project.get("tool", {}).get("hatch", {})
    if (
        project["build-system"]["build-backend"] != "hatchling.build"
        or project["project"].get("dynamic")
        or hatch.get("version")
        or hatch.get("build", {}).get("hooks")
        or any(t.get("hooks") for t in hatch.get("build", {}).get("targets", {}).values())
    ):
        return False  # Unknown/VCS-derived build identity cannot reuse a different merge SHA.
    target = os.environ["GITHUB_SHA"]
    prs = api(f"repos/{repo}/commits/{target}/pulls?per_page=100")
    prs = [
        p
        for p in prs
        if p["merged_at"]
        and p["merge_commit_sha"] == target
        and p["base"]["ref"] == "main"
        and p["head"]["ref"] == "dev"
        and p["head"]["repo"]
        and p["head"]["repo"]["full_name"] == repo
    ]
    if len(prs) != 1:
        return False
    pr = prs[0]
    runs = api(
        f"repos/{repo}/actions/workflows/ci.yml/runs?event=pull_request"
        f"&head_sha={pr['head']['sha']}&status=success&per_page=100"
    )
    for record in runs["workflow_runs"]:
        if record.get("head_repository", {}).get("full_name") != repo:
            continue
        try:
            download(record["id"], "release-candidate", directory)
            m = verify_bundle(directory, git("rev-parse", "HEAD^{tree}"))
            if (
                m["run_id"] != record["id"]
                or m["run_attempt"] != record["run_attempt"]
                or m["pr_number"] != pr["number"]
                or (m["head_commit"] != pr["head"]["sha"])
            ):
                raise ValueError("Candidate PR provenance mismatch")
            return True
        except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError):
            # Local download only, under .cache; no stale partial payload can be used.
            if directory.exists():
                shutil.rmtree(directory)
    return False


def plan():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    kind = os.environ["GITHUB_EVENT_NAME"]
    if kind == "pull_request":
        pr = event["pull_request"]
        base = pr["base"]["sha"]
        paths = changed(base)
        mode = classify(paths, git("diff", base, "HEAD", "--", "*.md"))
        target = pr["base"]["ref"]
        head = pr["head"]["ref"]
        if target == "dev" and not head.startswith("feature/"):
            raise ValueError("Integration PR must originate from feature/*")
        if target == "main":
            if head != "dev" or pr["head"]["repo"]["full_name"] != os.environ["GITHUB_REPOSITORY"]:
                raise ValueError("main only accepts this repository's dev")
            delivery = any(label["name"] == "delivery-docs" for label in pr["labels"])
            mode = "docs" if delivery and mode == "docs" else "full"
        output(mode=mode, candidate=str(target == "main" and mode == "full").lower())
    elif kind == "push" and os.environ["GITHUB_REF"] == "refs/heads/main":
        if find_candidate(event, ROOT / ".cache/ci/reused"):
            output(mode="reuse", candidate="true")
        else:
            repo = os.environ["GITHUB_REPOSITORY"]
            prs = api(f"repos/{repo}/commits/{os.environ['GITHUB_SHA']}/pulls?per_page=100")
            delivery = any(
                p["merged_at"]
                and p["merge_commit_sha"] == os.environ["GITHUB_SHA"]
                and p["base"]["ref"] == "main"
                and p["head"]["ref"] == "dev"
                and p["head"]["repo"]
                and p["head"]["repo"]["full_name"] == repo
                and any(label["name"] == "delivery-docs" for label in p["labels"])
                for p in prs
            )
            mode = classify(
                changed(event["before"]), git("diff", event["before"], "HEAD", "--", "*.md")
            )
            docs_only = delivery and mode == "docs"
            output(mode="docs" if docs_only else "full", candidate=str(not docs_only).lower())
    else:
        raise ValueError("Unexpected CI event")


def confirm(directory):
    m = verify_bundle(directory, git("rev-parse", "HEAD^{tree}"))
    save(
        directory / "confirmation.json",
        {
            "schema": 1,
            "target": os.environ["GITHUB_SHA"],
            "tree": m["tree"],
            "candidate_sha256": sha(directory / "candidate.json"),
            "main_run_id": int(os.environ["GITHUB_RUN_ID"]),
            "main_run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
        },
    )
    (directory / "SOURCE_COMMIT").write_text(os.environ["GITHUB_SHA"] + "\n")
    names = sorted(p.name for p in directory.iterdir())
    (directory / "SHA256SUMS").write_text("".join(f"{sha(directory / n)}  {n}\n" for n in names))
    verify_bundle(directory, m["tree"], confirmed=True)


def publish(directory, tag, run_id):
    """Called only from main's protected dispatch; no payload is ever executed here."""
    repo = os.environ["GITHUB_REPOSITORY"]
    if os.environ["GITHUB_REF"] != "refs/heads/main" or not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("Dispatch must use main and a stable version tag")
    record = download(run_id, "verified-release", directory)
    if record["event"] != "push" or record["head_branch"] != "main":
        raise ValueError("Release requires a successful main confirmation")
    m = verify_bundle(directory, confirmed=True)
    c = json.loads((directory / "confirmation.json").read_text())
    if (
        c["main_run_id"] != int(run_id)
        or c["target"] != record["head_sha"]
        or c["main_run_attempt"] != record["run_attempt"]
    ):
        raise ValueError("Confirmation provenance mismatch")
    target = c["target"]
    git("fetch", "origin", target)
    git("merge-base", "--is-ancestor", target, "HEAD")
    if git("rev-parse", f"{target}^{{tree}}") != m["tree"]:
        raise ValueError("Release content differs from verified candidate")
    if tag != "v" + m["version"]:
        raise ValueError("Tag/package version mismatch")
    notes = git("show", f"{target}:docs/releases/{tag}.md")
    # Existing immutable tag must match, or create it on the validated target only.
    refs = git("ls-remote", "origin", f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}")
    if refs:
        git("fetch", "origin", "tag", tag)
        if git("rev-parse", f"refs/tags/{tag}^{{commit}}") != target:
            raise ValueError("Existing tag points elsewhere; never overwrite")
    releases = api(f"repos/{repo}/releases?per_page=100")
    existing = next((r for r in releases if r["tag_name"] == tag), None)
    if existing and not existing["draft"]:
        raise ValueError("Version already published; refusing replacement")
    if existing and not refs and existing.get("target_commitish") != target:
        raise ValueError("Existing draft target differs; refusing publication")
    note_file = ROOT / ".cache/ci/release-notes.md"
    note_file.parent.mkdir(parents=True, exist_ok=True)
    note_file.write_text(notes)
    if not existing:
        run(
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            repo,
            "--target",
            target,
            "--draft",
            "--title",
            tag,
            "--notes-file",
            str(note_file),
        )
        existing = next(
            r for r in api(f"repos/{repo}/releases?per_page=100") if r["tag_name"] == tag
        )
    expected = {p.name: sha(p) for p in directory.iterdir()}
    for asset in existing["assets"]:
        if (
            asset["name"] not in expected
            or asset.get("digest") != "sha256:" + expected[asset["name"]]
        ):
            raise ValueError("Existing release asset differs; preserve and investigate")
    present = {a["name"] for a in existing["assets"]}
    for name in sorted(expected.keys() - present):
        run("gh", "release", "upload", tag, str(directory / name), "--repo", repo)
    final = next(r for r in api(f"repos/{repo}/releases?per_page=100") if r["tag_name"] == tag)
    if {a["name"]: a.get("digest") for a in final["assets"]} != {
        n: "sha256:" + d for n, d in expected.items()
    }:
        raise ValueError("Uploaded asset verification failed; draft retained")
    run("gh", "release", "edit", tag, "--repo", repo, "--draft=false")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "package", "confirm", "publish"])
    parser.add_argument("--directory", type=Path, default=ROOT / ".cache/ci/bundle")
    parser.add_argument("--tag")
    parser.add_argument("--run-id", type=int)
    args = parser.parse_args()
    if args.action == "plan":
        plan()
    elif args.action == "package":
        package(args.directory)
    elif args.action == "confirm":
        download(os.environ["GITHUB_RUN_ID"], "release-candidate", args.directory, completed=False)
        confirm(args.directory)
    else:
        publish(args.directory, args.tag, args.run_id)


if __name__ == "__main__":
    main()
