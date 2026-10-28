"""Validate and freeze workspace inputs before any paid operation."""

import hashlib
import re
from pathlib import Path, PureWindowsPath

from .images import load_image
from .models import REFERENCE_POLICY, Delta, ProductContext, RunOptions
from .storage import atomic_write, digest, strict_json


def comparable_path(path: Path) -> Path:
    """Compare ordinary DOS/UNC paths consistently without another filesystem probe."""
    if not isinstance(path, PureWindowsPath):
        return path
    value = str(path)
    if value.lower().startswith("\\\\?\\unc\\"):
        value = "\\\\" + value[8:]
    elif re.match(r"^\\\\\?\\[A-Za-z]:\\", value):
        value = value[4:]
    elif value.startswith(("\\\\?\\", "\\\\.\\")):
        raise ValueError("Unsupported Windows device namespace")
    normalized = type(path)(value)
    # Extended paths with these names are not equivalent to ordinary Win32 paths.
    if any(part.endswith((".", " ")) for part in normalized.parts[1:]):
        raise ValueError("Ambiguous Windows path component")
    return normalized


def safe_path(root: Path, relative: str, *, exists: bool = True) -> Path:
    root = root.resolve(strict=True)
    candidate = root / relative
    if Path(relative).anchor or ".." in Path(relative).parts:
        raise ValueError("Only workspace-relative paths are accepted")
    if isinstance(candidate, PureWindowsPath) and any(":" in p for p in Path(relative).parts):
        raise ValueError("Windows alternate streams are not accepted")
    # Refuse symlinks, including intermediate directories, for inputs and outputs.
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink() or cursor.is_junction():
            raise ValueError("Symlink paths are not allowed")
    resolved = comparable_path(candidate.resolve(strict=exists))
    comparison_root = comparable_path(root)
    if not resolved.is_relative_to(comparison_root):
        raise ValueError("Path escapes authorized workspace")
    # Preserve the root's representation for downstream relative_to and task bindings.
    return root / resolved.relative_to(comparison_root)


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


def stable_image_id(source: str, sha: str) -> str:
    # Filename + content identity survives filtering and insertion of other images.
    return f"{Path(source).as_posix()}:{sha[:16]}"


def inspect_images(root: Path, max_input_bytes: int | None = None) -> list[dict]:
    def fingerprint(source: str):
        path = safe_path(root, source)
        if not path.is_file() or (
            max_input_bytes is not None and path.stat().st_size > max_input_bytes
        ):
            raise ValueError("Input must be a file within the configured input byte limit")
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()

    return [
        {
            "source": source,
            "order": order,
            "image_id": stable_image_id(source, fingerprint(source)),
        }
        for paths in discover(root).values()
        for order, source in enumerate(paths, 1)
    ]


def freeze(
    root: Path,
    options: RunOptions,
    *,
    version: int = 2,
    max_input_bytes: int | None = None,
    max_input_pixels: int | None = None,
) -> dict:
    if version not in {1, 2}:
        raise ValueError("Unsupported manifest version")
    root = root.resolve(strict=True)
    groups = discover(root)
    runtime = safe_path(root, ".replicator", exists=False)
    runtime.mkdir(exist_ok=True, mode=0o700)

    def snapshot(relative: str, image: bool = False):
        source = safe_path(root, relative)
        if not source.is_file() or (
            max_input_bytes is not None and source.stat().st_size > max_input_bytes
        ):
            raise ValueError("Input must be a file within the configured input byte limit")
        content = source.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        suffix = source.suffix.lower()
        target = safe_path(root, f".replicator/inputs/{sha}{suffix}", exists=False)
        atomic_write(target, content)
        if image:
            load_image(target, max_input_pixels)
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
                image_id=(
                    f"{group}/{number}:{job['sha256'][:16]}"
                    if version == 1
                    else stable_image_id(path, job["sha256"])
                ),
                delta=Delta.model_validate(delta).model_dump(
                    exclude={"design"} if version == 1 else set()
                ),
            )
            jobs.append(job)
    manifest: dict = {
        "version": version,
        "jobs": jobs,
        "products": products,
        "brief": brief,
        "options": options.model_dump(
            include={"image_model", "concurrency"} if version == 1 else None
        ),
    }
    if version == 2:
        manifest["alignment_policy"] = REFERENCE_POLICY
        context_path = safe_path(root, "brief/design.json", exists=False)
        context = ProductContext()
        if context_path.exists():
            frozen = snapshot("brief/design.json")
            context = ProductContext.model_validate(
                strict_json(Path(frozen["path"]).read_text(encoding="utf-8"))
            )
        manifest["product_context"] = context.model_dump()
        if options.selected_image_ids is not None:
            selected = set(options.selected_image_ids)
            if len(selected) != len(options.selected_image_ids) or not selected <= {
                j["image_id"] for j in jobs
            }:
                raise ValueError("Selected image IDs must be unique and present in inspect_inputs")
            manifest["jobs"] = [job for job in jobs if job["image_id"] in selected]
            manifest["options"]["selected_image_ids"] = [
                job["image_id"] for job in manifest["jobs"]
            ]
    manifest["thread_id"] = digest(manifest)
    return manifest
