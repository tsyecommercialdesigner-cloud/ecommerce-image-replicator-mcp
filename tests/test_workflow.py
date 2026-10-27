import base64
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from image_replicator.config import Settings
from image_replicator.inputs import freeze
from image_replicator.models import RunOptions
from image_replicator.provider import ProviderFailure, SafeToRetry, SubmissionUnknown
from image_replicator.storage import Journal, atomic_write
from image_replicator.workflow import Workflow


class FakeProvider:
    def __init__(self):
        self.analysis = []
        self.submissions = []
        self.download_fail = False
        self.submit_error = None
        self.misorder = False
        self.fail_primary = False

    async def analyze(self, body):
        self.analysis.append(body)
        if self.fail_primary and body["model"] == "gemini-3.8-flash":
            raise ProviderFailure("Temporary LLM failure")
        ids = [
            json.loads(p["text"])["image_id"]
            for p in body["messages"][1]["content"]
            if p["type"] == "text"
        ]
        if self.misorder:
            ids = list(reversed(ids))
        is_text = body["response_format"]["json_schema"]["name"] == "text_batch"
        return json.dumps(
            {
                "images": [
                    {
                        "image_id": id,
                        **(
                            {"texts": []}
                            if is_text
                            else {"scene": "A product centered against a white background"}
                        ),
                    }
                    for id in ids
                ]
            }
        )

    async def submit(self, body):
        self.submissions.append(body)
        if self.submit_error:
            raise self.submit_error
        return "task_" + str(len(self.submissions))

    async def query(self, task_id):
        index = int(task_id.split("_")[1]) - 1
        image = Image.new("RGB", tuple(map(int, self.submissions[index]["size"].split("x"))), "red")
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        return {
            "status": "SUCCESS",
            "task_id": task_id,
            "data": {"data": [{"b64_json": base64.b64encode(stream.getvalue()).decode()}]},
        }

    async def download(self, item, target):
        if self.download_fail:
            raise ProviderFailure("Download unavailable")
        atomic_write(target, base64.b64decode(item["b64_json"]))


@pytest.fixture
def setup(workspace, monkeypatch):
    async def no_delay(_):
        pass

    monkeypatch.setattr("image_replicator.workflow.asyncio.sleep", no_delay)
    manifest = freeze(workspace, RunOptions())
    settings = Settings(workspace, workspace, 10, 10_000_000, 8000, poll_seconds=0)
    journal = Journal(workspace / ".replicator/journal.sqlite")
    provider = FakeProvider()
    return Workflow(settings, journal, provider), manifest, provider


async def test_full_graph_and_sqlite_resume(setup):
    workflow, manifest, provider = setup
    result = await workflow.execute(manifest)
    assert len(result["artifacts"]) == 3
    assert len(provider.analysis) == 2  # text + visual, each batches all 3 images
    assert len(provider.submissions) == 3
    assert [Path(p).name for p in result["artifacts"]] == [
        "images_1_001_task_1.png",
        "images_1_002_task_2.png",
        "images_1_003_task_3.png",
    ]
    fresh_workflow = Workflow(workflow.settings, workflow.journal, provider)
    again = await fresh_workflow.execute(manifest)
    assert again["artifacts"] == result["artifacts"]
    assert len(provider.submissions) == 3
    assert len(provider.analysis) == 2


@pytest.mark.parametrize("family", ["gpt-image-2.5-flare", "gpt-image-2.5-sunburst"])
async def test_routes_actual_canvas_and_retains_model_on_resume(setup, family):
    workflow, _, provider = setup
    for name, size in [("1.png", (1024, 1024)), ("2.png", (2049, 2048)), ("10.png", (4096, 2016))]:
        Image.new("RGB", size, "blue").save(workflow.root / "references/images_1" / name)
    manifest = freeze(workflow.root, RunOptions(image_model=family))
    provider.download_fail = True
    with pytest.raises(ProviderFailure):
        await workflow.execute(manifest)
    expected = [family, family + "-2k", family + "-4k"]
    assert [body["model"] for body in provider.submissions] == expected
    # The 2049px source is resized to a 2048px canvas: route by the canvas, not source.
    assert provider.submissions[1]["size"] == "2048x2048"
    assert provider.submissions[2]["size"] == "4096x2016"
    for index, model in enumerate(expected):
        link = workflow.journal.get("run_job", f"{manifest['thread_id']}:{index}")
        assert workflow.journal.get("image", link["key"])["model"] == model
    provider.download_fail = False
    await Workflow(workflow.settings, workflow.journal, provider).execute(manifest)
    assert len(provider.submissions) == 3


async def test_legacy_unknown_operation_is_not_resubmitted_after_routing_change(setup):
    workflow, _, provider = setup
    Image.new("RGB", (2048, 1024), "blue").save(workflow.root / "references/images_1/1.png")
    manifest = freeze(workflow.root, RunOptions())
    provider.submit_error = SubmissionUnknown("Lost receipt")
    with pytest.raises(SubmissionUnknown):
        await workflow.execute(manifest)
    for index in range(3):
        link = workflow.journal.get("run_job", f"{manifest['thread_id']}:{index}")
        record = workflow.journal.get("image", link["key"])
        record.pop("model")  # Legacy journal entries did not store a resolved model.
        workflow.journal.put("image", link["key"], record)
    with pytest.raises(SubmissionUnknown):
        await workflow.execute(manifest)
    assert len(provider.submissions) == 3


async def test_download_failure_does_not_repeat_paid_submission(setup):
    workflow, manifest, provider = setup
    provider.download_fail = True
    with pytest.raises(ProviderFailure):
        await workflow.execute(manifest)
    assert len(provider.submissions) == 3
    provider.download_fail = False
    result = await Workflow(workflow.settings, workflow.journal, provider).execute(manifest)
    assert len(result["artifacts"]) == 3
    assert len(provider.submissions) == 3


async def test_ambiguous_submission_is_never_replayed(setup):
    workflow, manifest, provider = setup
    provider.submit_error = SubmissionUnknown("Connection lost after request")
    with pytest.raises(SubmissionUnknown):
        await workflow.execute(manifest)
    count = len(provider.submissions)
    provider.submit_error = None
    with pytest.raises(SubmissionUnknown):
        await Workflow(workflow.settings, workflow.journal, provider).execute(manifest)
    assert len(provider.submissions) == count


async def test_proven_preconnect_failure_max_three(setup):
    workflow, manifest, provider = setup
    provider.submit_error = SafeToRetry("No connection")
    with pytest.raises(ProviderFailure):
        await workflow.execute(manifest)
    assert len(provider.submissions) == 9
    with pytest.raises(ProviderFailure):
        await workflow.execute(manifest)
    assert len(provider.submissions) == 9


async def test_llm_fallback_after_three(setup):
    workflow, manifest, provider = setup
    provider.fail_primary = True
    await workflow.execute(manifest)
    models = [b["model"] for b in provider.analysis]
    assert models.count("gemini-3.8-flash") == 6
    assert models.count("gemini-3.7-flash") == 2


async def test_reordered_outputs_fail_before_generation(setup):
    workflow, manifest, provider = setup
    provider.misorder = True
    with pytest.raises(ProviderFailure):
        await workflow.execute(manifest)
    assert not provider.submissions
    count = len(provider.analysis)
    with pytest.raises(ProviderFailure):
        await workflow.execute(manifest)
    assert len(provider.analysis) == count


async def test_known_terminal_failure_retries_within_total_budget(setup):
    workflow, manifest, provider = setup

    async def failure(task_id):
        return {"status": "FAILURE", "task_id": task_id}

    provider.query = failure
    with pytest.raises(ProviderFailure):
        await workflow.execute(manifest)
    assert len(provider.submissions) == 9
    for index in range(3):
        link = workflow.journal.get("run_job", f"{manifest['thread_id']}:{index}")
        record = workflow.journal.get("image", link["key"])
        assert record["status"] == "failed"
        assert len(record["history"]) == 3
    with pytest.raises(ProviderFailure):
        await workflow.execute(manifest)
    assert len(provider.submissions) == 9


async def test_changed_delta_reuses_base_analysis(setup):
    workflow, manifest, provider = setup
    await workflow.execute(manifest)
    (workflow.root / "prompts/images_1.json").write_text('[{}, {}, {"instruction": "red"}]')
    updated = freeze(workflow.root, RunOptions())
    assert updated["thread_id"] != manifest["thread_id"]
    await workflow.execute(updated)
    assert len(provider.analysis) == 2
    assert len(provider.submissions) == 4  # only the modified job is regenerated


async def test_configured_batch_limit(setup):
    from dataclasses import replace

    workflow, manifest, provider = setup
    workflow.settings = replace(workflow.settings, max_batch_images=2)
    await workflow.execute(manifest)
    assert len(provider.analysis) == 4
    assert all(len(body["messages"][1]["content"]) <= 4 for body in provider.analysis)


async def test_cross_process_execution_lock(setup):
    import portalocker

    workflow, manifest, provider = setup
    with portalocker.Lock(str(workflow.root / ".replicator/execution.lock"), timeout=0):
        with pytest.raises(ValueError, match="active workflow"):
            await workflow.execute(manifest)
    assert not provider.submissions


async def test_crash_after_intent_before_receipt_blocks_resubmission(setup):
    workflow, manifest, provider = setup
    provider.submit_error = SubmissionUnknown("Crash")
    with pytest.raises(SubmissionUnknown):
        await workflow.execute(manifest)
    for index in range(3):
        link = workflow.journal.get("run_job", f"{manifest['thread_id']}:{index}")
        record = workflow.journal.get("image", link["key"])
        record["status"] = "submitting"  # simulate power loss before writing exception status
        workflow.journal.put("image", link["key"], record)
    count = len(provider.submissions)
    with pytest.raises(SubmissionUnknown):
        await workflow.execute(manifest)
    assert len(provider.submissions) == count
