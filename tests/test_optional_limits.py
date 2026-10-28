import argparse
from dataclasses import replace

import httpx
import pytest
from test_workflow import FakeProvider

from image_replicator.config import KEYS, Settings
from image_replicator.design import review_body
from image_replicator.inputs import freeze
from image_replicator.models import RunOptions
from image_replicator.provider import Provider, ProviderFailure, analysis_body
from image_replicator.server import Service, positive_limit
from image_replicator.storage import Journal
from image_replicator.workflow import Workflow


@pytest.mark.parametrize("field", ["max_batch_images", "max_request_bytes", "max_output_tokens"])
@pytest.mark.parametrize("value", [0, -1, True])
def test_explicit_limits_require_positive_integer(tmp_path, field, value):
    with pytest.raises(ValueError, match="positive integer"):
        replace(Settings(tmp_path, tmp_path), **{field: value})


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_cli_rejects_invalid_explicit_limit(value):
    with pytest.raises(argparse.ArgumentTypeError):
        positive_limit(value)


async def test_default_service_executes_without_limits(workspace, monkeypatch):
    fake = FakeProvider()

    async def close():
        pass

    fake.close = close
    monkeypatch.setattr("image_replicator.server.read_keys", lambda _: {})
    monkeypatch.setattr("image_replicator.server.Provider", lambda *_: fake)
    service = Service(Settings(workspace, workspace))
    manifest = freeze(workspace, RunOptions())
    service.journal.put("manifest", manifest["thread_id"], manifest)
    assert (await service.execute(manifest["thread_id"]))["status"] == "scheduled"
    await service.tasks[manifest["thread_id"]]
    result = service.status(manifest["thread_id"])
    assert result["generation_complete"]
    assert len(fake.submissions) == 3
    assert all("max_tokens" not in body for body in fake.analysis)
    job = result["jobs"][0]
    plan = service.design(manifest["thread_id"], job["image_id"])["plan"]
    args = (
        plan,
        workspace / job["source"],
        workspace / job["artifact"],
        job["artifact_sha256"],
        manifest["products"],
    )
    assert "max_tokens" not in review_body(*args, None)
    assert review_body(*args, 321)["max_tokens"] == 321
    # Changing process limits does not change frozen identity or resubmit completed images.
    service.settings = replace(service.settings, max_output_tokens=512)
    await service.execute(manifest["thread_id"])
    await service.tasks[manifest["thread_id"]]
    assert len(fake.submissions) == 3


def test_independent_batch_bytes_and_token_limits(workspace):
    jobs = [
        {"image_id": str(i), "transform": {}, "prepared_path": str(workspace / "products/p.png")}
        for i in range(3)
    ]
    # Use an existing safe image fixture rather than a fabricated provider request.
    for job in jobs:
        job["prepared_path"] = str(next((workspace / "products").iterdir()))
    base = Settings(workspace, workspace)
    journal = Journal(workspace / ".replicator/limits.sqlite")
    engine = Workflow(base, journal, FakeProvider())
    assert len(engine.batches(jobs, "text", {})) == 1
    engine.settings = replace(base, max_batch_images=1)
    assert len(engine.batches(jobs, "text", {})) == 3
    engine.settings = replace(base, max_request_bytes=1)
    with pytest.raises(ValueError, match="Single reference"):
        engine.batches(jobs, "text", {})
    assert "max_tokens" not in analysis_body("test", "text", jobs, {}, None)
    assert analysis_body("test", "text", jobs, {}, 123)["max_tokens"] == 123
    assert not base.request_exceeds_limit(10**20)
    assert not replace(base, max_request_bytes=100).request_exceeds_limit(100)
    assert replace(base, max_request_bytes=100).request_exceeds_limit(101)


async def test_image_submit_enforces_only_explicit_byte_limit(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"task_id": "fixture"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        p = Provider(Settings(tmp_path, tmp_path), dict.fromkeys(KEYS, "fixture"), client)
        assert await p.submit({"prompt": "x" * 1000}) == "fixture"
        p.settings = replace(p.settings, max_request_bytes=1)
        with pytest.raises(ProviderFailure, match="byte limit"):
            await p.submit({"prompt": "x"})
    assert len(calls) == 1
