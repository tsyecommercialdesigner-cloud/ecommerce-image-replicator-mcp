"""Offline probe executed by each released installation, without pytest or real keys."""

import asyncio
import base64
import io
import json
import sys
from importlib.metadata import version
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from PIL import Image

from image_replicator.config import Settings, read_keys
from image_replicator.inputs import freeze
from image_replicator.models import RunOptions
from image_replicator.server import Service
from image_replicator.storage import atomic_write
from image_replicator.workflow_v2 import ImageWorkflow

phase, installation, workspace, evidence = sys.argv[1:]
installation, workspace, evidence = map(Path, (installation, workspace, evidence))
state_file = evidence / "fixture-state.json"
state = json.loads(state_file.read_text()) if state_file.exists() else {"posts": []}


class Provider:
    async def analyze(self, body):
        raise AssertionError("Fixture supplies analysis; no LLM allowed")

    async def submit(self, body):
        assert phase == "seed", "Upgrade/recovery must not submit again"
        state["posts"].append(body["size"])
        return "fixture_" + str(len(state["posts"]))

    async def query(self, task_id):
        if phase == "seed" and task_id == "fixture_2":
            raise asyncio.CancelledError  # persist pending receipt at a real graph boundary
        size = state["posts"][int(task_id.split("_")[1]) - 1]
        stream = io.BytesIO()
        Image.new("RGB", tuple(map(int, size.split("x"))), "red").save(stream, format="PNG")
        return {
            "status": "SUCCESS",
            "task_id": task_id,
            "data": {"data": [{"b64_json": base64.b64encode(stream.getvalue()).decode()}]},
        }

    async def download(self, item, target):
        atomic_write(target, base64.b64decode(item["b64_json"]))


async def main():
    keys = read_keys(installation)
    assert set(keys.values()) == {"fixture-not-a-real-key"}
    settings = Settings(installation, workspace, 2, 10_000_000, 8000, poll_seconds=0)
    service = Service(settings)
    if phase == "seed":
        for name in ("references/group", "products", "brief", "prompts"):
            (workspace / name).mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (128, 128), "blue").save(workspace / "references/group/01.png")
        Image.new("RGB", (128, 128), "red").save(workspace / "products/product.png")
        (workspace / "brief/product.md").write_text("Offline fixture", encoding="utf-8")
        (workspace / "prompts/group.json").write_text('[{"texts":[],"scene":"fixture"}]')
        state["threads"] = []
        for concurrency in (1, 2):
            (workspace / "prompts/group.json").write_text(
                json.dumps([{"texts": [], "scene": f"fixture {concurrency}"}])
            )
            manifest = freeze(workspace, RunOptions(concurrency=concurrency))
            service.journal.put("manifest", manifest["thread_id"], manifest)
            state["threads"].append(manifest["thread_id"])
            try:
                await ImageWorkflow(settings, service.journal, Provider()).execute(manifest)
            except asyncio.CancelledError:
                assert concurrency == 2
    else:
        for thread in state["threads"]:
            result = await ImageWorkflow(settings, service.journal, Provider()).execute(
                service.manifest(thread)
            )
            assert result["generation_complete"]
    assert len(state["posts"]) == 2
    receipts = sorted(record["task_id"] for _, record in service.journal.records("image"))
    assert receipts == ["fixture_1", "fixture_2"]
    args = ["-m", "image_replicator", "--project-root", str(installation)]
    if phase != "upgrade":
        args += ["--workspace", str(workspace)]
    params = StdioServerParameters(command=sys.executable, args=args, cwd=str(evidence))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.discover()
            assert len((await client.list_tools()).tools) == (
                8 if version("ecommerce-image-replicator-mcp") == "0.1.1" else 9
            )
            for thread in state["threads"]:
                identity = {"thread_id": thread}
                if phase == "upgrade":
                    imported = await client.call_tool(
                        "import_run", {"workspace": str(workspace), "thread_id": thread}
                    )
                    assert not imported.is_error
                    identity = {"run_id": imported.structured_content["run_id"]}
                status = await client.call_tool("get_run", identity)
                assert not status.is_error
                assert status.structured_content["thread_id"] == thread
    state_file.write_text(json.dumps(state), encoding="utf-8")
    print(
        json.dumps(
            {
                "phase": phase,
                "fake_submissions_total": 2,
                "real_provider_requests": 0,
                "legacy_tasks": 2,
                "status": "passed",
            }
        )
    )


asyncio.run(main())
