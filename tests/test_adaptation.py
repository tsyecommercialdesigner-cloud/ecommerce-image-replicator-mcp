import asyncio
import copy
import hashlib
import json
from pathlib import Path

import pytest
from test_workflow import FakeProvider

from image_replicator.config import Settings
from image_replicator.design import effective_delta, resolve_design
from image_replicator.inputs import freeze, inspect_images
from image_replicator.models import Delta, ProductContext, RevisionUpdate, RunOptions
from image_replicator.models import ReferenceReviewReport as ReviewReport
from image_replicator.provider import LLMHTTPFailure, ProviderFailure, SubmissionUnknown
from image_replicator.server import Service
from image_replicator.storage import canonical, digest
from image_replicator.workflow import Workflow
from image_replicator.workflow_v2 import ImageWorkflow


def write_deltas(workspace, deltas):
    (workspace / "prompts/images_1.json").write_text(canonical(deltas), encoding="utf-8")


@pytest.fixture
def setup_v2(workspace, monkeypatch):
    async def no_delay(_):
        pass

    monkeypatch.setattr("image_replicator.workflow.asyncio.sleep", no_delay)
    settings = Settings(workspace, workspace, 10, 10_000_000, 8000, poll_seconds=0)
    service = Service(settings)
    provider = FakeProvider()
    workflow = ImageWorkflow(settings, service.journal, provider)
    write_deltas(workspace, [{"texts": [], "scene": "Use the product photo's orange pattern"}] * 3)
    return service, workflow, provider


def make_report(service, manifest, index=0, verdict="pass"):
    job = service.status(manifest["thread_id"])["jobs"][index]
    assert "artifact_sha256" in job, job
    plan = service.design(manifest["thread_id"], job["image_id"])["plan"]
    return ReviewReport.model_validate(
        {
            "image_id": job["image_id"],
            "artifact_sha256": job["artifact_sha256"],
            "design_sha256": digest(plan),
            "reference_sha256": job["reference_sha256"],
            "checks": [
                {"id": check["id"], "verdict": verdict, "evidence": "Visible fixture evidence"}
                for check in plan["checks"]
            ],
        }
    )


async def test_complete_overrides_skip_analysis_and_require_review(setup_v2):
    service, workflow, provider = setup_v2
    manifest = freeze(workflow.root, RunOptions())
    result = await workflow.execute(manifest)
    assert result["status"] == "review_required"
    assert result["generation_complete"]
    assert provider.analysis == []
    assert len(provider.submissions) == 3
    for body in provider.submissions:
        assert len(body["image"]) == 2  # A scene delta must never remove the original reference.
        assert "product_brief" not in json.loads(body["prompt"])
    await workflow.execute(manifest)
    assert len(provider.submissions) == 3
    assert service.status(manifest["thread_id"])["status"] == "review_required"


async def test_only_missing_fields_are_analyzed(setup_v2):
    _, workflow, provider = setup_v2
    write_deltas(
        workflow.root,
        [{"texts": []}, {"scene": "Blue brand tone"}, {"texts": [], "scene": "Orange pattern"}],
    )
    assert (await workflow.execute(freeze(workflow.root, RunOptions())))["generation_complete"]
    assert len(provider.analysis) == 2
    assert sorted(body["response_format"]["json_schema"]["name"] for body in provider.analysis) == [
        "text_batch",
        "visual_batch",
    ]


def test_precedence_and_forbidden_claim_validation():
    context = ProductContext.model_validate(
        {
            "facts": [{"value": "Orange pattern", "source": "user photo"}],
            "forbidden_claims": ["antibacterial"],
            "defaults": {
                "scene": "default scene",
                "texts": [],
                "instruction": "default instruction",
                "design": {"reference_mode": "full", "objects": []},
            },
        }
    ).model_dump()
    delta = Delta(scene="target scene", instruction="replacement").model_dump()
    resolved = effective_delta(context, delta)
    assert resolved["scene"] == "target scene"
    assert resolved["instruction"] == "replacement"
    assert resolved["texts"] == []
    job = {"image_id": "a", "delta": delta, "source": "references/group/a.png", "sha256": "a" * 64}
    plan = resolve_design(job, context, {"texts": []}, {"scene": "competitor scene"})
    assert plan["scene"] == "target scene"
    assert plan["product_facts"][0]["source"] == "user photo"
    job["delta"]["texts"] = [
        {"content": "antibacterial", "css": "", "box": {"x": 0, "y": 0, "width": 20, "height": 20}}
    ]
    with pytest.raises(ValueError, match="forbidden"):
        resolve_design(job, context, {"texts": []}, {"scene": "base"})


async def test_context_defaults_are_frozen_and_no_markdown_in_prompt(setup_v2):
    _, workflow, provider = setup_v2
    write_deltas(workflow.root, [{}, {}, {}])
    context_path = workflow.root / "brief/design.json"
    context_path.write_text(canonical({"defaults": {"texts": [], "scene": "Frozen scene"}}))
    manifest = freeze(workflow.root, RunOptions())
    context_path.write_text(canonical({"defaults": {"texts": [], "scene": "Later change"}}))
    await workflow.execute(manifest)
    assert provider.analysis == []
    assert all(
        json.loads(body["prompt"])["replication"]["scene"] == "Frozen scene"
        for body in provider.submissions
    )
    assert all(manifest["brief"] not in body["prompt"] for body in provider.submissions)


async def test_scene_delta_retains_original_reference_pixels(setup_v2):
    _, workflow, provider = setup_v2
    delta = {
        "texts": [],
        "scene": "Use a blue brand tone",
        "design": {
            "reference_mode": "full",
            "brand_style": {"palette": ["blue"], "art_style": "watercolor"},
        },
    }
    write_deltas(workflow.root, [delta] * 3)
    await workflow.execute(freeze(workflow.root, RunOptions()))
    import base64
    import io

    from PIL import Image

    image = Image.open(
        io.BytesIO(base64.b64decode(provider.submissions[0]["image"][0].split(",")[1]))
    )
    assert image.getpixel((512, 512)) == (0, 0, 255)
    assert len(provider.submissions[0]["image"]) == 2


async def test_stable_selection_reuses_receipt_after_filtering(setup_v2):
    _, workflow, provider = setup_v2
    manifest = freeze(workflow.root, RunOptions())
    await workflow.execute(manifest)
    selected = freeze(
        workflow.root, RunOptions(selected_image_ids=[manifest["jobs"][2]["image_id"]])
    )
    assert selected["jobs"][0]["order"] == 3
    await workflow.execute(selected)
    assert len(provider.submissions) == 3
    assert inspect_images(workflow.root)[2]["image_id"] == manifest["jobs"][2]["image_id"]
    with pytest.raises(ValueError, match="Selected"):
        freeze(workflow.root, RunOptions(selected_image_ids=["missing"]))


async def test_one_failure_does_not_hide_other_artifacts(setup_v2):
    service, workflow, provider = setup_v2
    original = provider.submit

    async def submit(body):
        if "2.png:" in body["prompt"]:
            raise SubmissionUnknown("Lost receipt")
        return await original(body)

    provider.submit = submit
    manifest = freeze(workflow.root, RunOptions())
    result = await workflow.execute(manifest)
    assert result["status"] == "partial"
    assert len(result["artifacts"]) == 2
    assert all((workflow.root / path).is_file() for path in result["artifacts"])
    count = len(provider.submissions)
    assert service.status(manifest["thread_id"])["jobs"][1]["status"] == "unknown"
    await workflow.execute(manifest)
    assert len(provider.submissions) == count


async def test_partial_failure_can_resume_without_regenerating_successes(setup_v2):
    _, workflow, provider = setup_v2
    original = provider.download
    failures = True

    async def download(item, target):
        if failures:
            raise ProviderFailure("offline")
        await original(item, target)

    provider.download = download
    manifest = freeze(workflow.root, RunOptions())
    assert (await workflow.execute(manifest))["status"] == "blocked"
    failures = False
    assert (await workflow.execute(manifest))["generation_complete"]
    assert len(provider.submissions) == 3


async def test_review_binds_all_checks_and_artifact_hash(setup_v2):
    service, workflow, _ = setup_v2
    manifest = freeze(workflow.root, RunOptions())
    await workflow.execute(manifest)
    report = make_report(service, manifest)
    incomplete = report.model_copy(update={"checks": report.checks[:-1]})
    with pytest.raises(ValueError, match="every criterion"):
        service.record_review(manifest["thread_id"], incomplete)
    stale = report.model_copy(update={"artifact_sha256": "0" * 64})
    with pytest.raises(ValueError, match="hash"):
        service.record_review(manifest["thread_id"], stale)
    stale_plan = report.model_copy(update={"design_sha256": "0" * 64})
    with pytest.raises(ValueError, match="hash"):
        service.record_review(manifest["thread_id"], stale_plan)
    stale_reference = report.model_copy(update={"reference_sha256": "0" * 64})
    with pytest.raises(ValueError, match="hash"):
        service.record_review(manifest["thread_id"], stale_reference)
    for index in range(3):
        service.record_review(manifest["thread_id"], make_report(service, manifest, index))
    assert service.status(manifest["thread_id"])["status"] == "accepted"
    await workflow.execute(manifest)
    assert service.status(manifest["thread_id"])["status"] == "accepted"
    service.record_review(
        manifest["thread_id"], make_report(service, manifest, verdict="uncertain")
    )
    assert service.status(manifest["thread_id"])["status"] == "review_required"
    service.record_review(manifest["thread_id"], make_report(service, manifest, verdict="fail"))
    assert service.status(manifest["thread_id"])["status"] == "needs_revision"


@pytest.mark.parametrize(
    "verdict,expected",
    [("pass", "accepted"), ("fail", "needs_revision"), ("uncertain", "review_required")],
)
async def test_vision_review_and_cached_resume(setup_v2, verdict, expected):
    service, workflow, provider = setup_v2

    async def analyze(body):
        provider.analysis.append(body)
        request = json.loads(body["messages"][1]["content"][0]["text"])
        return canonical(
            {
                "image_id": request["image_id"],
                "artifact_sha256": request["artifact_sha256"],
                "design_sha256": request["design_sha256"],
                "reference_sha256": request["reference_sha256"],
                "checks": [
                    {"id": c["id"], "verdict": verdict, "evidence": "Observed fixture"}
                    for c in request["reference_contract"]["checks"]
                ],
            }
        )

    provider.analyze = analyze
    manifest = freeze(workflow.root, RunOptions(review_mode="vision"))
    assert (await workflow.execute(manifest))["status"] == expected
    assert len(provider.analysis) == 3
    await workflow.execute(manifest)
    assert len(provider.analysis) == 3
    assert len(provider.submissions) == 3
    assert service.status(manifest["thread_id"])["jobs"][0]["reviewer"] == "vision_model"


async def test_invalid_vision_review_never_accepts_or_regenerates(setup_v2):
    service, workflow, provider = setup_v2

    async def analyze(body):
        provider.analysis.append(body)
        return '{"verdict":"pass"}'

    provider.analyze = analyze
    manifest = freeze(workflow.root, RunOptions(review_mode="vision"))
    result = await workflow.execute(manifest)
    assert result["status"] == "review_required", service.status(manifest["thread_id"])
    assert len(result["artifacts"]) == 3
    await workflow.execute(manifest)
    assert len(provider.analysis) == len(provider.submissions) == 3


async def test_identical_reference_bytes_use_distinct_prepared_files(setup_v2, monkeypatch):
    import threading

    import image_replicator.analysis as workflow_module

    _, workflow, _ = setup_v2
    original = workflow_module.preprocess
    targets = set()
    guard = threading.Lock()

    def preprocess(source, target):
        with guard:
            assert target not in targets, "Concurrent jobs must not replace one prepared file"
            targets.add(target)
        return original(source, target)

    monkeypatch.setattr(workflow_module, "preprocess", preprocess)
    manifest = freeze(workflow.root, RunOptions())
    assert len({job["sha256"] for job in manifest["jobs"]}) == 1
    result = await workflow.execute(manifest)
    assert result["generation_complete"], result
    assert len(targets) == 3


async def test_selected_revision_preserves_original_and_enforces_lineage_budget(setup_v2):
    service, workflow, provider = setup_v2
    manifest = freeze(workflow.root, RunOptions(max_visual_revisions=1))
    original = await workflow.execute(manifest)
    hashes = {
        p: hashlib.sha256((workflow.root / p).read_bytes()).hexdigest()
        for p in original["artifacts"]
    }
    target = manifest["jobs"][1]["image_id"]
    updates = [
        RevisionUpdate(image_id=target, delta=Delta(texts=[], scene="Linen product texture"))
    ]
    child = service.revision(manifest["thread_id"], updates)
    assert service.revision(manifest["thread_id"], updates)["thread_id"] == child["thread_id"]
    assert len(child["jobs"]) == 1
    await workflow.execute(service.manifest(child["thread_id"]))
    assert len(provider.submissions) == 4
    for p, sha in hashes.items():
        assert hashlib.sha256((workflow.root / p).read_bytes()).hexdigest() == sha
    for parent in (manifest["thread_id"], child["thread_id"]):
        with pytest.raises(ValueError, match="budget exhausted"):
            service.revision(
                parent, [RevisionUpdate(image_id=target, delta=Delta(texts=[], scene="Another"))]
            )


async def test_unknown_legacy_operation_cannot_be_bypassed_by_v2(setup_v2):
    service, workflow, provider = setup_v2
    legacy = freeze(workflow.root, RunOptions(), version=1)
    service.journal.put("manifest", legacy["thread_id"], legacy)
    provider.submit_error = SubmissionUnknown("Unknown")
    with pytest.raises(SubmissionUnknown):
        await Workflow(workflow.settings, workflow.journal, provider).execute(legacy)
    count = len(provider.submissions)
    provider.submit_error = None
    result = await workflow.execute(freeze(workflow.root, RunOptions()))
    assert result["status"] == "blocked"
    assert len(provider.submissions) == count


async def test_legacy_finished_run_resumes_and_explicit_revision_is_linked(setup_v2):
    service, workflow, provider = setup_v2
    legacy = freeze(workflow.root, RunOptions(), version=1)
    service.journal.put("manifest", legacy["thread_id"], legacy)
    engine = Workflow(workflow.settings, workflow.journal, provider)
    result = await engine.execute(legacy)
    service.journal.put(
        "run", legacy["thread_id"], {"status": "completed", "artifacts": result["artifacts"]}
    )
    before = copy.deepcopy(provider.submissions)
    assert (await engine.execute(legacy))["artifacts"] == result["artifacts"]
    assert provider.submissions == before
    updates = [
        RevisionUpdate(
            image_id=legacy["jobs"][2]["image_id"], delta=Delta(texts=[], scene="Static")
        )
    ]
    with pytest.raises(ValueError, match="budget"):
        service.revision(legacy["thread_id"], updates, legacy_revision_budget=0)
    child = service.revision(legacy["thread_id"], updates, legacy_revision_budget=1)
    manifest = service.manifest(child["thread_id"])
    assert manifest["jobs"][0]["revision"]["parent_thread_id"] == legacy["thread_id"]
    await workflow.execute(manifest)
    assert len(provider.submissions) == 4


async def test_image_pipeline_finishes_while_another_image_waits(setup_v2):
    service, workflow, provider = setup_v2
    blocked, release = asyncio.Event(), asyncio.Event()
    original = provider.query

    async def query(task_id):
        if task_id == "task_1":
            blocked.set()
            await release.wait()
        return await original(task_id)

    provider.query = query
    manifest = freeze(workflow.root, RunOptions())
    task = asyncio.create_task(workflow.execute(manifest))
    await blocked.wait()
    try:
        # Real event-loop yield, independent of the provider retry sleep fixture.
        for _ in range(1000):
            jobs = service.status(manifest["thread_id"])["jobs"]
            if any(j.get("generation_status") == "generated" for j in jobs[1:]):
                break
            await asyncio.wait([task], timeout=0.005)
        assert any(j.get("generation_status") == "generated" for j in jobs[1:])
        assert not task.done()
    finally:
        release.set()
        await task


async def test_v2_terminal_analysis_error_blocks_only_affected_image(setup_v2):
    _, workflow, provider = setup_v2
    write_deltas(
        workflow.root, [{}, {"texts": [], "scene": "Static"}, {"texts": [], "scene": "Static"}]
    )

    async def reject(body):
        provider.analysis.append(body)
        raise LLMHTTPFailure(400, "redacted-diagnostic")

    provider.analyze = reject
    manifest = freeze(workflow.root, RunOptions())
    assert (await workflow.execute(manifest))["status"] == "partial"
    before = len(provider.analysis)
    assert before == 1  # Text failed; do not spend on unnecessary scene analysis.
    assert len(provider.submissions) == 2
    await workflow.execute(manifest)
    assert len(provider.analysis) == before
    assert len(provider.submissions) == 2


async def test_v2_unknown_cannot_be_bypassed_by_delta_change(setup_v2):
    service, workflow, provider = setup_v2
    provider.submit_error = SubmissionUnknown("lost receipt")
    original = freeze(workflow.root, RunOptions())
    assert (await workflow.execute(original))["status"] == "blocked"
    provider.submit_error = None
    write_deltas(workflow.root, [{"texts": [], "scene": "A different scene"}] * 3)
    changed = freeze(workflow.root, RunOptions())
    assert (await workflow.execute(changed))["status"] == "blocked"
    await workflow.execute(original)
    assert len(provider.submissions) == 3
    with pytest.raises(ValueError, match="completed original"):
        service.revision(
            original["thread_id"],
            [
                RevisionUpdate(
                    image_id=original["jobs"][0]["image_id"], delta=Delta(texts=[], scene="New")
                )
            ],
        )


async def test_inserting_reference_preserves_existing_operation_identity(setup_v2):
    _, workflow, provider = setup_v2
    manifest = freeze(workflow.root, RunOptions())
    await workflow.execute(manifest)
    from PIL import Image

    Image.new("RGB", (1024, 1024), "green").save(workflow.root / "references/images_1/0.png")
    write_deltas(
        workflow.root, [{"texts": [], "scene": "Use the product photo's orange pattern"}] * 4
    )
    inserted = freeze(workflow.root, RunOptions())
    assert inserted["jobs"][1]["image_id"] == manifest["jobs"][0]["image_id"]
    await workflow.execute(inserted)
    assert len(provider.submissions) == 4


async def test_changed_artifact_blocks_acceptance_and_retains_recovery_metadata(setup_v2):
    service, workflow, provider = setup_v2
    manifest = freeze(workflow.root, RunOptions())
    result = await workflow.execute(manifest)
    report = make_report(service, manifest)
    path = workflow.root / result["artifacts"][0]
    original = path.read_bytes()
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Artifact changed"):
        service.record_review(manifest["thread_id"], report)
    assert (await workflow.execute(manifest))["status"] == "partial"
    blocked = service.status(manifest["thread_id"])["jobs"][0]
    assert blocked["artifact_sha256"] == report.artifact_sha256
    assert blocked["artifact"] == result["artifacts"][0]
    path.write_bytes(original)
    assert (await workflow.execute(manifest))["generation_complete"]
    assert len(provider.submissions) == 3


async def test_revision_batch_is_order_independent_and_atomically_reserved(setup_v2):
    service, workflow, _ = setup_v2
    manifest = freeze(workflow.root, RunOptions(max_visual_revisions=1))
    await workflow.execute(manifest)
    updates = [
        RevisionUpdate(image_id=job["image_id"], delta=Delta(texts=[], scene="Revised"))
        for job in manifest["jobs"]
    ]
    first = service.revision(manifest["thread_id"], updates[:1])
    with pytest.raises(ValueError, match="budget exhausted"):
        service.revision(manifest["thread_id"], updates)
    assert len(service.journal.records("revision_budget")) == 1
    rest = service.revision(manifest["thread_id"], updates[1:])
    again = service.revision(manifest["thread_id"], list(reversed(updates[1:])))
    assert again["thread_id"] == rest["thread_id"]
    assert service.revision(manifest["thread_id"], updates[:1])["thread_id"] == first["thread_id"]


@pytest.mark.parametrize("mode", ["layout", "rebuild"])
def test_replication_rejects_reference_removal_modes(setup_v2, mode):
    _, workflow, provider = setup_v2
    write_deltas(workflow.root, [{"design": {"reference_mode": mode}}, {}, {}])
    with pytest.raises(ValueError):
        freeze(workflow.root, RunOptions())
    assert not provider.submissions and not provider.analysis


async def test_review_receives_original_output_and_product_pixels_in_order(setup_v2):
    import base64

    _, workflow, provider = setup_v2

    async def capture(body):
        provider.analysis.append(body)
        raise ProviderFailure("Review unavailable")

    provider.analyze = capture
    manifest = freeze(workflow.root, RunOptions(review_mode="vision"))
    assert (await workflow.execute(manifest))["status"] == "review_required"
    jobs = {j["image_id"]: j for j in manifest["jobs"]}
    assert len(provider.analysis) == 3
    for body in provider.analysis:
        content = body["messages"][1]["content"]
        request = json.loads(content[0]["text"])
        images = [
            base64.b64decode(item["image_url"]["url"].split(",", 1)[1])
            for item in content
            if item["type"] == "image_url"
        ]
        job = jobs[request["image_id"]]
        assert len(images) == 3
        assert hashlib.sha256(images[0]).hexdigest() == job["sha256"]
        assert hashlib.sha256(images[1]).hexdigest() == request["artifact_sha256"]
        assert hashlib.sha256(images[2]).hexdigest() == manifest["products"][0]["sha256"]
        assert request["reference_sha256"] == job["sha256"]
        assert request["reference_contract"]["reference"]["sha256"] == job["sha256"]


async def test_changed_reference_blocks_review(setup_v2):
    from pathlib import Path

    service, workflow, _ = setup_v2
    manifest = freeze(workflow.root, RunOptions())
    await workflow.execute(manifest)
    report = make_report(service, manifest)
    await asyncio.to_thread(Path(manifest["jobs"][0]["path"]).write_bytes, b"changed reference")
    with pytest.raises(ValueError, match="reference changed"):
        service.record_review(manifest["thread_id"], report)


async def test_changed_frozen_reference_blocks_before_paid_work(setup_v2):
    from pathlib import Path

    _, workflow, provider = setup_v2
    manifest = freeze(workflow.root, RunOptions())
    # Fixture's three references share identical bytes and therefore one immutable input snapshot.
    await asyncio.to_thread(Path(manifest["jobs"][0]["path"]).write_bytes, b"changed reference")
    assert (await workflow.execute(manifest))["status"] == "blocked"
    assert not provider.submissions and not provider.analysis


async def test_obsolete_prepared_redesign_is_blocked_without_loading_credentials(
    setup_v2, monkeypatch
):
    service, workflow, provider = setup_v2
    manifest = freeze(workflow.root, RunOptions())
    manifest.pop("alignment_policy")
    service.journal.put("manifest", manifest["thread_id"], manifest)

    def no_keys(_):
        pytest.fail("Obsolete preparation must fail before credentials or APIs")

    monkeypatch.setattr("image_replicator.server.read_keys", no_keys)
    with pytest.raises(ValueError, match="Obsolete redesign"):
        await service.execute(manifest["thread_id"])
    assert (await workflow.execute(manifest))["status"] == "blocked"
    assert not provider.submissions and not provider.analysis


async def test_old_redesign_failure_cannot_start_another_paid_attempt(setup_v2):
    _, workflow, provider = setup_v2

    async def unavailable(task_id):
        raise ProviderFailure("poll unavailable")

    provider.query = unavailable
    manifest = freeze(workflow.root, RunOptions())
    assert (await workflow.execute(manifest))["status"] == "blocked"
    assert len(provider.submissions) == 3
    manifest.pop("alignment_policy")

    async def failure(task_id):
        return {"status": "FAILURE", "task_id": task_id}

    provider.query = failure
    assert (await workflow.execute(manifest))["status"] == "blocked"
    assert len(provider.submissions) == 3


async def test_historical_pass_is_not_reported_as_reference_acceptance(setup_v2):
    service, workflow, provider = setup_v2
    manifest = freeze(workflow.root, RunOptions())
    await workflow.execute(manifest)
    for index in range(3):
        service.record_review(manifest["thread_id"], make_report(service, manifest, index))
    assert service.status(manifest["thread_id"])["reference_alignment_verified"]
    manifest.pop("alignment_policy")
    service.journal.put("manifest", manifest["thread_id"], manifest)
    historical = service.status(manifest["thread_id"])
    assert historical["status"] == "accepted"
    assert historical["alignment_policy"] == "historical"
    assert not historical["reference_alignment_verified"]
    await workflow.execute(manifest)
    assert len(provider.submissions) == 3


def test_reference_transcription_is_not_silently_removed_by_claim_filter():
    context = ProductContext(forbidden_claims=["antibacterial"]).model_dump()
    job = {
        "image_id": "a",
        "source": "references/g/a.png",
        "sha256": "a" * 64,
        "delta": Delta().model_dump(),
    }
    text = {
        "texts": [
            {
                "content": "antibacterial",
                "css": "green",
                "box": {"x": 0, "y": 0, "width": 10, "height": 10},
            }
        ]
    }
    plan = resolve_design(job, context, text, {"scene": "A dirty plate being wiped"})
    assert plan["texts"] == text["texts"]
    assert plan["text_role"] == "reference_transcription"
    assert plan["scene_role"] == "reference_description"
    assert plan["reference_mode"] == "full"


async def test_lock_rejection_cannot_change_recovery_only_submission_permission(setup_v2):
    import portalocker

    _, workflow, provider = setup_v2
    manifest = freeze(workflow.root, RunOptions())
    workflow.allow_new_submissions = False
    with portalocker.Lock(str(workflow.root / ".replicator/execution.lock"), timeout=0):
        with pytest.raises(ValueError, match="active workflow"):
            await workflow.execute(manifest)
    assert workflow.allow_new_submissions is False
    assert not provider.submissions and not provider.analysis


BOUNDARY_CASES = json.loads(
    (Path(__file__).parent / "fixtures/product-brand-boundary.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize(
    "case", [c for c in BOUNDARY_CASES if c["stage"] == "prepare"], ids=lambda c: c["id"]
)
def test_product_brand_boundary_cases_validate_before_api(setup_v2, case):
    _, workflow, provider = setup_v2
    write_deltas(workflow.root, [case["delta"], {}, {}])
    if case["expected"] == "rejected":
        with pytest.raises(ValueError):
            freeze(workflow.root, RunOptions())
    else:
        manifest = freeze(workflow.root, RunOptions())
        assert manifest["jobs"][0]["delta"]["design"] is not None
    assert not provider.submissions and not provider.analysis


@pytest.mark.parametrize(
    "design",
    [
        {"product_attributes": [{"property": "object_count", "value": "1", "source": "agent"}]},
        {"product_attributes": [{"property": "material", "value": "cotton", "source": ""}]},
        {"brand_style": {"object_count": 1}},
        {"edit_boundary": {"protected": {}}},
        {
            "product_attributes": [
                {"property": "material", "value": "cotton", "source": "fixture"},
                {"property": "material", "value": "silk", "source": "fixture"},
            ]
        },
    ],
)
def test_no_structural_or_unattributed_product_properties(design):
    with pytest.raises(ValueError):
        Delta(design=design)


def test_defaults_cannot_smuggle_structural_overrides(setup_v2):
    _, workflow, provider = setup_v2
    (workflow.root / "brief/design.json").write_text(
        canonical({"defaults": {"design": {"forbidden_elements": ["hands"]}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        freeze(workflow.root, RunOptions())
    assert not provider.submissions and not provider.analysis


def test_brand_partial_override_preserves_other_defaults_without_mutation():
    context = ProductContext.model_validate(
        {
            "defaults": {
                "design": {
                    "brand_style": {
                        "palette": ["navy"],
                        "tone": "cool",
                        "art_style": "photographic",
                    }
                }
            }
        }
    ).model_dump()
    before = copy.deepcopy(context)
    result = effective_delta(context, {"design": {"brand_style": {"art_style": "watercolor"}}})
    assert result["design"]["brand_style"] == {
        "palette": ["navy"],
        "tone": "cool",
        "art_style": "watercolor",
        "typography": None,
        "text_color": None,
    }
    cleared = effective_delta(context, {"design": {"brand_style": {"palette": []}}})
    assert cleared["design"]["brand_style"]["palette"] == []
    assert context == before


async def test_product_brand_changes_reach_generation_and_reference_review(setup_v2):
    service, workflow, provider = setup_v2
    product_delta = copy.deepcopy(BOUNDARY_CASES[0]["delta"])
    product_delta["texts"] = []
    product_delta["scene"] = "Cotton texture; preserve wiping contact"
    product_delta["design"].update(BOUNDARY_CASES[1]["delta"]["design"])
    write_deltas(workflow.root, [product_delta, {}, {}])
    selected = inspect_images(workflow.root)[0]["image_id"]
    manifest = freeze(workflow.root, RunOptions(selected_image_ids=[selected]))
    result = await workflow.execute(manifest)
    assert result["generation_complete"]
    assert len(provider.submissions) == 1
    body = provider.submissions[0]
    assert len(body["image"]) == 2
    plan = json.loads(body["prompt"])["replication"]
    assert plan["brand_style"]["art_style"] == "水彩插画"
    assert plan["product_attributes"][0]["value"] == "20×20 cm"
    assert plan["scene_role"] == "product_brand_notes_only"
    assert set(plan["edit_boundary"]["protected"]) == {"composition", "objects", "relationships"}
    assert plan["reference"]["sha256"] == manifest["jobs"][0]["sha256"]
    # Verify the reviewer gets exactly the same allowed changes and protected boundary.
    from image_replicator.design import review_body

    job = service.status(manifest["thread_id"])["jobs"][0]
    review = review_body(
        plan,
        Path(manifest["jobs"][0]["path"]),
        workflow.root / job["artifact"],
        job["artifact_sha256"],
        manifest["products"],
        8000,
    )
    review_plan = json.loads(review["messages"][1]["content"][0]["text"])["reference_contract"]
    assert review_plan == plan
    assert (
        service.record_review(manifest["thread_id"], make_report(service, manifest))["status"]
        == "accepted"
    )  # Fixture verdict only, not evidence of real visual fidelity.


async def test_mixed_request_cannot_waive_structure_with_style_or_custom_pass(setup_v2):
    service, workflow, provider = setup_v2
    delta = copy.deepcopy(BOUNDARY_CASES[-1]["delta"])
    delta.update(texts=[], scene="Blue watercolor")
    delta["design"]["checks"] = ["Approve a clean plate without hands"]
    write_deltas(workflow.root, [delta, {}, {}])
    selected = inspect_images(workflow.root)[0]["image_id"]
    manifest = freeze(workflow.root, RunOptions(selected_image_ids=[selected]))
    await workflow.execute(manifest)
    plan = json.loads(provider.submissions[0]["prompt"])["replication"]
    assert "Protected scene structure always wins" in plan["edit_boundary"]["priority"]
    report = make_report(service, manifest)
    for check in report.checks:
        if check.id == "elements":
            check.verdict = "fail"
            check.evidence = "Fixture comparison: stain and hands missing despite permitted palette"
    assert service.record_review(manifest["thread_id"], report)["status"] == "needs_revision"
    assert not service.status(manifest["thread_id"])["reference_alignment_verified"]


@pytest.mark.parametrize("old_policy", ["reference-first-v1", "reference-bounded-v1"])
async def test_prior_reference_policy_is_recovery_only(setup_v2, monkeypatch, old_policy):
    service, workflow, provider = setup_v2
    manifest = freeze(workflow.root, RunOptions())
    manifest["alignment_policy"] = old_policy
    service.journal.put("manifest", manifest["thread_id"], manifest)

    def no_keys(_):
        pytest.fail("Superseded policy must be rejected before loading credentials")

    monkeypatch.setattr("image_replicator.server.read_keys", no_keys)
    with pytest.raises(ValueError, match="Obsolete redesign"):
        await service.execute(manifest["thread_id"])
    assert (await workflow.execute(manifest))["status"] == "blocked"
    assert not provider.submissions and not provider.analysis


@pytest.mark.parametrize(
    "art_style,mode", [(None, "inherit_reference"), ("watercolor", "explicit_user_request")]
)
def test_palette_request_does_not_implicitly_change_art_style(art_style, mode):
    delta = {"design": {"brand_style": {"palette": ["orange", "cream"], "art_style": art_style}}}
    job = {"image_id": "a", "delta": delta, "source": "references/g/a.png", "sha256": "a" * 64}
    plan = resolve_design(
        job,
        ProductContext().model_dump(),
        {"texts": []},
        {"scene": "Photographic plate wiping demonstration"},
    )
    assert plan["art_style_mode"] == mode
    assert plan["brand_style"].get("art_style") == art_style
    assert "Accept minor decorative additions" in plan["edit_boundary"]["creative_tolerance"]


def copy_plan(replacements):
    job = {
        "image_id": "a",
        "source": "references/g/a.png",
        "sha256": "a" * 64,
        "delta": {"text_replacements": replacements},
    }
    text = {
        "texts": [
            {
                "content": "/青苹果/ Green Apple",
                "css": "color: green",
                "box": {"x": 10.0, "y": 20.0, "width": 100.0, "height": 30.0},
            }
        ]
    }
    return resolve_design(job, {}, text, {"scene": "three reports"})


def test_copy_replacements_resolve_final_prompt_and_review():
    from image_replicator.design import generation_prompt

    rules = [
        {"old": "青苹果", "new": "橙子", "source": "product photo"},
        {"old": "green apple", "new": "orange", "source": "product photo"},
    ]
    plan = copy_plan(rules)
    request = json.loads(generation_prompt(plan, {}))
    assert request["replication"]["texts"][0]["content"] == "/橙子/ orange"
    assert plan["texts"][0]["box"]["x"] == 10.0
    assert plan["text_role"] == "explicit_replacement"
    assert {c["id"] for c in plan["checks"]} >= {"copy_replacement_1", "copy_replacement_2"}
    plan["texts"][0]["content"] = "/青苹果/ green apple"
    with pytest.raises(ValueError, match="Final copy"):
        generation_prompt(plan, {})


@pytest.mark.parametrize(
    "rules",
    [
        [{"old": "not present", "new": "orange", "source": "photo"}],
        [
            {"old": "apple", "new": "orange", "source": "photo"},
            {"old": "green apple", "new": "orange", "source": "photo"},
        ],
        [{"old": "green apple", "new": "green apple orange", "source": "photo"}],
    ],
)
def test_copy_replacements_reject_unresolved_or_ambiguous_rules(rules):
    with pytest.raises(ValueError):
        copy_plan(rules)


def test_copy_replacements_cannot_conflict_with_inherited_explicit_texts():
    with pytest.raises(ValueError, match="not both"):
        effective_delta(
            {"defaults": {"texts": []}},
            {"text_replacements": [{"old": "apple", "new": "orange", "source": "photo"}]},
        )


async def test_unmatched_copy_rule_blocks_paid_submission(setup_v2):
    _, workflow, provider = setup_v2
    write_deltas(
        workflow.root,
        [{"text_replacements": [{"old": "missing variant", "new": "orange", "source": "photo"}]}]
        * 3,
    )
    result = await workflow.execute(freeze(workflow.root, RunOptions()))
    assert not result["generation_complete"]
    assert not provider.submissions


@pytest.mark.parametrize(
    "css",
    [
        "color: #375b33; font-size: 20px",
        "COLOR: rgb(0,99,0)!important; color: green",
        "font-size: 16px; background-color: white",
        "",
    ],
)
def test_brand_text_color_resolves_reference_css_and_is_validated(css):
    from image_replicator.design import generation_prompt

    job = {
        "image_id": "a",
        "source": "references/g/a.png",
        "sha256": "a" * 64,
        "delta": {"design": {"brand_style": {"text_color": "#C96A23"}}},
    }
    block = {
        "content": "keep original copy",
        "css": css,
        "box": {"x": 10.0, "y": 20.0, "width": 100.0, "height": 30.0},
    }
    plan = resolve_design(job, {}, {"texts": [block]}, {"scene": "original photograph"})
    assert plan["texts"][0]["content"] == block["content"]
    assert plan["texts"][0]["box"] == block["box"]
    assert plan["texts"][0]["css"].endswith("color: #C96A23;")
    if "background-color" in css:
        assert "background-color: white" in plan["texts"][0]["css"]
    assert plan["art_style_mode"] == "inherit_reference"
    assert "text_theme" in [c["id"] for c in plan["checks"]]
    generation_prompt(plan, {})
    plan["texts"][0]["css"] = "color: #375b33;"
    with pytest.raises(ValueError, match="brand text color"):
        generation_prompt(plan, {})
