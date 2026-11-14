"""Changed-scope checks without paid provider access."""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ci_policy import changed  # noqa: E402

RELATED = {
    "network.py": ["tests/test_network.py"],
    "diagnostics.py": ["tests/test_provider.py", "tests/test_analysis_recovery.py"],
    "images.py": [
        "tests/test_contracts.py",
        "tests/test_postprocessing.py",
        "tests/test_workflow.py",
        "tests/test_adaptation.py",
        "tests/test_analysis_recovery.py",
    ],
}

# Supplied API documents cite an external historical validation archive, not shipped files.
# Exact document/target pairs only; new broken links must still fail.
HISTORICAL = {
    "docs/API-ENDPOINT-GEMINILLM.md": {"validation/2026-10-20/gemini-0.json"},
    "docs/API-ENDPOINT-NANOBANANA.md": {
        "validation/2026-10-20/" + name
        for name in (
            "REPORT.md",
            "gemini-0.json",
            "gemini-0-empty-config.json",
            "gemini-0-budget-only.json",
            "gemini-0-thoughts-only.json",
            "followup-gemini-2-simple.json",
            "chat-temperature.json",
            "chat-top-p.json",
            "chat-bias-object.json",
            "chat-bias-null.json",
            "chat-tools-string.json",
            "chat-tools-object.json",
            "chat-seen.json",
            "chat-seed.json",
            "chat-unknown.json",
            "chat-image.json",
            "chat-2.json",
            "gen-1.json",
            "followup-gen-2-simple.json",
            "edits-1.json",
            "followup-edits-1-simple.json",
            "followup-edits-1-no-reference.json",
        )
    }
    | {"[URL_OMITTED]"},
}


def command(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def documents(paths, versioned=None):
    for name in paths:
        path = ROOT / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix == ".json":
            json.loads(text)
        elif path.suffix == ".toml":
            tomllib.loads(text)
        elif path.suffix == ".md":
            if len(re.findall(r"^```", text, re.M)) % 2:
                raise ValueError(f"Unclosed code fence: {name}")
            for body in re.findall(r"```json\s*\n(.*?)\n```", text, re.S):
                json.loads(body)
            for target in re.findall(r"\]\(([^\s)]+)\)", text):
                if target.startswith(("https://", "http://", "#", "<")):
                    continue
                target = target.split("#", 1)[0]
                if target in HISTORICAL.get(name, set()):
                    print(f"Historical external reference (not checked locally): {name}: {target}")
                    continue
                if "<" not in target:
                    destination = path.parent / target
                    available = destination.exists()
                    if versioned is not None:
                        try:
                            relative = destination.resolve().relative_to(ROOT.resolve()).as_posix()
                        except ValueError:
                            available = False
                        else:
                            available = available and (
                                relative in versioned
                                or any(p.startswith(relative.rstrip("/") + "/") for p in versioned)
                            )
                    if not available:
                        raise ValueError(f"Broken or unversioned local link in {name}: {target}")
    command(sys.executable, "scripts/check_secrets.py")


def related(paths):
    selected = {"tests/test_mcp.py", "tests/test_contracts.py"}
    for name in paths:
        if name.startswith("src/"):
            if Path(name).name not in RELATED:
                return ["tests"]
            selected.update(RELATED[Path(name).name])
        elif name.startswith("tests/"):
            if Path(name).name.startswith("test_") and Path(name).suffix == ".py":
                if (ROOT / name).is_file():
                    selected.add(name)
            else:
                return ["tests"]
    return sorted(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["docs", "light"])
    parser.add_argument("--base", required=True)
    parser.add_argument("--all", action="store_true", help="Parse all versionable documentation")
    args = parser.parse_args()
    paths = changed(args.base)
    versioned = set(
        subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    )
    doc_paths = paths
    if args.all:
        doc_paths = (
            subprocess.check_output(["git", "ls-files", "--cached"], cwd=ROOT).decode().splitlines()
        )
    documents([p for p in doc_paths if Path(p).suffix in {".md", ".json", ".toml"}], versioned)
    command("git", "diff", "--check", args.base, "HEAD")
    if args.mode == "light":
        python = [p for p in paths if p.endswith(".py") and (ROOT / p).is_file()]
        if python:
            command(sys.executable, "-m", "ruff", "format", "--check", *python)
            command(sys.executable, "-m", "ruff", "check", *python)
        command(sys.executable, "-m", "mypy", "src")
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="ci-scoped-", dir=ROOT / ".cache") as temp:
            command(
                sys.executable, "-m", "pytest", "-q", *related(paths), f"--basetemp={temp}/tests"
            )
    print(json.dumps({"status": "passed", "mode": args.mode, "paths": paths}))


if __name__ == "__main__":
    main()
