"""Smoke-test candidate distributions in disposable locked runtime environments."""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def call(*args, cwd=None):
    subprocess.run([str(a) for a in args], cwd=cwd or ROOT, check=True, timeout=240)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix="candidate-install-", dir=cache))
    try:
        (wheel,) = args.directory.glob("*.whl")
        (source,) = args.directory.glob("*.tar.gz")
        lock = temp / "runtime.txt"
        with lock.open("w", encoding="utf-8") as handle:
            subprocess.run(
                ["uv", "export", "--locked", "--no-dev", "--no-emit-project"],
                cwd=ROOT,
                stdout=handle,
                check=True,
                timeout=120,
            )
        for index, package in enumerate((wheel, source)):
            env = temp / f"env-{index}"
            call("uv", "venv", env, "--python", "3.12")
            python = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            call("uv", "pip", "sync", "--python", python, lock)
            call("uv", "pip", "install", "--python", python, "--no-deps", package.resolve())
            call(python, ROOT / "scripts/smoke.py", "--project-root", temp, cwd=temp)
    finally:
        shutil.rmtree(temp)


if __name__ == "__main__":
    main()
