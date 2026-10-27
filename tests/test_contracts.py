import json

import pytest
from PIL import Image

from image_replicator.config import KEYS, read_keys
from image_replicator.images import geometry, postprocess, preprocess, route_image_model
from image_replicator.inputs import discover, freeze, safe_path
from image_replicator.models import RunOptions, TextBatch
from image_replicator.storage import strict_json


def test_natural_order_empty_deltas_and_snapshot(workspace):
    paths = discover(workspace)["images_1"]
    assert [p.split("/")[-1] for p in paths] == ["1.png", "2.png", "10.png"]
    a = freeze(workspace, RunOptions())
    b = freeze(workspace, RunOptions())
    assert a["thread_id"] == b["thread_id"]
    assert len(a["jobs"]) == 3
    assert a["jobs"][0]["delta"]["texts"] is None
    (workspace / "prompts/images_1.json").write_text('[{}, {}, {"texts": []}]')
    c = freeze(workspace, RunOptions())
    assert c["thread_id"] != a["thread_id"]
    assert c["jobs"][2]["delta"]["texts"] == []


@pytest.mark.parametrize("raw", ["[]", "[{},{}]", '[{},{},{"unknown":1}]', "{}"])
def test_invalid_delta_alignment(workspace, raw):
    (workspace / "prompts/images_1.json").write_text(raw)
    with pytest.raises(ValueError):
        freeze(workspace, RunOptions())


def test_path_escape(workspace):
    (workspace / "references/escape").symlink_to(workspace.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        discover(workspace)
    with pytest.raises(ValueError):
        safe_path(workspace, "../outside", exists=False)


@pytest.mark.parametrize("size", [(1921, 1081), (100, 100), (5000, 100), (8000, 5000)])
def test_geometry_constraints(size):
    transform = geometry(*size)
    w, h = transform["canvas"]
    assert w % 16 == h % 16 == 0
    assert max(w, h) <= 4096
    assert max(w, h) / min(w, h) <= 3
    assert 655360 <= w * h <= 8294400
    x, y, right, bottom = transform["crop"]
    assert 0 <= x < right <= w and 0 <= y < bottom <= h


@pytest.mark.parametrize("family", ["gpt-image-2.5-flare", "gpt-image-2.5-sunburst"])
@pytest.mark.parametrize(
    "length,suffix", [(1024, ""), (1025, "-2k"), (2048, "-2k"), (2049, "-4k"), (4096, "-4k")]
)
def test_model_routing_boundaries(family, length, suffix):
    assert route_image_model(family, [length, 640]) == family + suffix
    assert route_image_model(family, [640, length]) == family + suffix


def test_preprocess_can_preserve_4096_long_edge():
    assert geometry(4096, 2016)["canvas"] == [4096, 2016]
    with pytest.raises(ValueError, match="4096"):
        route_image_model("gpt-image-2.5-flare", [4112, 1024])


def test_roundtrip_size_format_and_mismatch(tmp_path):
    source, padded = tmp_path / "source.png", tmp_path / "padded.png"
    Image.new("RGB", (1921, 1081), "blue").save(source)
    transform = preprocess(source, padded)
    output = postprocess(padded, tmp_path / "result", transform)
    with Image.open(output) as image:
        assert image.size == (1921, 1081)
        assert image.format == "PNG"
    Image.new("RGB", (50, 50)).save(padded)
    with pytest.raises(ValueError, match="canvas"):
        postprocess(padded, tmp_path / "invalid", transform)


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', '{"a": NaN}', "```json\n{}\n```"])
def test_reject_ambiguous_or_non_strict_json(raw):
    with pytest.raises(ValueError):
        strict_json(raw)


def test_text_box_bounds():
    with pytest.raises(ValueError):
        TextBatch.model_validate(
            {
                "images": [
                    {
                        "image_id": "a",
                        "texts": [
                            {
                                "content": "中文",
                                "css": "color:red",
                                "box": {"x": 999, "y": 0, "width": 20, "height": 10},
                            }
                        ],
                    }
                ]
            }
        )


def test_credentials_priority_and_strict_errors(tmp_path, monkeypatch):
    for key in KEYS:
        monkeypatch.setenv(key, "test-process-value")
    path = tmp_path / ".env"
    path.write_text(f"{KEYS[0]}=test-file-value\n")
    assert read_keys(tmp_path)[KEYS[0]] == "test-file-value"
    assert read_keys(tmp_path)[KEYS[1]] == "test-process-value"
    for content in [f"{KEYS[0]}=\n", f"{KEYS[0]}=a\n{KEYS[0]}=b\n", 'key="unterminated']:
        path.write_text(content)
        with pytest.raises(ValueError) as caught:
            read_keys(tmp_path)
        assert "test-process-value" not in str(caught.value)
    path.write_text(f"{KEYS[0]}='${{NO_EXPANSION}}'\n")
    assert read_keys(tmp_path)[KEYS[0]] == "${NO_EXPANSION}"


def test_brief_snapshot_is_stable(workspace):
    frozen = freeze(workspace, RunOptions())
    (workspace / "brief/product.md").write_text("changed")
    assert frozen["brief"] != "changed"
    assert json.dumps(frozen, ensure_ascii=False)
