"""Reversible geometry: uniform scale, pad, validate output canvas, crop, resize."""

import io
import math
from pathlib import Path

from PIL import Image, ImageOps

from .storage import atomic_write

MIN_PIXELS = 655_360
MAX_PIXELS = 8_294_400
MAX_EDGE = 4096
Image.MAX_IMAGE_PIXELS = None  # Optional application pixel cap is checked before decoding.


def route_image_model(family: str, canvas: list[int]) -> str:
    """Select the provider variant from the actual padded request canvas."""
    if family not in {"gpt-image-2.5-flare", "gpt-image-2.5-sunburst"}:
        raise ValueError("Unknown image model family")
    if len(canvas) != 2 or any(type(edge) is not int or edge <= 0 for edge in canvas):
        raise ValueError("Invalid canvas dimensions")
    length = max(canvas)
    if length > MAX_EDGE:
        raise ValueError("Canvas exceeds the 4k model's 4096px long-edge limit")
    suffix = "" if length <= 1024 else "-2k" if length <= 2048 else "-4k"
    return family + suffix


def load_image(path: Path, max_pixels: int | None = None) -> Image.Image:
    with Image.open(path) as image:
        if image.format not in {"PNG", "JPEG"} or getattr(image, "n_frames", 1) != 1:
            raise ValueError("Only single-frame JPEG and PNG images are supported")
        if max_pixels is not None and image.width * image.height > max_pixels:
            raise ValueError("Image exceeds configured input pixel limit")
        image.load()
        return ImageOps.exif_transpose(image).copy()


def geometry(width: int, height: int) -> dict:
    if min(width, height) <= 0:
        raise ValueError("Invalid image dimensions")
    # Enumerate legal canvases; prefer full reference resolution and minimal padding.
    candidates = []
    for w in range(16, MAX_EDGE + 1, 16):
        low = max(16, math.ceil(w / 3 / 16) * 16, math.ceil(MIN_PIXELS / w / 16) * 16)
        high = min(MAX_EDGE, 3 * w, (MAX_PIXELS // w // 16) * 16)
        for h in range(low, high + 1, 16):
            scale = min(w / width, h / height)
            # Penalize scaling in either direction before minimizing padding.
            score = abs(math.log(scale)) * 10 + (w * h / (width * height * scale**2) - 1)
            candidates.append((score, w * h, w, h, scale))
    _, _, w, h, scale = min(candidates)
    sw, sh = min(w, max(1, round(width * scale))), min(h, max(1, round(height * scale)))
    left, top = (w - sw) // 2, (h - sh) // 2
    return {
        "original": [width, height],
        "canvas": [w, h],
        "resized": [sw, sh],
        "crop": [left, top, left + sw, top + sh],
    }


def preprocess(source: Path, destination: Path) -> dict:
    image = load_image(source).convert("RGB")
    transform = geometry(*image.size)
    resized = image.resize(tuple(transform["resized"]), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", tuple(transform["canvas"]), (255, 255, 255))
    canvas.paste(resized, tuple(transform["crop"][:2]))
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    atomic_write(destination, buffer.getvalue())
    return transform


def postprocess(raw: Path, target_stem: Path, transform: dict) -> Path:
    # Read actual encoding instead of trusting URL suffix or content-type.
    with Image.open(raw) as image:
        fmt = image.format
        if fmt not in {"PNG", "JPEG"}:
            raise ValueError("Unexpected provider output format")
        if list(image.size) != transform["canvas"]:
            raise ValueError(
                "Provider output canvas differs from requested size; raw image retained"
            )
        image.load()
        cropped = image.crop(tuple(transform["crop"]))
        result = cropped.resize(tuple(transform["original"]), Image.Resampling.LANCZOS)
        suffix = ".png" if fmt == "PNG" else ".jpg"
        destination = target_stem.with_suffix(suffix)
        buffer = io.BytesIO()
        if fmt == "JPEG":
            result = result.convert("RGB")
            result.save(buffer, format=fmt, quality=95)
        else:
            result.save(buffer, format=fmt)
        content = buffer.getvalue()
        if destination.exists() and destination.read_bytes() != content:
            raise ValueError("Existing artifact differs; refusing to overwrite")
        atomic_write(destination, content)
        return destination
