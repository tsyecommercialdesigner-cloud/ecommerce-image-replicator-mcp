"""Local stdio MCP entry point; paid work requires an explicit execute tool call."""

import argparse
import asyncio
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import portalocker
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .config import Settings, read_keys
from .inputs import discover, freeze, safe_path
from .models import Delta, RunOptions
from .provider import Provider, ProviderFailure, SubmissionUnknown
from .storage import Journal, canonical
from .workflow import Workflow, validate_task_id

INSTRUCTIONS = """Use input_contract and prepare_inputs before executing. Workspace is fixed by
the server operator. References are references/<group>/*.jpg or *.png; products/ contains user
product photos; brief/*.md contains product facts. Write prompts/<group>.json as a naturally
ordered array, one item per reference; {} retains the base prompt. Inspect inputs before calling
prepare_run. execute_run authorizes paid LLM and image requests for the frozen manifest, then
returns immediately; poll get_run. resume uses the same thread_id and retained provider task_ids.
Never resubmit unknown image outcomes; reconcile with a known supplier task_id first.
LLM batch limits and strict JSON compatibility are operator-configured and not yet live-verified.
"""


class Service:
    def __init__(self, settings: Settings):
        self.settings = settings
        root = settings.workspace.resolve(strict=True)
        runtime = safe_path(root, ".replicator", exists=False)
        runtime.mkdir(exist_ok=True, mode=0o700)
        self.journal = Journal(safe_path(root, ".replicator/journal.sqlite", exists=False))
        self.tasks: dict[str, asyncio.Task] = {}

    def manifest(self, thread_id: str):
        if not re.fullmatch(r"[a-f0-9]{64}", thread_id):
            raise ValueError("Invalid thread_id")
        result = self.journal.get("manifest", thread_id)
        if result is None:
            raise ValueError("Unknown thread_id")
        return result

    def status(self, thread_id: str):
        manifest = self.manifest(thread_id)
        state = self.journal.get("run", thread_id) or {"status": "prepared"}
        if state["status"] == "running" and thread_id not in self.tasks:
            state = {**state, "status": "interrupted_or_other_process"}
        jobs = []
        for index, job in enumerate(manifest["jobs"]):
            link = self.journal.get("run_job", f"{thread_id}:{index}")
            record = self.journal.get("image", link["key"]) if link else None
            jobs.append(
                {
                    "index": index,
                    "image_id": job["image_id"],
                    "status": record["status"] if record else "not_submitted",
                    "task_id": record.get("task_id") if record else None,
                    "model": record.get("model", manifest["options"]["image_model"])
                    if record and record["attempts"]
                    else None,
                }
            )
        return {"thread_id": thread_id, **state, "jobs": jobs}

    async def execute(self, thread_id: str):
        manifest = self.manifest(thread_id)
        if thread_id in self.tasks:
            return self.status(thread_id)
        self.settings.validate_execution()
        keys = read_keys(self.settings.project_root)

        async def worker():
            provider = Provider(self.settings, keys)
            try:
                self.journal.put("run", thread_id, {"status": "running"})
                result = await Workflow(self.settings, self.journal, provider).execute(manifest)
                self.journal.put(
                    "run", thread_id, {"status": "completed", "artifacts": result["artifacts"]}
                )
            except asyncio.CancelledError:
                self.journal.put("run", thread_id, {"status": "interrupted"})
                raise
            except Exception as exc:
                # Never expose validation inputs, provider payloads or credential-bearing URLs.
                detail = (
                    str(exc)
                    if isinstance(exc, (ProviderFailure, SubmissionUnknown))
                    else ("Local validation or workflow error; inspect inputs and checkpoints")
                )
                self.journal.put(
                    "run",
                    thread_id,
                    {"status": "blocked", "error": type(exc).__name__, "detail": detail},
                )
            finally:
                await provider.close()
                self.tasks.pop(thread_id, None)

        self.tasks[thread_id] = asyncio.create_task(worker())
        return {"thread_id": thread_id, "status": "scheduled"}

    async def close(self):
        running = list(self.tasks.values())
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)


def create_server(settings: Settings) -> MCPServer:
    service = Service(settings)

    @asynccontextmanager
    async def lifespan(server):
        try:
            yield service
        finally:
            await service.close()

    server = MCPServer(
        "ecommerce-image-replicator", instructions=INSTRUCTIONS, version="0.1.0", lifespan=lifespan
    )

    @server.resource("replicator://input-contract", mime_type="application/json")
    def input_contract() -> str:
        return canonical(
            {
                "instructions": INSTRUCTIONS,
                "delta_item_schema": Delta.model_json_schema(),
                "ordering": "natural filename order within each reference folder",
                "structured_output": True,
                "batch_images": settings.max_batch_images,
                "request_bytes": settings.max_request_bytes,
                "output_tokens": settings.max_output_tokens,
            }
        )

    @server.prompt()
    def prepare_inputs() -> str:
        return (
            INSTRUCTIONS + "\nUse inspect_inputs to obtain the authoritative order. "
            "Review each reference, the product photos and brief. For changed tasks supply "
            "texts (complete replacement array), scene (complete replacement string), and/or "
            "instruction (additional requirements). Copy boxes as normalized 0..1000 positions. "
            "Do not invent product specifications. Omitted fields retain their base descriptions."
        )

    @server.tool(structured_output=True)
    def inspect_inputs() -> dict[str, Any]:
        """Read reference folder/image order; no API calls or paid work."""
        try:
            return {"groups": discover(settings.workspace.resolve())}
        except Exception as exc:
            raise ToolError(f"Input inspection failed ({type(exc).__name__})") from None

    @server.tool(structured_output=True)
    def prepare_run(options: RunOptions | None = None) -> dict[str, Any]:
        """Validate and snapshot all input files; return stable thread_id without API calls."""
        try:
            manifest = freeze(settings.workspace, options or RunOptions())
            thread_id = manifest["thread_id"]
            service.journal.put("manifest", thread_id, manifest)
            return service.status(thread_id)
        except Exception as exc:
            raise ToolError(
                f"Preparation failed ({type(exc).__name__}); check input contract"
            ) from None

    @server.tool(structured_output=True)
    async def execute_run(thread_id: str) -> dict[str, Any]:
        """Start/resume the frozen run. This authorizes paid LLM and image API calls."""
        try:
            return await service.execute(thread_id)
        except ValueError as exc:
            # Configuration errors contain names only, never credential values.
            raise ToolError(str(exc)) from None

    @server.tool(structured_output=True)
    def get_run(thread_id: str) -> dict[str, Any]:
        """Read durable progress, task IDs and artifact paths; no supplier calls."""
        try:
            return service.status(thread_id)
        except ValueError as exc:
            raise ToolError(str(exc)) from None

    @server.tool(structured_output=True)
    async def reconcile_submission(thread_id: str, index: int, task_id: str) -> dict[str, Any]:
        """Bind an operator-verified supplier task_id to an unknown submission; never resubmit."""
        try:
            manifest = service.manifest(thread_id)
            if index < 0 or index >= len(manifest["jobs"]):
                raise ValueError("Invalid job index")
            validate_task_id(task_id)
            link = service.journal.get("run_job", f"{thread_id}:{index}")
            if not link:
                raise ValueError("No submission to reconcile")
            lock = portalocker.Lock(
                str(safe_path(settings.workspace, ".replicator/execution.lock", exists=False)),
                timeout=0,
            )
            with lock:
                record = service.journal.get("image", link["key"])
                if record["status"] not in {"unknown", "submitting"}:
                    raise ValueError("Only unknown submissions may be reconciled")
                provider = Provider(settings, read_keys(settings.project_root))
                try:
                    await provider.query(task_id)
                finally:
                    await provider.close()
                record.update(status="pending", task_id=task_id)
                service.journal.put("image", link["key"], record)
            return service.status(thread_id)
        except Exception as exc:
            raise ToolError(f"Reconciliation failed ({type(exc).__name__})") from None

    return server


def main():
    parser = argparse.ArgumentParser(description="Ecommerce image replicator MCP stdio server")
    parser.add_argument(
        "--project-root",
        required=True,
        type=Path,
        help="Installation root containing the private .env",
    )
    parser.add_argument(
        "--workspace", required=True, type=Path, help="Authorized Agent business workspace"
    )
    parser.add_argument("--max-batch-images", type=int, default=0)
    parser.add_argument("--max-request-bytes", type=int, default=0)
    parser.add_argument("--max-output-tokens", type=int, default=0)
    parser.add_argument(
        "--download-host", action="append", default=["ai.t8star.org", "files.closeai.fans"]
    )
    args = parser.parse_args()
    settings = Settings(
        args.project_root.resolve(strict=True),
        args.workspace.resolve(strict=True),
        args.max_batch_images,
        args.max_request_bytes,
        args.max_output_tokens,
        tuple(args.download_host),
    )
    create_server(settings).run(transport="stdio")
