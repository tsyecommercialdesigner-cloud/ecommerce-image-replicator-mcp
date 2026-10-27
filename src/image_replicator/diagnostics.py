"""Bounded, redacted provider errors. Never persist raw HTTP bodies or request headers."""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import httpx

from .inputs import safe_path
from .storage import atomic_write, canonical


def redact_error(value: str, request: dict, secrets: dict) -> str:
    # Known credentials are removed before truncation, including common encoded echoes.
    for secret in secrets.values():
        if secret:
            for variant in (secret, quote(secret, safe=""), json.dumps(secret)[1:-1]):
                value = value.replace(variant, "[REDACTED]")

    def strings(node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, list):
            for item in node:
                yield from strings(item)
        elif isinstance(node, dict):
            for item in node.values():
                yield from strings(item)

    # Error messages that echo private message content are omitted, not partially logged.
    for text in strings(request.get("messages", [])):
        if len(text) >= 16:
            for variant in (text, json.dumps(text)[1:-1]):
                if variant[:64] in value:
                    return "[REQUEST_CONTENT_OMITTED]"
    value = re.sub(r"(?i)data:[^\s\"<>]+", "[DATA_URL_REDACTED]", value)
    value = re.sub(r"(?i)https?://[^\s\"<>]+", "[URL_REDACTED]", value)
    value = re.sub(r"(?i)bearer\s+[^\s\"<>]+", "Bearer [REDACTED]", value)
    value = re.sub(r"(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]+", "[TOKEN_REDACTED]", value)
    value = re.sub(r"[A-Za-z0-9_+/=-]{64,}", "[OPAQUE_REDACTED]", value)
    return value[:2048]


def record_llm_error(workspace: Path, response: httpx.Response, body: dict, keys: dict) -> str:
    diagnostic_id = uuid4().hex
    error = {}
    if len(response.content) <= 65536:
        try:
            payload = response.json()
            candidate = payload.get("error", payload) if isinstance(payload, dict) else {}
            if isinstance(candidate, str):
                candidate = {"message": candidate}
            if isinstance(candidate, dict):
                for name in ("message", "type", "code", "param"):
                    value = candidate.get(name)
                    if isinstance(value, (str, int)):
                        error[name] = redact_error(str(value), body, keys)
        except ValueError:
            pass  # Non-JSON errors retain metadata only; HTML may contain private echoes.
    record = {
        "diagnostic_id": diagnostic_id,
        "operation": "llm_analysis",
        "http_status": response.status_code,
        "model": redact_error(str(body.get("model", "")), body, keys),
        "response_bytes": len(response.content),
        "response_sha256": hashlib.sha256(response.content).hexdigest(),
        "error": error,
    }
    path = safe_path(workspace, f".replicator/errors/{diagnostic_id}.json", exists=False)
    atomic_write(path, canonical(record).encode())
    return diagnostic_id
