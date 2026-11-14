"""Shared local/CI quality gate; preserve each subprocess's failure status."""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def remove_temporary(path: Path):
    cache = (ROOT / ".cache").resolve()
    resolved = path.resolve()
    if (
        resolved == cache
        or not resolved.is_relative_to(cache)
        or path.is_symlink()
        or path.is_junction()
    ):
        raise ValueError("Cleanup must stay inside the workspace test cache")

    def readonly_retry(function, filename, error):
        if not isinstance(error, PermissionError):
            raise error
        # Git objects are read-only on Windows; do not suppress a real ACL/lock failure.
        os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        function(filename)

    shutil.rmtree(path, onexc=readonly_retry)


def main():
    temporary = ROOT / ".cache" / "check-tests"
    reports = ROOT / ".cache" / "validation"
    reports.mkdir(parents=True, exist_ok=True)
    checks = [
        [sys.executable, "-m", "ruff", "format", "--check", "src", "tests", "scripts"],
        [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"],
        [sys.executable, "-m", "mypy", "src"],
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            f"--basetemp={temporary}",
            f"--junitxml={reports / 'pytest.xml'}",
        ],
        [sys.executable, "scripts/check_secrets.py"],
    ]
    try:
        for command in checks:
            result = subprocess.run(command, cwd=ROOT, check=False)
            if result.returncode:
                return result.returncode
        return 0
    finally:
        if temporary.exists():
            remove_temporary(temporary)


if __name__ == "__main__":
    raise SystemExit(main())
