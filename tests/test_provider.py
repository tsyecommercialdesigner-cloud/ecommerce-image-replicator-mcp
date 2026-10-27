import json

import httpx
import pytest

from image_replicator.config import KEYS, Settings
from image_replicator.models import TextBatch, VisualBatch
from image_replicator.provider import (
    LLMHTTPFailure,
    Provider,
    ProviderFailure,
    SafeToRetry,
    SubmissionUnknown,
    gemini_response_schema,
    inline_schema,
)


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


@pytest.mark.parametrize("contract", [TextBatch, VisualBatch])
def test_gemini_schema_expands_refs_without_losing_validation(contract):
    from jsonschema import Draft202012Validator

    original = contract.model_json_schema()
    before = json.dumps(original, sort_keys=True)
    expanded = inline_schema(original)
    assert "$ref" not in json.dumps(expanded) and "$defs" not in json.dumps(expanded)
    assert json.dumps(original, sort_keys=True) == before
    if contract is TextBatch:
        valid = {
            "images": [
                {
                    "image_id": "x",
                    "texts": [
                        {
                            "content": "hello",
                            "css": "color:red",
                            "box": {"x": 0, "y": 0, "width": 100, "height": 100},
                        }
                    ],
                }
            ]
        }
        invalid = {
            "images": [
                {
                    "image_id": "x",
                    "texts": [
                        {
                            "content": "hello",
                            "css": "",
                            "box": {"x": 1001, "y": 0, "width": 0, "height": 100},
                        }
                    ],
                }
            ]
        }
    else:
        valid = {"images": [{"image_id": "x", "scene": "A product"}]}
        invalid = {"images": [{"image_id": "x", "scene": "", "unknown": True}]}
    for schema in (original, expanded):
        validator = Draft202012Validator(schema)
        assert validator.is_valid(valid)
        assert not validator.is_valid(invalid)


@pytest.mark.parametrize(
    "schema",
    [
        {"$ref": "https://external.invalid/schema"},
        {"$ref": "#/$defs/missing"},
        {"$defs": {"loop": {"$ref": "#/$defs/loop"}}, "$ref": "#/$defs/loop"},
        {"$defs": {"x": {"type": "string"}}, "items": {"$ref": "#/$defs/x", "maxLength": 2}},
    ],
)
def test_schema_rejects_unresolvable_or_ambiguous_refs(schema):
    with pytest.raises(ValueError):
        inline_schema(schema)


def test_supplier_schema_subset_keeps_full_local_contract():
    from pydantic import ValidationError

    projected = gemini_response_schema(TextBatch.model_json_schema())
    encoded = json.dumps(projected)
    for unsupported in ("$defs", "$ref", "additionalProperties", "exclusiveMinimum"):
        assert unsupported not in encoded
    box = projected["properties"]["images"]["items"]["properties"]["texts"]["items"]["properties"][
        "box"
    ]
    assert box["properties"]["width"]["minimum"] == 0
    assert "strictly greater" in box["properties"]["width"]["description"]
    for invalid in (
        {"images": [], "unexpected": "must be rejected locally"},
        {
            "images": [
                {
                    "image_id": "x",
                    "texts": [
                        {
                            "content": "x",
                            "css": "",
                            "box": {"x": 0, "y": 0, "width": 0, "height": 10},
                        }
                    ],
                }
            ]
        },
    ):
        with pytest.raises(ValidationError):
            TextBatch.model_validate(invalid)


async def test_llm_http_error_is_redacted_and_not_exposed_in_exception(tmp_path):
    secret = "test-not-a-real-key"
    message = (
        f"Unknown name '$defs'; Bearer {secret}; "
        "https://example.invalid/?token=private data:image/png;base64,AAABBB"
    )

    def handler(request):
        assert request.headers["Accept"] == "application/json"
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": message,
                    "type": "invalid_request",
                    "code": 400,
                    "request": {"private": "DO_NOT_SAVE"},
                    "authorization": secret,
                }
            },
        )

    p = provider(tmp_path, handler)
    with pytest.raises(LLMHTTPFailure) as caught:
        await p.analyze({"model": "gemini-3.8-flash"})
    await p.close()
    assert caught.value.terminal
    assert "$defs" not in str(caught.value)
    path = tmp_path / f".replicator/errors/{caught.value.diagnostic_id}.json"
    raw = path.read_text()
    for forbidden in (secret, "example.invalid", "AAABBB", "DO_NOT_SAVE", "authorization"):
        assert forbidden not in raw
    saved = json.loads(raw)
    assert saved["http_status"] == 400
    assert "$defs" in saved["error"]["message"]
    assert len(saved["response_sha256"]) == 64


@pytest.mark.parametrize("mode", ["html", "oversized", "echo"])
async def test_llm_diagnostics_omit_private_and_unstructured_bodies(tmp_path, mode):
    private = "Private business brief which must never appear in error logs"

    def handler(request):
        if mode == "html":
            return httpx.Response(502, text=f"<html>{private}</html>")
        return httpx.Response(
            400, json={"error": {"message": private if mode == "echo" else private * 2000}}
        )

    p = provider(tmp_path, handler)
    with pytest.raises(LLMHTTPFailure) as caught:
        await p.analyze({"messages": [{"role": "user", "content": private}]})
    await p.close()
    raw = (tmp_path / f".replicator/errors/{caught.value.diagnostic_id}.json").read_text()
    assert private not in raw
    assert len(raw) < 4096
