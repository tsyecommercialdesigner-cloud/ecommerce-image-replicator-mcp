"""Offline analysis inspection and stable, optionally recovery-scoped cache identities."""

import hashlib
from pathlib import Path

from .images import preprocess
from .inputs import safe_path
from .models import TextBatch, VisualBatch
from .provider import ProviderFailure, analysis_body
from .storage import digest


class AnalysisFailure(ProviderFailure):
    def __init__(self, kind: str, key: str, record: dict):
        fallback_code = (
            "analysis_http_failure"
            if record.get("terminal_http_status")
            else "analysis_retry_exhausted"
            if record["attempts"] >= 6
            else "analysis_previous_attempt_failed"
        )
        self.diagnostic = {
            "phase": "analysis",
            "analysis_kind": kind,
            "cache_key": key,
            "error_code": record.get("failure_code", fallback_code),
            "attempts": record["attempts"],
            "schema_errors": record.get("schema_errors", []),
            "http_status": record.get("terminal_http_status"),
            "diagnostic_id": record.get("diagnostic_id"),
            "recovery_action": "preflight_run_then_prepare_analysis_recovery",
        }
        http = (
            f"HTTP {record['terminal_http_status']}; " if record.get("terminal_http_status") else ""
        )
        super().__init__(
            f"LLM {http}analysis {kind} blocked; code={self.diagnostic['error_code']}; cache={key}"
        )


def analysis_key(settings, kind: str, batch: list[dict], schema: dict) -> str:
    key = digest(
        {
            "version": 1,
            "body": analysis_body(
                "gemini-3.8-flash", kind, batch, schema, settings.max_output_tokens
            ),
        }
    )
    scopes = [job.get("analysis_retry_scopes", {}).get(kind) for job in batch]
    return digest({"base": key, "recovery_scopes": scopes}) if any(scopes) else key


def prepare_reference(root: Path, job: dict) -> dict:
    original = Path(job["path"]).read_bytes()
    if hashlib.sha256(original).hexdigest() != job["sha256"]:
        raise ValueError("Frozen reference changed")
    key = digest({"image_id": job["image_id"], "sha256": job["sha256"]})
    target = safe_path(root, f".replicator/prepared-v2/{key}.png", exists=False)
    transform = preprocess(Path(job["path"]), target)
    return {**job, "transform": transform, "prepared_path": str(target)}


def inspect_analysis(settings, journal, job: dict, kind: str) -> tuple[dict, dict | None]:
    contract = TextBatch if kind == "text" else VisualBatch
    key = analysis_key(settings, kind, [job], contract.model_json_schema())
    record = journal.get("llm", key) or {"attempts": 0}
    view = {"cache_key": key, "attempts": record["attempts"]}
    if "result" in record:
        try:
            parsed = contract.model_validate({"images": record["result"]})
            if [item.image_id for item in parsed.images] != [job["image_id"]]:
                raise ValueError("Cached analysis identity mismatch")
            return {**view, "status": "succeeded", "stale_error_marker": "error" in record}, (
                parsed.images[0].model_dump()
            )
        except ValueError:
            return {**view, "status": "invalid_cache", "error_code": "invalid_analysis_cache"}, None
    if record.get("error") or record.get("terminal_http_status") or record["attempts"] >= 6:
        resumable = not record.get("terminal_http_status") and record["attempts"] < 6
        return {
            **view,
            **AnalysisFailure(kind, key, record).diagnostic,
            "status": "retry_available" if resumable else "blocked",
            "recovery_action": "resume_original_run" if resumable else "prepare_analysis_recovery",
        }, None
    return {**view, "status": "analysis_required"}, None


def clear_analysis_error(record: dict) -> bool:
    fields = (
        "error",
        "failure_code",
        "error_type",
        "schema_errors",
        "terminal_http_status",
        "diagnostic_id",
    )
    removed = {key: record.pop(key) for key in fields if key in record}
    if removed:
        record.setdefault("failure_history", []).append({"legacy_error_cleared": True, **removed})
    return bool(removed)


def schema_locations(exc) -> list[dict]:
    allowed = {
        "images",
        "image_id",
        "texts",
        "scene",
        "content",
        "css",
        "box",
        "x",
        "y",
        "width",
        "height",
    }
    return [
        {
            "type": error["type"],
            "path": [
                part if isinstance(part, int) or part in allowed else "<field>"
                for part in error["loc"]
            ],
        }
        for error in exc.errors(include_input=False, include_context=False)
    ]
