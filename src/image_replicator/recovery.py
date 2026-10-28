"""Non-billable per-image preflight and auditable analysis recovery preparation."""

import copy

from .analysis import inspect_analysis, prepare_reference
from .design import (
    CopyValidationError,
    effective_delta,
    resolve_copy,
    resolve_design,
    validate_final_copy,
)
from .models import REFERENCE_POLICY
from .storage import canonical, digest


class RecoveryRejected(ValueError):
    """Only fixed, credential-free remediation messages cross the tool boundary."""


def job_key(thread: str, index: int) -> str:
    return f"{thread}:{index}"


def preflight(settings, journal, manifest: dict, image_ids: list[str] | None = None) -> dict:
    if manifest.get("alignment_policy") != REFERENCE_POLICY or manifest["version"] != 2:
        raise RecoveryRejected("Preflight/recovery requires a reference-first v2 run")
    selected = (
        set(image_ids) if image_ids is not None else {j["image_id"] for j in manifest["jobs"]}
    )
    if (
        not selected
        or (image_ids is not None and len(selected) != len(image_ids))
        or not selected <= {j["image_id"] for j in manifest["jobs"]}
    ):
        raise RecoveryRejected("Select unique image IDs from the frozen run")
    jobs = []
    for index, original in enumerate(manifest["jobs"]):
        if original["image_id"] not in selected:
            continue
        key = job_key(manifest["thread_id"], index)
        saved = journal.get("job_result", key) or {}
        row = {"image_id": original["image_id"], "index": index}
        redirected = journal.get("analysis_recovery_link", key)
        if redirected:
            jobs.append({**row, "status": "recovery_prepared", **redirected})
            continue
        if saved.get("generation_status") == "generated":
            jobs.append({**row, "status": "generated_preserved", "artifact": saved["artifact"]})
            continue
        link = journal.get("run_job", key)
        if link and journal.get("image", link["key"]):
            jobs.append(
                {
                    **row,
                    "status": "image_operation_exists",
                    "recovery_action": "resume_or_reconcile_original_image_operation",
                }
            )
            continue
        try:
            job = prepare_reference(settings.workspace, original)
            delta = effective_delta(manifest["product_context"], job["delta"])
            views: dict[str, dict] = {}
            results: dict[str, dict | None] = {}
            for kind, field in (("text", "texts"), ("visual", "scene")):
                if delta[field] is not None:
                    views[kind] = {"status": "provided"}
                    results[kind] = {field: delta[field]}
                else:
                    views[kind], results[kind] = inspect_analysis(settings, journal, job, kind)
            row.update(
                analysis=views,
                delta=original["delta"],
                effective_delta=delta,
                replacement_rule_source=(
                    "job.delta.text_replacements"
                    if original["delta"].get("text_replacements") is not None
                    else "product_context.defaults.text_replacements"
                ),
            )
            text = results["text"]
            if text is None:
                row.update(status="analysis_required", copy_status="pending_text_analysis")
            else:
                row["transcription"] = text["texts"]
                try:
                    resolve_copy(text["texts"], delta["text_replacements"] or [])
                    row.update(
                        copy_status="passed",
                        status="ready" if results["visual"] is not None else "analysis_required",
                    )
                    if results["visual"] is not None:
                        try:
                            plan = resolve_design(
                                job, manifest["product_context"], text, results["visual"]
                            )
                            validate_final_copy(plan)
                            row["design_sha256"] = digest(plan)
                        except ValueError as exc:
                            row.update(
                                status="blocked",
                                phase="design_preflight",
                                error_code="design_validation_failed",
                                error_type=type(exc).__name__,
                            )
                except CopyValidationError as exc:
                    row.update(status="blocked", copy_status="failed", **exc.diagnostic)
            if any(v["status"] in {"blocked", "invalid_cache"} for v in views.values()):
                row["status"] = "blocked"
                row.setdefault("recovery_action", "prepare_analysis_recovery")
        except CopyValidationError as exc:
            row.update(status="blocked", copy_status="failed", **exc.diagnostic)
        except Exception as exc:
            row.update(
                status="blocked",
                phase="input_preflight",
                error_code="local_preflight_failed",
                error_type=type(exc).__name__,
            )
        jobs.append(row)
    return {
        "thread_id": manifest["thread_id"],
        "jobs": jobs,
        "provider_requests": 0,
        "ready_for_generation": all(j["status"] in {"ready", "generated_preserved"} for j in jobs),
        "analysis_calls_may_be_billable": True,
    }


def prepare_recovery(service, parent: dict, updates: list, request_id: str) -> dict:
    if (
        not request_id
        or len(request_id) > 120
        or not updates
        or len({u.image_id for u in updates}) != len(updates)
    ):
        raise RecoveryRejected("Supply a stable request_id and unique selected recovery updates")
    if parent.get("alignment_policy") != REFERENCE_POLICY or parent["version"] != 2:
        raise RecoveryRejected("Analysis recovery requires a reference-first v2 run")
    updates = sorted(updates, key=lambda u: service.image_index(parent, u.image_id))
    journal = service.journal
    child = copy.deepcopy(parent)
    child.pop("thread_id")
    child["parent_thread_id"] = parent["thread_id"]
    child["analysis_recovery"] = {
        "parent_thread_id": parent["thread_id"],
        "request_id": request_id,
        "updates_sha256": digest([u.model_dump() for u in updates]),
        "auto_execute": False,
    }
    child["jobs"] = []
    selected = []
    for update in updates:
        index = service.image_index(parent, update.image_id)
        original = parent["jobs"][index]
        result = journal.get("job_result", job_key(parent["thread_id"], index)) or {}
        link = journal.get("run_job", job_key(parent["thread_id"], index))
        if result.get("generation_status") == "generated" or (
            link and journal.get("image", link["key"])
        ):
            raise RecoveryRejected(
                "Recovery cannot touch generated or submitted images; "
                "resume/reconcile or use visual revision"
            )
        if result.get("generation_status") != "blocked":
            raise RecoveryRejected(
                "Select a failed pre-image job, not an unexecuted or successful job"
            )
        if result.get("phase") not in {
            None,
            "analysis",
            "copy_preflight",
            "resolve_design",
            "design_preflight",
        }:
            raise RecoveryRejected(
                "This failure is outside analysis/copy; inspect its original operation"
            )
        job = copy.deepcopy(original)
        if update.delta is not None:
            job["delta"] = update.delta.model_dump()
        scopes = dict(job.get("analysis_retry_scopes", {}))
        for kind in update.retry_kinds:
            scopes[kind] = digest(
                {
                    "parent": parent["thread_id"],
                    "image": update.image_id,
                    "request_id": request_id,
                    "kind": kind,
                }
            )
        job["analysis_retry_scopes"] = scopes
        child["jobs"].append(job)
        selected.append(index)
    child["options"]["selected_image_ids"] = [j["image_id"] for j in child["jobs"]]
    child["thread_id"] = digest(child)
    request_key = digest({"parent": parent["thread_id"], "request_id": request_id})
    previous_request = journal.get("analysis_recovery_request", request_key)
    if previous_request and previous_request["thread_id"] != child["thread_id"]:
        raise RecoveryRejected(
            "request_id already used with different updates; "
            "do not change an existing recovery request"
        )
    existing = journal.get("manifest", child["thread_id"])
    if existing is not None:
        return {
            "thread_id": child["thread_id"],
            "status": "recovery_prepared",
            "idempotent": True,
            "provider_requests": 0,
        }
    for index, update in zip(selected, updates, strict=True):
        if journal.get("analysis_recovery_link", job_key(parent["thread_id"], index)):
            raise RecoveryRejected(
                "A recovery already exists for this image; follow its recovery_run_id"
            )
        old_job = prepare_reference(service.settings.workspace, parent["jobs"][index])
        for kind in update.retry_kinds:
            view, _ = inspect_analysis(service.settings, journal, old_job, kind)
            if view["status"] == "retry_available":
                raise RecoveryRejected(
                    "Analysis has remaining attempts; "
                    "resume original run without resetting its budget"
                )
            if view["status"] not in {"blocked", "invalid_cache"}:
                raise RecoveryRejected(
                    "Reset only a failed analysis kind; successful analysis must be reused"
                )
            if view.get("http_status") and not update.allow_terminal_http_retry:
                raise RecoveryRejected(
                    "Terminal HTTP failure requires confirmed configuration repair "
                    "before explicit retry"
                )
    report = preflight(service.settings, journal, child)
    if any(j["status"] == "blocked" for j in report["jobs"]):
        return {
            "thread_id": parent["thread_id"],
            "status": "preflight_failed",
            "preflight": report,
            "provider_requests": 0,
        }
    with journal.connect() as conn:
        conn.execute(
            "INSERT INTO records VALUES(?,?,?)", ("manifest", child["thread_id"], canonical(child))
        )
        conn.execute(
            "INSERT INTO records VALUES(?,?,?)",
            (
                "analysis_recovery_request",
                request_key,
                canonical({"thread_id": child["thread_id"]}),
            ),
        )
        for index in selected:
            conn.execute(
                "INSERT INTO records VALUES(?,?,?)",
                (
                    "analysis_recovery_link",
                    job_key(parent["thread_id"], index),
                    canonical(
                        {
                            "recovery_thread_id": child["thread_id"],
                            "recovery_action": "follow_recovery_run",
                        }
                    ),
                ),
            )
    return {
        "thread_id": child["thread_id"],
        "status": "recovery_prepared",
        "preflight": report,
        "provider_requests": 0,
        "auto_execute": False,
    }
