"""Explicit project-root configuration; never search the caller's cwd for secrets."""

import os
import sys
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

from dotenv.parser import parse_stream

KEYS = ("ZHENZHEN_GEMINILLM_API_KEY", "ZHENZHEN_GPTIMAGEGEN_API_KEY")


def windows_user_value(name: str) -> str | None:
    if sys.platform != "win32":
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value)
    except FileNotFoundError:
        return None


def read_keys(project_root: Path) -> dict[str, str]:
    path = project_root / ".env"
    values: dict[str, str | None] = {}
    try:
        content = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        content = ""
    except (OSError, UnicodeError):
        raise ValueError("Cannot read project .env") from None
    for binding in parse_stream(StringIO(content)):
        if binding.error:
            raise ValueError("Invalid syntax in project .env")
        if binding.key is not None:
            if binding.key in values:
                raise ValueError(f"Duplicate .env field: {binding.key}")
            values[binding.key] = binding.value
    result = {}
    for name in KEYS:
        if name in values:
            value = values[name]
        elif name in os.environ:
            value = os.environ[name]
        else:
            value = windows_user_value(name)
            if value is None:
                raise ValueError(f"Missing credential: {name}")
        if not value or not value.strip() or any(c in value for c in "\r\n\x00"):
            raise ValueError(f"Empty or invalid credential: {name}")
        result[name] = value
    return result


@dataclass(frozen=True)
class Settings:
    project_root: Path
    workspace: Path
    # Operator supplies provisional budgets; provider compatibility needs validation.
    max_batch_images: int = 0
    max_request_bytes: int = 0
    max_output_tokens: int = 0
    download_hosts: tuple[str, ...] = ("ai.t8star.org", "files.closeai.fans")
    poll_seconds: float = 5.0
    poll_timeout: float = 300.0
    max_download_bytes: int = 50 * 1024 * 1024
    base_url: str = field(default="https://ai.t8star.org", init=False)

    def validate_execution(self):
        if min(self.max_batch_images, self.max_request_bytes, self.max_output_tokens) <= 0:
            raise ValueError(
                "Configure max-batch-images, max-request-bytes, "
                "and max-output-tokens before execution"
            )
