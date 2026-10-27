"""Shared local/CI quality gate; preserve each subprocess's failure status."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
            shutil.rmtree(temporary)


if __name__ == "__main__":
    raise SystemExit(main())
