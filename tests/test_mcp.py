import json
import shutil
import sys
from importlib.metadata import version
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PROJECT = Path(__file__).resolve().parents[1]


async def test_recovery_preflight_failure_is_structured_tool_error_without_payload(workspace):
    from image_replicator.storage import Journal

    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "image_replicator",
            "--project-root",
            str(PROJECT),
            "--workspace",
            str(workspace),
            "--state-dir",
            str(workspace),
        ],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.discover()
            prepared = (await client.call_tool("prepare_run", {})).structured_content
            thread = prepared["thread_id"]
            Journal(workspace / ".replicator/journal.sqlite").put(
                "job_result", f"{thread}:0", {"generation_status": "blocked"}
            )
            secret = "fixture-copy-payload-not-for-error"
            failed = await client.call_tool(
                "prepare_analysis_recovery",
                {
                    "thread_id": thread,
                    "request_id": "proposed-copy-conflict",
                    "updates": [
                        {
                            "image_id": prepared["jobs"][0]["image_id"],
                            "delta": {
                                "texts": [],
                                "text_replacements": [
                                    {"old": secret, "new": "brand", "source": "fixture"}
                                ],
                            },
                        }
                    ],
                },
            )
            assert failed.is_error
            assert failed.structured_content["status"] == "preflight_failed"
            assert (
                failed.structured_content["preflight"]["jobs"][0]["error_code"]
                == "copy_input_conflict"
            )
            assert secret not in json.dumps(failed.structured_content)
            assert len(Journal(workspace / ".replicator/journal.sqlite").records("manifest")) == 1


async def test_task_workspaces_stdio_restart_and_legacy_import(workspace):
    roots = [workspace / name for name in ("a", "b")]
    for root in roots:
        root.mkdir()
        for name in ("references", "products", "brief", "prompts"):
            shutil.copytree(workspace / name, root / name)
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "image_replicator",
            "--project-root",
            str(PROJECT),
            "--state-dir",
            str(workspace),
            "--allow-workspace-root",
            str(workspace),
        ],
        cwd=str(PROJECT),
    )
    runs = []
    for restart in (False, True):
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.discover()
                resource = await client.read_resource("replicator://input-contract")
                assert json.loads(resource.contents[0].text)["workspace_mode"] == "task"
                assert (await client.call_tool("prepare_run", {})).is_error
                assert (
                    await client.call_tool("inspect_inputs", {"workspace": str(PROJECT)})
                ).is_error
                if not restart:
                    for root in roots:
                        prepared = await client.call_tool("prepare_run", {"workspace": str(root)})
                        assert not prepared.is_error
                        runs.append(prepared.structured_content)
                    assert runs[0]["run_id"] != runs[1]["run_id"]
                for root, run in zip(roots, runs, strict=True):
                    result = await client.call_tool("get_run", {"run_id": run["run_id"]})
                    assert not result.is_error
                    assert result.structured_content["workspace"].lower() == str(root).lower()
                    assert (
                        await client.call_tool("get_run", {"thread_id": run["thread_id"]})
                    ).is_error
                    imported = await client.call_tool(
                        "import_run", {"workspace": str(root), "thread_id": run["thread_id"]}
                    )
                    assert not imported.is_error
                    assert imported.structured_content["run_id"] == run["run_id"]
                    assert (
                        await client.call_tool("execute_run", {"run_id": "run_missing"})
                    ).is_error
                    # Unknown binding is rejected before any supplier call.


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
            "--state-dir",
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
                "import_run",
                "prepare_run",
                "execute_run",
                "get_run",
                "reconcile_submission",
                "get_design",
                "record_review",
                "prepare_revision",
                "preflight_run",
                "prepare_analysis_recovery",
            }
            resources = await client.list_resources()
            assert len(resources.resources) == 1
            resource = await client.read_resource("replicator://input-contract")
            contract = json.loads(resource.contents[0].text)
            assert contract["alignment_policy"] == "reference-creative-v1"
            assert contract["execution_limit_policy"] == "opt-in-v1"
            assert contract["operational_limit_policy"] == "opt-in-v1"
            assert all(
                contract[k] is None
                for k in (
                    "batch_images",
                    "request_bytes",
                    "output_tokens",
                    "download_hosts",
                    "input_bytes",
                    "download_bytes",
                    "poll_timeout",
                    "http_timeout",
                    "default_concurrency",
                    "default_max_visual_revisions",
                )
            )
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
            preflight = await client.call_tool("preflight_run", {"thread_id": thread_id})
            assert not preflight.is_error
            assert preflight.structured_content["provider_requests"] == 0
            assert not preflight.structured_content["ready_for_generation"]
            assert contract["analysis_recovery_policy"] == "explicit-pre-image-child-v1"
            rejected_recovery = await client.call_tool(
                "prepare_analysis_recovery",
                {
                    "thread_id": thread_id,
                    "request_id": "unexecuted-is-not-failed",
                    "updates": [
                        {"image_id": status.structured_content["jobs"][0]["image_id"], "delta": {}}
                    ],
                },
            )
            assert rejected_recovery.is_error  # No API key or provider request is required.
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
            failure = await client.call_tool("execute_run", {"thread_id": "0" * 64})
            assert failure.is_error  # unknown task; no accidental charged call
            invalid = await client.call_tool("get_run", {"thread_id": "../escape"})
            assert invalid.is_error
            (workspace / "prompts/images_1.json").write_text(
                json.dumps([{"design": {"forbidden_elements": ["hands"]}}, {}, {}]),
                encoding="utf-8",
            )
            out_of_scope = await client.call_tool("prepare_run", {})
            assert out_of_scope.is_error
