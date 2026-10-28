"""Discover installed stdio capabilities without executing provider requests."""

import argparse
import asyncio
import json
import sys
from importlib.metadata import version
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def check(project: Path, workspace: Path | None):
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "image_replicator",
            "--project-root",
            str(project),
        ]
        + (["--workspace", str(workspace)] if workspace else []),
        cwd=str(project),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.discover()
            if client.server_info is None or client.server_info.version != version(
                "ecommerce-image-replicator-mcp"
            ):
                raise RuntimeError("MCP server version differs from installed distribution")
            tools = await client.list_tools()
            expected = {
                "inspect_inputs",
                "import_run",
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
            if version("ecommerce-image-replicator-mcp") in {"0.1.3", "0.1.4", "0.1.5"}:
                if data.get("operational_limit_policy") != "opt-in-v1":
                    raise RuntimeError("Installed operational limit policy mismatch")
                for key in (
                    "batch_images",
                    "request_bytes",
                    "output_tokens",
                    "input_bytes",
                    "input_pixels",
                    "download_bytes",
                    "download_hosts",
                    "poll_timeout",
                    "http_timeout",
                    "default_concurrency",
                    "default_max_visual_revisions",
                ):
                    if data.get(key, "missing") is not None:
                        raise RuntimeError(f"Default limit is not disabled: {key}")
            if data["alignment_policy"] != "reference-creative-v1":
                raise RuntimeError("Installed reference policy mismatch")
            if data["workspace_mode"] != ("fixed" if workspace else "task"):
                raise RuntimeError("Installed workspace mode mismatch")
    print(
        json.dumps(
            {"status": "passed", "tools": 9, "resources": 1, "prompts": 1, "provider_requests": 0}
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()
    asyncio.run(
        asyncio.wait_for(
            check(
                args.project_root.resolve(strict=True),
                args.workspace.resolve(strict=True) if args.workspace else None,
            ),
            timeout=45,
        )
    )


if __name__ == "__main__":
    main()
