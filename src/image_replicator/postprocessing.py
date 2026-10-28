"""Local-only recovery of downloaded v2 images; no Provider or graph execution."""

import hashlib
import re
from pathlib import Path

from .images import CanvasMismatch, geometry, load_image, postprocess
from .inputs import safe_path
from .storage import canonical, strict_json
from .workflow import validate_task_id
from .workflow_v2 import result_key


class LocalRecoveryRejected(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def recover_postprocessing(service, manifest: dict, image_ids: list[str]) -> dict:
    if manifest["version"] != 2:
        raise ValueError("Local postprocess recovery requires a v2 run")
    if not image_ids or len(set(image_ids)) != len(image_ids):
        raise ValueError("Supply explicit unique image_ids")
    # Validate selection before writing any image.
    indexes = [service.image_index(manifest, image_id) for image_id in image_ids]
    root, journal = service.settings.workspace, service.journal
    rows = []
    for index in indexes:
        job = manifest["jobs"][index]
        key = result_key(manifest["thread_id"], index)
        row = {"image_id": job["image_id"], "index": index}
        try:
            previous = journal.get("job_result", key) or {}
            if previous.get("generation_status") == "generated":
                artifact = safe_path(root, previous["artifact"])
                if hashlib.sha256(artifact.read_bytes()).hexdigest() != previous["artifact_sha256"]:
                    raise LocalRecoveryRejected("artifact_hash_mismatch")
                rows.append({**row, "status": "generated_preserved"})
                continue
            link = journal.get("run_job", key)
            if not link or not re.fullmatch(r"[a-f0-9]{64}", link["key"]):
                raise LocalRecoveryRejected("image_operation_missing")
            receipt = journal.get("image", link["key"])
            if not receipt or receipt["status"] != "downloaded":
                raise LocalRecoveryRejected("downloaded_receipt_required")
            task_id = validate_task_id(receipt["task_id"])
            raw = safe_path(root, f".replicator/raw/{link['key']}.image")
            frozen = safe_path(root, str(Path(job["path"]).relative_to(root)))
            if hashlib.sha256(frozen.read_bytes()).hexdigest() != job["sha256"]:
                raise LocalRecoveryRejected("frozen_reference_hash_mismatch")
            original = load_image(frozen).size
            transform = receipt.get("transform") or geometry(*original)
            if tuple(transform["original"]) != original:
                raise LocalRecoveryRejected("stored_geometry_conflict")
            target = safe_path(
                root, f"artifacts/{job['group']}_{job['order']:03d}_{task_id}", exists=False
            )
            artifact = postprocess(raw, target, transform)
            report = strict_json(artifact.with_suffix(".geometry.json").read_text(encoding="utf-8"))
            report["transform_source"] = (
                "stored_request" if receipt.get("transform") else "legacy_frozen_reference"
            )
            result = {
                "generation_status": "generated",
                "review_status": "review_required",
                "artifact": str(artifact.relative_to(root)),
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "reference_sha256": job["sha256"],
                "postprocess": report,
                "postprocess_recovered": True,
            }
            # Keep the prior error as history, never project it as active on success.
            with journal.connect() as conn:
                for kind, record_key, value in (
                    ("postprocess_history", key, previous),
                    ("postprocess", link["key"], report),
                    ("job_result", key, result),
                ):
                    conn.execute(
                        "INSERT OR REPLACE INTO records VALUES(?,?,?)",
                        (kind, record_key, canonical(value)),
                    )
            rows.append({**row, "status": "recovered", **result})
        except Exception as exc:
            rows.append(
                {
                    **row,
                    "status": "rejected",
                    "phase": "postprocess",
                    "error_code": (
                        exc.code
                        if isinstance(exc, LocalRecoveryRejected)
                        else "local_file_missing"
                        if isinstance(exc, FileNotFoundError)
                        else "local_permission_denied"
                        if isinstance(exc, PermissionError)
                        else "local_postprocess_recovery_rejected"
                    ),
                    **(exc.diagnostic if isinstance(exc, CanvasMismatch) else {}),
                    "recovery_action": "preserve_receipt_and_raw_inspect_local_conditions",
                }
            )
    return {
        "thread_id": manifest["thread_id"],
        "status": "partial_or_rejected" if any(r["status"] == "rejected" for r in rows) else "ok",
        "provider_calls": 0,
        "jobs": rows,
    }
