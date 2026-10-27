"""Discover installed stdio capabilities without executing provider requests."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def check(project: Path, workspace: Path):
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "image_replicator",
            "--project-root",
            str(project),
            "--workspace",
            str(workspace),
        ],
        cwd=str(workspace),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.discover()
            tools = await client.list_tools()
            expected = {
                "inspect_inputs",
                "prepare_run",
                "execute_run",
                "get_run",
                "get_design",
                "record_review",
                "prepare_revision",
                "reconcile_submission",
            }
            if {item.name for item in tools.tools} != expected:
                raise RuntimeError("Installed tool contract mismatch")
            resources = await client.list_resources()
            prompts = await client.list_prompts()
            if len(resources.resources) != 1 or len(prompts.prompts) != 1:
                raise RuntimeError("Installed resource/prompt discovery mismatch")
            contract = await client.read_resource("replicator://input-contract")
            data = json.loads(contract.contents[0].text)
            if data["alignment_policy"] != "reference-creative-v1":
                raise RuntimeError("Installed reference policy mismatch")
    print(
        json.dumps(
            {"status": "passed", "tools": 8, "resources": 1, "prompts": 1, "provider_requests": 0}
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(
        asyncio.wait_for(
            check(args.project_root.resolve(strict=True), args.workspace.resolve(strict=True)),
            timeout=45,
        )
    )


if __name__ == "__main__":
    main()
