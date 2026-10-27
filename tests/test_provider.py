import json

import httpx
import pytest

from image_replicator.config import KEYS, Settings
from image_replicator.provider import Provider, ProviderFailure, SafeToRetry, SubmissionUnknown


def provider(tmp_path, handler):
    return Provider(
        Settings(tmp_path, tmp_path, 2, 100_000, 1000),
        dict.fromkeys(KEYS, "test-not-a-real-key"),
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


async def test_async_submit_top_level_task_id(tmp_path):
    def handler(request):
        assert request.url.path == "/v1/images/generations"
        assert request.url.params["async"] == "true"
        assert json.loads(request.content)["model"] == "gpt-image-2.5-flare"
        return httpx.Response(200, json={"task_id": "known"})

    p = provider(tmp_path, handler)
    assert await p.submit({"model": "gpt-image-2.5-flare"}) == "known"
    await p.close()


@pytest.mark.parametrize("code,body", [(500, {}), (429, {}), (200, {}), (200, {"task_id": ""})])
async def test_ambiguous_http_outcomes_are_not_retried(tmp_path, code, body):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(code, json=body)

    p = provider(tmp_path, handler)
    with pytest.raises(SubmissionUnknown):
        await p.submit({})
    assert len(calls) == 1
    await p.close()


@pytest.mark.parametrize(
    "error,expected",
    [
        (httpx.ConnectError, SafeToRetry),
        (httpx.ReadTimeout, SubmissionUnknown),
        (httpx.WriteError, SubmissionUnknown),
    ],
)
async def test_transport_uncertainty(tmp_path, error, expected):
    def handler(request):
        raise error("test", request=request)

    p = provider(tmp_path, handler)
    with pytest.raises(expected):
        await p.submit({})
    await p.close()


@pytest.mark.parametrize(
    "url",
    [
        "http://ai.t8star.org/image",
        "https://evil.invalid/image",
        "https://user:password@ai.t8star.org/image",
    ],
)
async def test_download_rejects_unauthorized_targets(tmp_path, url):
    def handler(request):
        pytest.fail("Must reject before network access")

    p = provider(tmp_path, handler)
    with pytest.raises(ProviderFailure):
        await p.download({"url": url}, tmp_path / "image")
    await p.close()
