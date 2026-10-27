import sys
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
            listed = await client.list_tools()
            assert {tool.name for tool in listed.tools} == {
                "inspect_inputs",
                "prepare_run",
                "execute_run",
                "get_run",
                "reconcile_submission",
            }
            resources = await client.list_resources()
            assert len(resources.resources) == 1
            prompts = await client.list_prompts()
            assert len(prompts.prompts) == 1
            result = await client.call_tool("prepare_run", {})
            assert not result.is_error
            thread_id = result.structured_content["thread_id"]
            status = await client.call_tool("get_run", {"thread_id": thread_id})
            assert not status.is_error
            assert len(status.structured_content["jobs"]) == 3
            failure = await client.call_tool("execute_run", {"thread_id": thread_id})
            assert failure.is_error  # explicit missing budgets; no accidental charged call
            invalid = await client.call_tool("get_run", {"thread_id": "../escape"})
            assert invalid.is_error
