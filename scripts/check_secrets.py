"""Focused secret check of versionable files; reports locations, never matched values.

This checks private key blocks, common access-token forms, and nonempty API-key
assignments. It is not a replacement for a platform secret scanner/history scan.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"),
    re.compile(r"^ZHENZHEN_(?:GEMINILLM|GPTIMAGEGEN)_API_KEY[ \t]*=[ \t]*\S+", re.M),
]


def main():
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    failures = []
    for name in sorted(set(paths) - {""}):
        path = ROOT / name
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for pattern in PATTERNS:
            for match in pattern.finditer(content):
                failures.append(f"{name}:{content[: match.start()].count(chr(10)) + 1}")
    if failures:
        raise SystemExit("Potential secrets at: " + ", ".join(failures))
    print("Focused secret checks passed")


if __name__ == "__main__":
    main()
