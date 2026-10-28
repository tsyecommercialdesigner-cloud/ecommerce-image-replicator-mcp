import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import portalocker
import pytest
from PIL import Image
from test_workflow import FakeProvider

from image_replicator.analysis import analysis_key, prepare_reference
from image_replicator.config import Settings
from image_replicator.inputs import freeze
from image_replicator.models import AnalysisRecoveryUpdate, GraphState, RunOptions, VisualBatch
from image_replicator.provider import ProviderFailure
from image_replicator.recovery import RecoveryRejected
from image_replicator.routing import WorkspaceRouter
from image_replicator.server import Service
from image_replicator.storage import canonical
from image_replicator.workflow_v2 import ImageWorkflow, result_key


@pytest.fixture
def setup_recovery(workspace, monkeypatch):
    async def no_delay(_):
        pass

    monkeypatch.setattr("image_replicator.workflow.asyncio.sleep", no_delay)
    settings = Settings(workspace, workspace, poll_seconds=0)
    service = Service(settings)
    provider = FakeProvider()
    return service, ImageWorkflow(settings, service.journal, provider), provider


async def test_seven_successes_and_four_failures_recover_without_repeating_successes(
    setup_recovery,
):
    service, workflow, provider = setup_recovery
    root = service.settings.workspace
    for number in range(11, 19):
        Image.new("RGB", (8, 8), "white").save(root / f"references/images_1/{number}.png")
    deltas = (
        [
            {
                "scene": "fixture",
                "text_replacements": [{"old": "absent label", "new": "brand", "source": "fixture"}],
            },
        ]
        * 2
        + [{"texts": []}] * 2
        + [{"texts": [], "scene": "fixture"}] * 7
    )
    (root / "prompts/images_1.json").write_text(canonical(deltas), encoding="utf-8")
    parent = freeze(root, RunOptions(concurrency=3))
    scene_ids = {j["image_id"] for j in parent["jobs"][2:4]}
    original_analyze = provider.analyze
    failing = True

    async def analyze(body):
        ids = [
            json.loads(p["text"])["image_id"]
            for p in body["messages"][1]["content"]
            if p["type"] == "text"
        ]
        if failing and any(i in scene_ids for i in ids):
            provider.analysis.append(body)
            raise ProviderFailure("fixture-private-upstream-payload")
        return await original_analyze(body)

    provider.analyze = analyze
    assert (await workflow.execute(parent))["status"] == "partial"
    thread = parent["thread_id"]
    assert len(provider.submissions) == 7
    before_calls = len(provider.analysis)
    before_manifest = canonical(service.manifest(thread))
    before_results = {
        i: service.journal.get("job_result", result_key(thread, i)) for i in range(11)
    }
    before_images = dict(service.journal.records("image"))
    hashes = {
        r["artifact"]: hashlib.sha256((root / r["artifact"]).read_bytes()).hexdigest()
        for r in before_results.values()
        if r.get("artifact")
    }
    before_llm = copy.deepcopy(dict(service.journal.records("llm")))
    report = service.preflight(thread)
    assert len(provider.analysis) == before_calls
    assert [r["status"] for r in report["jobs"]] == ["blocked"] * 4 + ["generated_preserved"] * 7
    assert report["jobs"][0]["replacement_indexes"] == [0]
    assert report["jobs"][0]["error_code"] == "copy_replacement_unmatched"
    assert before_results[0]["phase"] == "copy_preflight"
    assert before_results[2]["phase"] == "analysis"

    updates = [
        AnalysisRecoveryUpdate(
            image_id=j["image_id"], delta={"text_replacements": [], "scene": "fixture"}
        )
        for j in parent["jobs"][:2]
    ]
    updates += [
        AnalysisRecoveryUpdate(image_id=j["image_id"], retry_kinds=["visual"])
        for j in parent["jobs"][2:4]
    ]
    recovery = service.recover_analysis(thread, updates, "offline-recovery-1")
    child = service.manifest(recovery["thread_id"])
    assert len(child["jobs"]) == 4
    assert recovery["provider_requests"] == 0 and not recovery["auto_execute"]
    assert service.recover_analysis(thread, updates, "offline-recovery-1")["idempotent"]
    with pytest.raises(RecoveryRejected, match="already exists"):
        service.recover_analysis(thread, updates, "accidental-duplicate")
    assert canonical(service.manifest(thread)) == before_manifest
    assert dict(service.journal.records("llm")) == before_llm
    assert dict(service.journal.records("image")) == before_images
    assert len(provider.submissions) == 7
    # Re-executing the parent follows recovery links instead of retrying its four jobs.
    await workflow.execute(parent)
    assert len(provider.analysis) == before_calls and len(provider.submissions) == 7
    failing = False
    restarted = Service(service.settings)
    router = WorkspaceRouter(service.settings, task_workspaces=True)
    child_id = router.bind(restarted, child["thread_id"])
    assert (
        router.expose(restarted, restarted.status(thread))["jobs"][0]["recovery_run_id"] == child_id
    )
    result = await ImageWorkflow(service.settings, restarted.journal, provider).execute(child)
    assert result["generation_complete"]
    assert len(provider.submissions) == 11 and len(provider.analysis) == before_calls + 2
    assert dict(service.journal.records("llm")).items() >= before_llm.items()
    assert all(
        service.journal.get("job_result", result_key(thread, i)) == saved
        for i, saved in before_results.items()
    )
    assert all(
        hashlib.sha256((root / name).read_bytes()).hexdigest() == value
        for name, value in hashes.items()
    )
    assert all(service.journal.get("image", key) == value for key, value in before_images.items())


async def test_success_clears_active_and_legacy_error_markers(setup_recovery):
    service, workflow, provider = setup_recovery
    manifest = freeze(workflow.root, RunOptions())
    state = GraphState(manifest["thread_id"], manifest)
    state.prepared = [prepare_reference(workflow.root, manifest["jobs"][0])]
    provider.fail_primary = True
    await workflow.describe(state, "text")
    key, record = service.journal.records("llm")[0]
    assert "error" not in record and record["failure_history"]
    record["error"] = "LLM request or strict output validation failed"
    service.journal.put("llm", key, record)
    calls = len(provider.analysis)
    await workflow.describe(state, "text")
    assert len(provider.analysis) == calls
    assert "error" not in service.journal.get("llm", key)


async def test_schema_errors_are_located_without_echoing_input(setup_recovery):
    service, workflow, provider = setup_recovery
    manifest = freeze(
        workflow.root,
        RunOptions(selected_image_ids=[freeze(workflow.root, RunOptions())["jobs"][0]["image_id"]]),
    )
    secret = "fixture-secret-not-for-diagnostics"

    async def bad_scene(body):
        iid = manifest["jobs"][0]["image_id"]
        provider.analysis.append(body)
        if body["response_format"]["json_schema"]["name"] == "text_batch":
            return json.dumps({"images": [{"image_id": iid, "texts": []}]})
        return json.dumps({"images": [{"image_id": iid, "scene": [secret], secret: secret}]})

    provider.analyze = bad_scene
    await workflow.execute(manifest)
    row = service.status(manifest["thread_id"])["jobs"][0]
    assert row["phase"] == "analysis" and row["error_code"] == "analysis_schema_validation_failed"
    assert {e["type"] for e in row["schema_errors"]} == {"string_type", "extra_forbidden"}
    assert secret not in canonical(row)
    report = service.preflight(manifest["thread_id"])
    assert secret not in canonical(report)
    assert report["jobs"][0]["analysis"]["visual"]["status"] == "blocked"


@pytest.mark.parametrize(
    "image_status", ["unknown", "submitting", "pending", "success", "downloaded", "failed"]
)
def test_recovery_never_touches_an_existing_image_receipt(setup_recovery, image_status):
    service, workflow, _ = setup_recovery
    manifest = freeze(workflow.root, RunOptions())
    thread = manifest["thread_id"]
    service.journal.put("manifest", thread, manifest)
    service.journal.put("job_result", result_key(thread, 0), {"generation_status": "blocked"})
    service.journal.put("run_job", result_key(thread, 0), {"key": "receipt"})
    service.journal.put("image", "receipt", {"status": image_status, "attempts": 1})
    with pytest.raises(RecoveryRejected, match="submitted images"):
        service.recover_analysis(
            thread,
            [AnalysisRecoveryUpdate(image_id=manifest["jobs"][0]["image_id"], delta={})],
            "unsafe",
        )
    assert len(service.journal.records("manifest")) == 1


def test_terminal_retry_needs_confirmation_and_request_identity_is_stable(setup_recovery):
    service, workflow, _ = setup_recovery
    manifest = freeze(workflow.root, RunOptions())
    thread = manifest["thread_id"]
    service.journal.put("manifest", thread, manifest)
    service.journal.put("job_result", result_key(thread, 0), {"generation_status": "blocked"})
    job = prepare_reference(workflow.root, manifest["jobs"][0])
    key = analysis_key(service.settings, "visual", [job], VisualBatch.model_json_schema())
    service.journal.put(
        "llm", key, {"attempts": 1, "error": "LLM HTTP 400", "terminal_http_status": 400}
    )
    assert (
        service.preflight(thread)["jobs"][0]["analysis"]["visual"]["error_code"]
        == "analysis_http_failure"
    )
    # Supply validated text locally; visual analysis remains a failed explicit retry.
    update = AnalysisRecoveryUpdate(
        image_id=job["image_id"], delta={"texts": []}, retry_kinds=["visual"]
    )
    with pytest.raises(RecoveryRejected, match="confirmed configuration"):
        service.recover_analysis(thread, [update], "terminal-fix")
    update.allow_terminal_http_retry = True
    child = service.recover_analysis(thread, [update], "terminal-fix")
    assert child["status"] == "recovery_prepared"
    altered = update.model_copy(update={"delta": None})
    with pytest.raises(RecoveryRejected, match="different updates"):
        service.recover_analysis(thread, [altered], "terminal-fix")
    with portalocker.Lock(str(workflow.root / ".replicator/execution.lock"), timeout=0):
        with pytest.raises(portalocker.LockException):
            service.preflight(thread)


def test_unknown_text_is_not_claimed_as_a_passed_preflight(setup_recovery):
    service, workflow, provider = setup_recovery
    manifest = freeze(workflow.root, RunOptions())
    service.journal.put("manifest", manifest["thread_id"], manifest)
    report = service.preflight(manifest["thread_id"])
    assert not report["ready_for_generation"]
    assert all(j["copy_status"] == "pending_text_analysis" for j in report["jobs"])
    assert not provider.analysis and not provider.submissions


async def test_global_replacements_can_be_overridden_per_image_without_changing_theme(
    setup_recovery,
):
    service, workflow, provider = setup_recovery
    context = {
        "defaults": {
            "text_replacements": [{"old": "missing", "new": "brand", "source": "fixture"}],
            "design": {"brand_style": {"palette": ["#FF8800"], "text_color": "#FF8800"}},
        }
    }
    (workflow.root / "brief/design.json").write_text(canonical(context), encoding="utf-8")
    manifest = freeze(workflow.root, RunOptions())
    await workflow.execute(manifest)
    thread = manifest["thread_id"]
    report = service.preflight(thread)
    assert all(
        r["replacement_rule_source"] == "product_context.defaults.text_replacements"
        for r in report["jobs"]
    )
    row = report["jobs"][0]
    corrected = {**row["delta"], "text_replacements": []}
    prepared = service.recover_analysis(
        thread, [AnalysisRecoveryUpdate(image_id=row["image_id"], delta=corrected)], "copy-fix"
    )
    child = service.manifest(prepared["thread_id"])
    assert child["product_context"] == manifest["product_context"]
    assert (await workflow.execute(child))["generation_complete"]
    plan = service.design(child["thread_id"], row["image_id"])["plan"]
    assert plan["brand_style"]["palette"] == ["#FF8800"]
    assert len(provider.submissions) == 1
    assert all(service.status(thread)["jobs"][i]["generation_status"] == "blocked" for i in (1, 2))


async def test_non_analysis_node_failure_is_diagnosed_and_not_reset_as_analysis(setup_recovery):
    service, workflow, provider = setup_recovery
    manifest = freeze(workflow.root, RunOptions())
    for job in manifest["jobs"]:
        # A corrupt frozen image must be diagnosed as preprocessing, not LLM schema.
        job["sha256"] = "0" * 64
    await workflow.execute(manifest)
    row = service.status(manifest["thread_id"])["jobs"][0]
    assert row["phase"] == "preprocess" and row["error_code"] == "preprocess_failed"
    with pytest.raises(RecoveryRejected, match="outside analysis"):
        service.recover_analysis(
            manifest["thread_id"],
            [AnalysisRecoveryUpdate(image_id=row["image_id"], delta={})],
            "bad-preprocess-reset",
        )
    assert not provider.analysis and not provider.submissions


async def test_uncorrected_copy_does_not_prepare_a_child_or_spend_on_visual_analysis(
    setup_recovery,
):
    service, workflow, provider = setup_recovery
    replacement = [{"old": "missing", "new": "brand", "source": "fixture"}]
    (workflow.root / "prompts/images_1.json").write_text(
        canonical([{"text_replacements": replacement}] * 3), encoding="utf-8"
    )
    manifest = freeze(workflow.root, RunOptions())
    await workflow.execute(manifest)
    assert len(provider.analysis) == 3
    assert all(
        b["response_format"]["json_schema"]["name"] == "text_batch" for b in provider.analysis
    )
    update = AnalysisRecoveryUpdate(
        image_id=manifest["jobs"][0]["image_id"], delta={"text_replacements": replacement}
    )
    result = service.recover_analysis(manifest["thread_id"], [update], "still-wrong")
    assert result["status"] == "preflight_failed"
    assert len(service.journal.records("manifest")) == 1
    assert not service.journal.records("analysis_recovery_link")
    with pytest.raises(RecoveryRejected, match="Select unique"):
        service.preflight(manifest["thread_id"], [update.image_id, update.image_id])
    assert not provider.submissions


def test_valid_scene_with_stale_error_is_reused_not_reset(setup_recovery):
    service, workflow, provider = setup_recovery
    (workflow.root / "prompts/images_1.json").write_text(
        canonical([{"texts": []}] * 3), encoding="utf-8"
    )
    manifest = freeze(workflow.root, RunOptions())
    thread = manifest["thread_id"]
    service.journal.put("manifest", thread, manifest)
    job = prepare_reference(workflow.root, manifest["jobs"][0])
    key = analysis_key(service.settings, "visual", [job], VisualBatch.model_json_schema())
    service.journal.put(
        "llm",
        key,
        {
            "attempts": 6,
            "error": "LLM request or strict output validation failed",
            "result": [{"image_id": job["image_id"], "scene": "fixture"}],
        },
    )
    service.journal.put("job_result", result_key(thread, 0), {"generation_status": "blocked"})
    row = service.preflight(thread, [job["image_id"]])["jobs"][0]
    assert row["status"] == "ready"
    assert row["analysis"]["visual"]["status"] == "succeeded"
    assert row["analysis"]["visual"]["stale_error_marker"]
    with pytest.raises(RecoveryRejected, match="successful analysis"):
        service.recover_analysis(
            thread,
            [AnalysisRecoveryUpdate(image_id=job["image_id"], retry_kinds=["visual"])],
            "unnecessary-reset",
        )
    assert not provider.analysis and not provider.submissions


def test_concurrent_preparation_is_one_recovery_with_no_duplicate_branch(setup_recovery):
    service, workflow, provider = setup_recovery
    manifest = freeze(workflow.root, RunOptions())
    thread = manifest["thread_id"]
    service.journal.put("manifest", thread, manifest)
    service.journal.put("job_result", result_key(thread, 0), {"generation_status": "blocked"})
    update = AnalysisRecoveryUpdate(
        image_id=manifest["jobs"][0]["image_id"], delta={"texts": [], "scene": "fixture"}
    )

    def prepare(_):
        try:
            return service.recover_analysis(thread, [update], "concurrent-idempotent")["thread_id"]
        except portalocker.LockException:
            return None  # A caller may retry this same request after the active lock clears.

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(prepare, range(2)))
    ids = {value for value in outcomes if value}
    assert len(ids) == 1
    assert service.recover_analysis(thread, [update], "concurrent-idempotent")["thread_id"] in ids
    assert len(service.journal.records("manifest")) == 2
    assert len(service.journal.records("analysis_recovery_link")) == 1
    assert not provider.analysis and not provider.submissions


def test_non_exhausted_analysis_preserves_remaining_attempts(setup_recovery):
    service, workflow, provider = setup_recovery
    manifest = freeze(workflow.root, RunOptions())
    thread = manifest["thread_id"]
    service.journal.put("manifest", thread, manifest)
    service.journal.put("job_result", result_key(thread, 0), {"generation_status": "blocked"})
    job = prepare_reference(workflow.root, manifest["jobs"][0])
    key = analysis_key(service.settings, "visual", [job], VisualBatch.model_json_schema())
    service.journal.put(
        "llm", key, {"attempts": 1, "error": "LLM request or strict output validation failed"}
    )
    view = service.preflight(thread)["jobs"][0]["analysis"]["visual"]
    assert view["status"] == "retry_available"
    assert view["error_code"] == "analysis_previous_attempt_failed"
    assert view["recovery_action"] == "resume_original_run"
    with pytest.raises(RecoveryRejected, match="remaining attempts"):
        service.recover_analysis(
            thread,
            [AnalysisRecoveryUpdate(image_id=job["image_id"], retry_kinds=["visual"])],
            "not-exhausted",
        )
    assert service.journal.get("llm", key)["attempts"] == 1
    assert not provider.analysis and not provider.submissions
