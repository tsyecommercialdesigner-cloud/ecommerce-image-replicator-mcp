"""Opt-in release upgrade/rollback probe; all generated data stays inside .cache."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "v0.1.1": "c85f396c559411a68bdd5a2cba4bbbe858ab3245",
    "v0.1.2": "036ef5e3246ce32f23ddd8138284fc1d18f357ed",
    "v0.1.3": "f437164d10a8a7dd7fd21bd85ee1deccf7b4533e",
    "v0.1.4": "a77ed089de3031cbefdbd235608b6631a95d3e40",
    "v0.1.5": "b1c1bd1bcdba05ec50ec5e33a83797c90ec5751f",
    "v0.1.6": "1459ebd0e4b63de6bc5a75e41458846f7e6dce83",
}


def acl(path):
    if os.name != "nt":
        return str(path.stat().st_mode)
    import win32security

    flags = (
        win32security.OWNER_SECURITY_INFORMATION
        | win32security.GROUP_SECURITY_INFORMATION
        | win32security.DACL_SECURITY_INFORMATION
    )
    descriptor = win32security.GetFileSecurity(str(path), flags)
    return win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(descriptor, 1, flags)


def snapshot(paths):
    result = {}
    for root in paths:
        for path in [root, *sorted(root.rglob("*"))] if root.is_dir() else [root]:
            result[str(path)] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
                "acl": acl(path),
            }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", help="Git ref to verify against --baseline, then roll back")
    parser.add_argument("--baseline", choices=TARGETS, default="v0.1.2")
    args = parser.parse_args()
    reports = ROOT / ".cache/validation"
    reports.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="upgrade-", dir=ROOT / ".cache"))
    logs = []
    report = {
        "status": "failed",
        "targets": TARGETS,
        "platform": os.name,
        "real_provider_requests": 0,
    }
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"):
        env.pop(key, None)
    env["UV_CACHE_DIR"] = str(temporary / "cache")
    env["UV_LINK_MODE"] = "copy"

    def run(args, cwd=temporary):
        result = subprocess.run(
            [str(a) for a in args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        logs.append(
            {
                "command": list(map(str, args)),
                "exit": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        if result.returncode:
            raise RuntimeError(result.stderr[-1500:])
        return result.stdout.strip()

    try:
        install, workspace = temporary / "installation", temporary / "workspace"
        workspace.mkdir()
        run(["git", "clone", "--no-local", "--no-checkout", ROOT, install])
        probe = ROOT / "tests/fixtures/upgrade_probe.py"
        retained = []
        phases = (("seed", "v0.1.1"), ("upgrade", "v0.1.2"), ("rollback", "v0.1.1"))
        if args.candidate:
            candidate = run(["git", "rev-parse", f"{args.candidate}^{{commit}}"], install)
            report["candidate"] = candidate
            phases = (("seed", args.baseline), ("upgrade", candidate), ("rollback", args.baseline))
        for phase, tag in phases:
            before = snapshot(retained)
            assert run(["git", "rev-parse", f"{tag}^{{commit}}"], install) == TARGETS.get(tag, tag)
            run(["git", "switch", "--detach", "--no-overwrite-ignore", tag], install)
            run(["uv", "sync", "--locked", "--no-dev", "--python", "3.12"], install)
            assert snapshot(retained) == before, "Upgrade changed retained files or ACLs"
            private = install / ".env"
            if phase == "seed":
                private.write_text(
                    "ZHENZHEN_GEMINILLM_API_KEY=fixture-not-a-real-key\n"
                    "ZHENZHEN_GPTIMAGEGEN_API_KEY=fixture-not-a-real-key\n"
                )
            python = install / (
                ".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python"
            )
            result = json.loads(run([python, probe, phase, install, workspace, temporary]))
            report[phase] = result
            if phase == "seed":
                retained = [private, workspace]
                original_env = snapshot([private])
                original_artifacts = snapshot([workspace / "artifacts"])
            else:
                assert snapshot([private]) == original_env
                current = snapshot([workspace / "artifacts"])
                assert all(current[k] == v for k, v in original_artifacts.items())
            if phase == "upgrade":
                retained.append(install / ".replicator")
        report.update(
            status="passed",
            retained_bytes_and_acls=True,
            pending_receipt_resumed_without_resubmission=True,
            published_tags_unchanged=True,
        )
    finally:
        assert temporary.resolve().is_relative_to((ROOT / ".cache").resolve())

        # Git's read-only object files need their writable bit restored on Windows.
        def writable_retry(function, path, exc):
            os.chmod(path, 0o700)
            function(path)

        shutil.rmtree(temporary, onexc=writable_retry)
        report["temporary_removed"] = not temporary.exists()
        (reports / "upgrade-preservation.json").write_text(json.dumps(report, indent=2))
        (reports / "upgrade-preservation-log.json").write_text(json.dumps(logs, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
