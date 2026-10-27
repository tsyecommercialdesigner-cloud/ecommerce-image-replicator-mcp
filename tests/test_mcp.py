import json
import sys
from importlib.metadata import version
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PROJECT = Path(__file__).resolve().parents[1]


async def test_official_mcp_client_stdio_contracts(workspace):
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "image_replicator",
            "--project-root",
            str(PROJECT),
            "--workspace",
            str(workspace),
        ],
        cwd=str(workspace),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            discovery = await client.discover()
            assert discovery is not None
            assert client.server_info is not None
            assert client.server_info.version == version("ecommerce-image-replicator-mcp")
            listed = await client.list_tools()
            assert {tool.name for tool in listed.tools} == {
                "inspect_inputs",
                "prepare_run",
                "execute_run",
                "get_run",
                "reconcile_submission",
                "get_design",
                "record_review",
                "prepare_revision",
            }
            resources = await client.list_resources()
            assert len(resources.resources) == 1
            resource = await client.read_resource("replicator://input-contract")
            contract = json.loads(resource.contents[0].text)
            assert contract["alignment_policy"] == "reference-creative-v1"
            assert set(contract["edit_boundary"]["protected"]) == {
                "composition",
                "objects",
                "relationships",
            }
            definitions = contract["delta_item_schema"]["$defs"]
            assert "BrandStyle" in definitions and "ProductAttribute" in definitions
            assert (
                definitions["DesignOverrides"]["properties"]["objects"]["anyOf"][0]["maxItems"] == 0
            )
            prompts = await client.list_prompts()
            assert len(prompts.prompts) == 1
            result = await client.call_tool("prepare_run", {})
            assert not result.is_error
            thread_id = result.structured_content["thread_id"]
            status = await client.call_tool("get_run", {"thread_id": thread_id})
            assert not status.is_error
            assert len(status.structured_content["jobs"]) == 3
            assert status.structured_content["version"] == 2
            inspection = await client.call_tool("inspect_inputs", {})
            image_id = inspection.structured_content["images"][1]["image_id"]
            selected = await client.call_tool(
                "prepare_run", {"options": {"selected_image_ids": [image_id]}}
            )
            assert not selected.is_error
            assert [job["image_id"] for job in selected.structured_content["jobs"]] == [image_id]
            design = await client.call_tool(
                "get_design", {"thread_id": thread_id, "image_id": image_id}
            )
            assert design.structured_content["missing"] == ["texts", "scene"]
            revision = await client.call_tool(
                "prepare_revision",
                {
                    "parent_thread_id": thread_id,
                    "updates": [{"image_id": image_id, "delta": {"texts": [], "scene": "new"}}],
                },
            )
            assert revision.is_error  # no original completed image
            review = await client.call_tool(
                "record_review",
                {
                    "thread_id": thread_id,
                    "report": {
                        "image_id": image_id,
                        "artifact_sha256": "0" * 64,
                        "design_sha256": "0" * 64,
                        "reference_sha256": "0" * 64,
                        "checks": [],
                    },
                },
            )
            assert review.is_error  # no generated artifact; cannot mark prepared input accepted
            failure = await client.call_tool("execute_run", {"thread_id": thread_id})
            assert failure.is_error  # explicit missing budgets; no accidental charged call
            invalid = await client.call_tool("get_run", {"thread_id": "../escape"})
            assert invalid.is_error
            (workspace / "prompts/images_1.json").write_text(
                json.dumps([{"design": {"forbidden_elements": ["hands"]}}, {}, {}]),
                encoding="utf-8",
            )
            out_of_scope = await client.call_tool("prepare_run", {})
            assert out_of_scope.is_error
