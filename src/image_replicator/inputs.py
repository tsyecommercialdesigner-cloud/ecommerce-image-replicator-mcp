"""Validate and freeze workspace inputs before any paid operation."""

import hashlib
import re
from pathlib import Path

from .images import load_image
from .models import Delta, RunOptions
from .storage import atomic_write, digest, strict_json


def safe_path(root: Path, relative: str, *, exists: bool = True) -> Path:
    root = root.resolve(strict=True)
    candidate = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Only workspace-relative paths are accepted")
    # Refuse symlinks, including intermediate directories, for inputs and outputs.
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlink paths are not allowed")
    resolved = candidate.resolve(strict=exists)
    if not resolved.is_relative_to(root):
        raise ValueError("Path escapes authorized workspace")
    return resolved


def natural_key(path: Path):
    return [
        (0, int(s)) if s.isdigit() else (1, s.casefold()) for s in re.split(r"(\d+)", path.name)
    ]


def image_files(directory: Path) -> list[Path]:
    result = sorted(
        (p for p in directory.iterdir() if p.suffix.lower() in {".jpg", ".png"}),
        key=lambda p: (natural_key(p), p.name),
    )
    if not result:
        raise ValueError(f"No JPG/PNG inputs in {directory.name}")
    keys = [natural_key(p) for p in result]
    if len({repr(k) for k in keys}) != len(keys):
        raise ValueError("Ambiguous natural order; rename duplicate numeric/case variants")
    return result


def discover(root: Path) -> dict:
    references = safe_path(root, "references")
    groups = sorted((p for p in references.iterdir() if p.is_dir()), key=natural_key)
    result = {}
    for group in groups:
        if not re.fullmatch(r"[\w-]{1,80}", group.name):
            raise ValueError("Reference folder names must contain letters, numbers, '_' or '-'")
        folder = safe_path(root, f"references/{group.name}")
        result[group.name] = [str(p.relative_to(root)) for p in image_files(folder)]
    if not result:
        raise ValueError("references/ must contain image subfolders")
    return result


def freeze(root: Path, options: RunOptions) -> dict:
    root = root.resolve(strict=True)
    groups = discover(root)
    runtime = safe_path(root, ".replicator", exists=False)
    runtime.mkdir(exist_ok=True, mode=0o700)

    def snapshot(relative: str, image: bool = False):
        source = safe_path(root, relative)
        if not source.is_file() or source.stat().st_size > 50 * 1024 * 1024:
            raise ValueError("Input must be a file of at most 50 MiB")
        content = source.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        suffix = source.suffix.lower()
        target = safe_path(root, f".replicator/inputs/{sha}{suffix}", exists=False)
        atomic_write(target, content)
        if image:
            load_image(target)
        return {"source": relative, "sha256": sha, "path": str(target)}

    products = [
        snapshot(str(p.relative_to(root)), True) for p in image_files(safe_path(root, "products"))
    ]
    brief_dir = safe_path(root, "brief")
    briefs = sorted(brief_dir.glob("*.md"), key=natural_key)
    if not briefs:
        raise ValueError("brief/ must contain Markdown product information")
    brief = "\n\n".join(
        Path(snapshot(str(p.relative_to(root)))["path"]).read_text(encoding="utf-8") for p in briefs
    )
    if len(brief) > 100_000:
        raise ValueError("Product brief exceeds 100000 characters")
    jobs = []
    for group, paths in groups.items():
        delta_path = safe_path(root, f"prompts/{group}.json", exists=False)
        deltas = (
            strict_json(delta_path.read_text(encoding="utf-8"))
            if delta_path.exists()
            else ([{} for _ in paths])
        )
        if not isinstance(deltas, list) or len(deltas) != len(paths):
            raise ValueError(f"prompts/{group}.json must have one array item per reference")
        for number, (path, delta) in enumerate(zip(paths, deltas, strict=True), 1):
            job = snapshot(path, True)
            job.update(
                group=group,
                order=number,
                image_id=f"{group}/{number}:{job['sha256'][:16]}",
                delta=Delta.model_validate(delta).model_dump(),
            )
            jobs.append(job)
    manifest = {
        "version": 1,
        "jobs": jobs,
        "products": products,
        "brief": brief,
        "options": options.model_dump(),
    }
    manifest["thread_id"] = digest(manifest)
    return manifest
