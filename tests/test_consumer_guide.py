import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_consumer_entries_link_to_complete_synchronized_guidebook():
    source = ROOT / "docs/guidebook-of-ecommerce-image-replicator-mcp.md"
    distributed = ROOT / "output-docs/docs/guidebook-of-ecommerce-image-replicator-mcp.md"
    assert source.read_bytes() == distributed.read_bytes()
    bodies = []
    for name in ("AGENTS.md", "CLAUDE.md", "CONVENTIONS.md"):
        entry = ROOT / "output-docs" / name
        text = entry.read_text(encoding="utf-8")
        assert "./docs/guidebook-of-ecommerce-image-replicator-mcp.md" in text
        for target in re.findall(r"\]\(([^)]+)\)", text):
            assert (entry.parent / target).is_file()
        bodies.append(text.split("\n", 1)[1])
    assert len(set(bodies)) == 1
    guide = source.read_text(encoding="utf-8")
    assert len(re.findall(r"^## \d+\.", guide, re.M)) == 10
    for text in re.findall(r"```json\n(.*?)\n```", guide, re.S):
        json.loads(text)
    for term in (
        "copy_preflight",
        "schema_errors",
        "replacement_rule_source",
        "prepare_analysis_recovery",
        "prepare_revision",
        "postprocess",
        "pending_text_analysis",
    ):
        assert term in guide
