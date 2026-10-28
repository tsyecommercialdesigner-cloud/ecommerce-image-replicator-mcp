import asyncio
import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import portalocker
import pytest
from PIL import Image
from test_workflow import FakeProvider

from image_replicator.config import Settings
from image_replicator.images import CanvasMismatch, geometry, postprocess, preprocess
from image_replicator.inputs import freeze
from image_replicator.models import RunOptions
from image_replicator.routing import WorkspaceRouter
from image_replicator.server import Service
from image_replicator.storage import canonical
from image_replicator.workflow_v2 import ImageWorkflow


@pytest.mark.parametrize("fmt", ["PNG", "JPEG"])
@pytest.mark.parametrize("size", [(1206, 1304), (1600, 1728), (400, 432), (800, 864)])
def test_canvas_normalization_restores_both_dimensions(tmp_path, fmt, size):
    raw = tmp_path / "raw.image"
    Image.new("RGB", size, "orange").save(raw, format=fmt)
    original = raw.read_bytes()
    transform = geometry(790, 857)
    assert transform["canvas"] == [800, 864]
    output = postprocess(raw, tmp_path / "final", transform)
    with Image.open(output) as image:
        assert image.size == (790, 857)
        assert image.format == fmt
    report = json.loads(output.with_suffix(".geometry.json").read_text())
    assert report["compensated"] == (list(size) != transform["canvas"])
    assert report["actual_size"] == list(size)
    assert report["final_size"] == [790, 857]
    assert raw.read_bytes() == original
    before = output.read_bytes()
    assert postprocess(raw, tmp_path / "final", transform).read_bytes() == before


def test_normalization_uses_padding_crop_and_rejects_distortion(tmp_path):
    source, prepared = tmp_path / "source.png", tmp_path / "prepared.png"
    Image.new("RGB", (790, 857), "red").save(source)
    transform = preprocess(source, prepared)
    with Image.open(prepared) as image:
        image.resize((1600, 1728)).save(tmp_path / "raw.png")
    output = postprocess(tmp_path / "raw.png", tmp_path / "final", transform)
    with Image.open(output) as image:
        # Padding must be removed, not stretched into the final reference rectangle.
        assert image.getpixel((395, 428)) == (255, 0, 0)
        assert image.getpixel((5, 5))[0] > 245
        assert image.getpixel((5, 5))[1] < 10
    original = output.read_bytes()
    Image.new("RGB", (800, 400)).save(tmp_path / "bad.png")
    with pytest.raises(CanvasMismatch) as caught:
        postprocess(tmp_path / "bad.png", tmp_path / "final", transform)
    assert caught.value.diagnostic["error_code"] == "provider_canvas_aspect_mismatch"
    assert output.read_bytes() == original
    Image.new("RGB", (800, 864), "blue").save(tmp_path / "changed.png")
    with pytest.raises(ValueError, match="overwrite"):
        postprocess(tmp_path / "changed.png", tmp_path / "final", transform)
    assert output.read_bytes() == original


@pytest.mark.parametrize("width,allowed", [(1009, True), (1010, True), (1011, False)])
def test_exact_one_percent_aspect_boundary(tmp_path, width, allowed):
    raw = tmp_path / "raw.png"
    Image.new("RGB", (width, 1000)).save(raw)
    transform = {"canvas": [1000, 1000], "original": [1000, 1000], "crop": [0, 0, 1000, 1000]}
    if allowed:
        assert postprocess(raw, tmp_path / "out", transform).is_file()
    else:
        with pytest.raises(CanvasMismatch):
            postprocess(raw, tmp_path / "out", transform)


@pytest.fixture
async def downloaded_run(workspace, monkeypatch):
    for i in range(11, 16):
        Image.new("RGB", (32, 32), "red").save(workspace / f"references/images_1/{i}.png")
    (workspace / "prompts/images_1.json").write_text(
        canonical([{"texts": [], "scene": "fixture"}] * 8), encoding="utf-8"
    )
    service = Service(Settings(workspace, workspace, poll_seconds=0))
    provider = FakeProvider()
    manifest = freeze(workspace, RunOptions(concurrency=1))
    import image_replicator.workflow as module

    real_postprocess = module.postprocess
    calls = 0

    def old_postprocess(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("Old strict canvas validation")
        return real_postprocess(*args)

    monkeypatch.setattr(module, "postprocess", old_postprocess)
    assert (await ImageWorkflow(service.settings, service.journal, provider).execute(manifest))[
        "status"
    ] == "partial"
    monkeypatch.setattr(module, "postprocess", real_postprocess)
    # Reproduce an old downloaded mismatched raw without stored geometry.
    key = service.journal.get("run_job", f"{manifest['thread_id']}:0")["key"]
    receipt = service.journal.get("image", key)
    receipt.pop("transform")
    service.journal.put("image", key, receipt)
    Image.new("RGB", (1536, 1536), "red").save(
        workspace / f".replicator/raw/{key}.image", format="PNG"
    )
    return service, manifest, provider, key


async def test_local_recovery_preserves_seven_successes_receipts_and_restarts(
    downloaded_run, monkeypatch
):
    service, manifest, provider, operation = downloaded_run
    thread = manifest["thread_id"]
    before_receipts = copy.deepcopy(service.journal.records("image"))
    before_results = dict(service.journal.records("job_result"))
    hashes = {
        r["artifact"]: hashlib.sha256(
            (service.settings.workspace / r["artifact"]).read_bytes()
        ).hexdigest()
        for r in before_results.values()
        if r.get("artifact")
    }

    def bomb(*args, **kwargs):
        raise AssertionError("Provider construction forbidden")

    monkeypatch.setattr("image_replicator.server.Provider", bomb)
    ids = [j["image_id"] for j in manifest["jobs"]]
    service.journal.put("run", thread, {"status": "running"})
    report = service.recover_postprocess(thread, ids)
    assert report["status"] == "ok"
    assert report["provider_calls"] == 0
    assert service.status(thread)["status"] == "review_required"
    assert [j["status"] for j in report["jobs"]] == ["recovered"] + ["generated_preserved"] * 7
    result = service.journal.get("job_result", f"{thread}:0")
    assert "error" not in result and "phase" not in result
    assert result["review_status"] == "review_required"
    assert result["postprocess"]["transform_source"] == "legacy_frozen_reference"
    assert service.journal.records("image") == before_receipts
    assert service.manifest(thread) == manifest
    for key, value in before_results.items():
        if key != f"{thread}:0":
            assert service.journal.get("job_result", key) == value
    for path, sha in hashes.items():
        assert hashlib.sha256((service.settings.workspace / path).read_bytes()).hexdigest() == sha
    assert len(provider.submissions) == 8 and provider.analysis == []
    # Concurrent retries and a new router preserve the same identity and result.
    with ThreadPoolExecutor(max_workers=2) as pool:

        def retry(_):
            try:
                return service.recover_postprocess(thread, [ids[0]])["status"]
            except portalocker.LockException:
                return "locked"

        assert set(pool.map(retry, range(2))) <= {"ok", "locked"}
    router = WorkspaceRouter(service.settings)
    run_id = router.bind(service, thread)
    fresh = WorkspaceRouter(service.settings)
    rebound, same_thread = fresh.resolve(run_id=run_id)
    assert (
        rebound.recover_postprocess(same_thread, [ids[0]])["jobs"][0]["status"]
        == "generated_preserved"
    )
    assert rebound.status(thread)["generation_complete"]
    assert service.journal.get("postprocess", operation)["compensated"]
    # Even later graph execution cannot replay recovered postprocess/review or discard verdicts.
    result = service.journal.get("job_result", f"{thread}:0")
    result["review_status"] = "accepted"
    service.journal.put("job_result", f"{thread}:0", result)
    assert (await ImageWorkflow(service.settings, service.journal, provider).execute(manifest))[
        "generation_complete"
    ]
    assert service.journal.get("job_result", f"{thread}:0") == result
    assert len(provider.submissions) == 8 and provider.analysis == []


@pytest.mark.parametrize("status", ["new", "pending", "unknown", "success", "failed"])
async def test_recovery_rejects_non_downloaded_without_reset(downloaded_run, status):
    service, manifest, _, key = downloaded_run
    receipt = service.journal.get("image", key)
    receipt["status"] = status
    service.journal.put("image", key, receipt)
    report = service.recover_postprocess(manifest["thread_id"], [manifest["jobs"][0]["image_id"]])
    assert report["status"] == "partial_or_rejected"
    assert service.journal.get("image", key) == receipt


async def test_recovery_missing_raw_changed_frozen_selection_and_lock(downloaded_run):
    service, manifest, _, key = downloaded_run
    thread, ids = manifest["thread_id"], [manifest["jobs"][0]["image_id"]]
    for selection in ([], ids * 2, ["not-an-image"]):
        with pytest.raises(ValueError):
            service.recover_postprocess(thread, selection)
    with portalocker.Lock(
        str(service.settings.workspace / ".replicator/execution.lock"), timeout=0
    ):
        with pytest.raises(portalocker.LockException):
            service.recover_postprocess(thread, ids)
    raw = service.settings.workspace / f".replicator/raw/{key}.image"
    content = raw.read_bytes()
    raw.unlink()
    assert service.recover_postprocess(thread, ids)["status"] == "partial_or_rejected"
    raw.write_bytes(content)
    from pathlib import Path

    frozen = Path(manifest["jobs"][0]["path"])
    await asyncio.to_thread(frozen.write_bytes, b"changed")
    assert service.recover_postprocess(thread, ids)["status"] == "partial_or_rejected"


async def test_large_aspect_failure_keeps_receipt_raw_and_reports_dimensions(downloaded_run):
    service, manifest, _, key = downloaded_run
    raw = service.settings.workspace / f".replicator/raw/{key}.image"
    Image.new("RGB", (1000, 400)).save(raw, format="PNG")
    before = raw.read_bytes()
    receipts = service.journal.records("image")
    results = service.journal.records("job_result")
    response = service.recover_postprocess(manifest["thread_id"], [manifest["jobs"][0]["image_id"]])
    row = response["jobs"][0]
    assert row["error_code"] == "provider_canvas_aspect_mismatch"
    assert row["actual_size"] == [1000, 400]
    assert row["requested_size"] == [1024, 1024]
    assert service.journal.records("image") == receipts
    assert service.journal.records("job_result") == results
    assert raw.read_bytes() == before


@pytest.mark.parametrize("family", ["gpt-image-2.5-flare", "gpt-image-2.5-sunburst"])
async def test_graph_automatically_compensates_base_model_output(workspace, family):
    (workspace / "prompts/images_1.json").write_text(
        canonical([{"texts": [], "scene": "fixture"}] * 3), encoding="utf-8"
    )
    service = Service(Settings(workspace, workspace, poll_seconds=0))
    provider = FakeProvider()

    async def download(item, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1536, 1536), "red").save(target, format="PNG")

    provider.download = download
    manifest = freeze(workspace, RunOptions(image_model=family))
    result = await ImageWorkflow(service.settings, service.journal, provider).execute(manifest)
    assert result["generation_complete"]
    assert len(provider.submissions) == 3
    assert all(body["model"] == family for body in provider.submissions)
    for job in service.status(manifest["thread_id"])["jobs"]:
        assert job["postprocess"]["compensated"]
        assert job["postprocess"]["final_size"] == [1024, 1024]


async def test_recovery_stdio_returns_success_and_structured_local_failure(downloaded_run):
    import sys
    from pathlib import Path

    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    service, manifest, _, _ = downloaded_run
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "image_replicator",
            "--project-root",
            str(Path(__file__).parents[1]),
            "--state-dir",
            str(service.settings.workspace),
        ],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.discover()
            imported = await client.call_tool(
                "import_run",
                {
                    "workspace": str(service.settings.workspace),
                    "thread_id": manifest["thread_id"],
                },
            )
            run_id = imported.structured_content["run_id"]
            resource = await client.read_resource("replicator://input-contract")
            assert (
                json.loads(resource.contents[0].text)["postprocess_recovery_policy"]
                == "downloaded-local-v1"
            )
            image_id = manifest["jobs"][0]["image_id"]
            response = await client.call_tool(
                "recover_postprocess",
                {
                    "run_id": run_id,
                    "image_ids": [image_id],
                },
            )
            assert not response.is_error
            assert response.structured_content["jobs"][0]["status"] == "recovered"
            assert response.structured_content["run_id"] == run_id
            # A changed successful file cannot be overwritten or silently reaccepted.
            artifact = response.structured_content["jobs"][0]["artifact"]
            target = service.settings.workspace / artifact
            target.write_bytes(b"externally-changed")
            rejected = await client.call_tool(
                "recover_postprocess",
                {
                    "run_id": run_id,
                    "image_ids": [image_id],
                },
            )
            assert rejected.is_error
            assert rejected.structured_content["jobs"][0]["error_code"] == "artifact_hash_mismatch"
            assert target.read_bytes() == b"externally-changed"
