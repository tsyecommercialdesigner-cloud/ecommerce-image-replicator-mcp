import base64
from dataclasses import replace

import httpx
import pytest
from test_workflow import FakeProvider

from image_replicator.config import KEYS, Settings
from image_replicator.inputs import freeze, inspect_images
from image_replicator.models import Delta, RevisionUpdate, RunOptions
from image_replicator.provider import Provider, ProviderFailure
from image_replicator.server import Service
from image_replicator.workflow_v2 import ImageWorkflow


def test_default_options_and_text_have_no_arbitrary_caps():
    assert RunOptions().concurrency is None
    assert RunOptions().max_visual_revisions is None
    assert RunOptions(concurrency=100, max_visual_revisions=100).concurrency == 100
    assert len(Delta(instruction="a" * 17000).instruction) == 17000
    with pytest.raises(ValueError):
        RunOptions(concurrency=0)


def test_input_size_is_only_enforced_when_configured(workspace):
    assert inspect_images(workspace)
    with pytest.raises(ValueError, match="byte limit"):
        inspect_images(workspace, max_input_bytes=1)
    assert freeze(workspace, RunOptions())
    with pytest.raises(ValueError, match="byte limit"):
        freeze(workspace, RunOptions(), max_input_bytes=1)
    with pytest.raises(ValueError, match="pixel limit"):
        freeze(workspace, RunOptions(), max_input_pixels=1)
    (workspace / "brief/long.md").write_text("x" * 100001, encoding="utf-8")
    assert len(freeze(workspace, RunOptions())["brief"]) > 100000


@pytest.mark.parametrize("inline", [True, False])
async def test_download_limits_are_opt_in(tmp_path, monkeypatch, inline):
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda *_: [(2, 1, 6, "", ("8.8.8.8", 443))])
    calls = []

    def handle(request):
        calls.append(request)
        assert "Authorization" not in request.headers
        return httpx.Response(200, content=b"test-data")

    item = (
        {"b64_json": base64.b64encode(b"test-data").decode()}
        if inline
        else {"url": "https://new-supplier.example/image"}
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = Provider(Settings(tmp_path, tmp_path), dict.fromkeys(KEYS, "fixture"), client)
        await provider.download(item, tmp_path / "image")
        assert (tmp_path / "image").read_bytes() == b"test-data"
        provider.settings = replace(provider.settings, max_download_bytes=2)
        with pytest.raises(ProviderFailure):
            await provider.download(item, tmp_path / "too-large")
        assert not (tmp_path / "too-large").exists()
        if not inline:
            provider.settings = replace(provider.settings, download_hosts=("allowed.example",))
            count = len(calls)
            with pytest.raises(ProviderFailure, match="not authorized"):
                await provider.download(item, tmp_path / "denied")
            assert len(calls) == count


async def test_public_network_and_https_checks_remain(tmp_path, monkeypatch):
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda *_: [(2, 1, 6, "", ("127.0.0.1", 443))])
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: pytest.fail("No request"))
    ) as client:
        provider = Provider(Settings(tmp_path, tmp_path), {}, client)
        for url in ["https://private.example/image", "http://public.example/image"]:
            with pytest.raises(ProviderFailure):
                await provider.download({"url": url}, tmp_path / "denied")


async def test_default_revision_budget_is_unlimited_but_explicit_zero_is_preserved(workspace):
    service = Service(Settings(workspace, workspace))
    engine = ImageWorkflow(service.settings, service.journal, FakeProvider())
    for explicit in [None, 0]:
        manifest = freeze(workspace, RunOptions(max_visual_revisions=explicit))
        assert (await engine.execute(manifest))["generation_complete"]
        update = RevisionUpdate(
            image_id=manifest["jobs"][0]["image_id"], delta=Delta(instruction="brand")
        )
        if explicit is None:
            result = service.revision(manifest["thread_id"], [update])
            assert result["options"]["max_visual_revisions"] is None
        else:
            with pytest.raises(ValueError, match="budget exhausted"):
                service.revision(manifest["thread_id"], [update])


async def test_http_timeout_defaults_to_disabled(tmp_path):
    provider = Provider(Settings(tmp_path, tmp_path), {})
    assert provider.client.timeout.read is None
    assert provider.client.timeout.connect is None
    limited = Provider(Settings(tmp_path, tmp_path, http_timeout=12), {})
    assert limited.client.timeout.read == 12
    await provider.close()
    await limited.close()
