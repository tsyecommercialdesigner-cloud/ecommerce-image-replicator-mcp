"""Local stdio MCP entry point; paid work requires an explicit execute tool call."""

import argparse
import asyncio
import copy
import hashlib
import logging
import re
import sys
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path
from typing import Any

import portalocker
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, TextContent

from .config import Settings, read_keys
from .design import edit_boundary, effective_delta, resolve_design, review_status
from .inputs import discover, freeze, inspect_images, safe_path
from .models import (
    REFERENCE_POLICY,
    AnalysisRecoveryUpdate,
    Delta,
    ProductContext,
    RevisionUpdate,
    RunOptions,
)
from .models import ReferenceReviewReport as ReviewReport
from .provider import Provider, ProviderFailure, SubmissionUnknown
from .recovery import RecoveryRejected, preflight, prepare_recovery
from .routing import WorkspaceRouter
from .runtime import StartupError, open_journal
from .storage import canonical, digest
from .workflow import Workflow, validate_task_id
from .workflow_v2 import ImageWorkflow, aggregate, result_key

LOGGER = logging.getLogger(__name__)

INSTRUCTIONS = """Read replicator://input-contract and prepare_inputs before executing.
In task mode pass
an absolute workspace to inspect_inputs/prepare_run. Use returned run_id for every subsequent
call; the workspace binding cannot change. In fixed mode the configured workspace is the default
and legacy thread_id remains usable. import_run binds an existing local thread without API calls.
References are references/<group>/*.jpg or *.png; products/ contains user
product photos; brief/*.md contains product facts. Write prompts/<group>.json as a naturally
ordered array, one item per reference; {} retains the base prompt. Inspect inputs before calling
prepare_run. execute_run authorizes paid LLM and image requests for the frozen manifest, then
returns immediately; poll get_run. Resume uses the same run_id (legacy fixed mode: thread_id)
and retained provider task_ids. prepare_revision uses parent_run_id in task mode.
Use preflight_run for per-image analysis/copy diagnostics without supplier calls.
prepare_analysis_recovery prepares ONLY selected blocked pre-image jobs, with corrected complete
deltas and/or explicit failed text/visual retry scopes. It returns a linked recovery run_id;
it never executes. Keep the original parent and successful artifacts. Reuse request_id for
idempotent preparation; follow recovery_run_id afterward. prepare_revision requires an artifact.
LLM analysis can be billable even when no image task was submitted. Valid cached result wins
over a historical error marker. Never inspect private Host configs or edit journal records.
Never resubmit unknown image outcomes; reconcile with a known supplier task_id first.
New runs preserve reference composition, object inventory and relationships, including props,
stains, water, hands, actions, counts and control subjects. Deltas may adapt product copy,
dimensions, material and other intrinsic properties, and overall brand palette, tone and art style.
Preserve the central message and key subjects/interactions; minor harmless creative variation,
including small decorative additions, is acceptable. Art style inherits each reference unless
the user explicitly requests another medium; a palette change alone is not an art-style request.
Use design.product_attributes (with sources) and design.brand_style for structured changes.
scene/instruction/text boxes/CSS/checks cannot override edit_boundary. Nonempty objects,
layout_regions and forbidden_elements overrides are rejected. Never discard the original image.
Review compares reference, output and product photos. Optional brief/design.json
contains facts and explicit default edits. Markdown stays frozen as provenance. get_design shows the
reference-bound contract. Historical redesign runs permit recovery only, not new image submissions.
record_review records artifact-bound checks. prepare_revision freezes selected replacements
and never submits. Revision budgets persist per image lineage.
When copy needs revision and the intended correction is missing, ask the user for it. If the
user explicitly chooses to continue without changing that copy, retain reference copy for
those unresolved fields and record that choice in the revision brief. Silence is not consent.
This fallback never removes required product identity/copy replacements or brand/text-color
adaptation. Keep evidenced edits and do not invent missing product facts. A known correction
may be applied directly; do not ask again for information already supplied. Prepare and review
the new artifact; never relabel the previous failed artifact as passing merely due to fallback.
review_mode=vision adds at most one
vision request per artifact/plan. Execution limits are opt-in: resource policy opt-in-v1
uses null for unlimited batch_images/request_bytes/output_tokens. Explicit positive startup
limits apply independently. Omitted output_tokens leaves max_tokens to the provider default.
Operational limits also default to null: input/download bytes, public HTTPS download host
allowlist, polling/HTTP deadlines, and new-run concurrency/revision caps. Explicit task options
and persisted lineage caps remain effective. HTTPS/public-address, path, image, identity and
unknown-submission checks remain mandatory. Finite automatic retries do not authorize endless POSTs.
"""


class Service:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.journal = open_journal(settings.workspace)
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
                    "source": job["source"],
                    "order": job["order"],
                    "revision": job.get("revision"),
                    "reference_sha256": job["sha256"],
                    "status": record["status"] if record else "not_submitted",
                    "task_id": record.get("task_id") if record else None,
                    "model": record.get("model", manifest["options"]["image_model"])
                    if record and record["attempts"]
                    else None,
                    **(self.journal.get("job_result", result_key(thread_id, index)) or {}),
                    **(
                        self.journal.get("analysis_recovery_link", result_key(thread_id, index))
                        or {}
                    ),
                }
            )
        if (
            manifest["version"] == 2
            and state["status"] not in {"running", "interrupted_or_other_process"}
            and all("generation_status" in job for job in jobs)
        ):
            state = {**state, **aggregate(jobs)}
        return {
            "thread_id": thread_id,
            "version": manifest["version"],
            "alignment_policy": manifest.get("alignment_policy", "historical"),
            "reference_alignment_verified": (
                manifest.get("alignment_policy") == REFERENCE_POLICY
                and state["status"] == "accepted"
            ),
            "parent_thread_id": manifest.get("parent_thread_id"),
            "analysis_recovery": manifest.get("analysis_recovery"),
            "options": manifest["options"],
            **state,
            "jobs": jobs,
        }

    def image_index(self, manifest: dict, image_id: str) -> int:
        for index, job in enumerate(manifest["jobs"]):
            if job["image_id"] == image_id:
                return index
        raise ValueError("Image ID is not in the frozen run")

    def preflight(self, thread_id: str, image_ids: list[str] | None = None):
        if any(not task.done() for task in self.tasks.values()):
            raise RecoveryRejected("Execution is active; wait before local preflight or recovery")
        with portalocker.Lock(
            str(safe_path(self.settings.workspace, ".replicator/execution.lock", exists=False)),
            timeout=0,
        ):
            return preflight(self.settings, self.journal, self.manifest(thread_id), image_ids)

    def recover_analysis(
        self, thread_id: str, updates: list[AnalysisRecoveryUpdate], request_id: str
    ):
        if any(not task.done() for task in self.tasks.values()):
            raise RecoveryRejected("Execution is active; wait before local preflight or recovery")
        with portalocker.Lock(
            str(safe_path(self.settings.workspace, ".replicator/execution.lock", exists=False)),
            timeout=0,
        ):
            return prepare_recovery(self, self.manifest(thread_id), updates, request_id)

    def design(self, thread_id: str, image_id: str):
        manifest = self.manifest(thread_id)
        index = self.image_index(manifest, image_id)
        stored = self.journal.get("design", result_key(thread_id, index))
        if stored:
            return {**stored, "design_sha256": digest(stored["plan"])}
        if manifest.get("alignment_policy") != REFERENCE_POLICY:
            raise ValueError("Historical run has no reference-first contract; prepare a new run")
        job = manifest["jobs"][index]
        context = manifest["product_context"]
        delta = effective_delta(context, job["delta"])
        missing = [field for field in ("texts", "scene") if delta[field] is None]
        if missing:
            return {"status": "analysis_required", "missing": missing}
        plan = resolve_design(job, context, {"texts": delta["texts"]}, {"scene": delta["scene"]})
        return {"plan": plan, "design_sha256": digest(plan)}

    def record_review(self, thread_id: str, report: ReviewReport):
        manifest = self.manifest(thread_id)
        if manifest.get("alignment_policy") != REFERENCE_POLICY:
            raise ValueError(
                "Historical redesign verdicts cannot be recorded as replication acceptance"
            )
        index = self.image_index(manifest, report.image_id)
        with portalocker.Lock(
            str(safe_path(self.settings.workspace, ".replicator/execution.lock", exists=False)),
            timeout=0,
        ):
            key = result_key(thread_id, index)
            result = self.journal.get("job_result", key)
            if not result or result["generation_status"] != "generated":
                raise ValueError("Review requires a generated v2 artifact")
            actual = hashlib.sha256(
                safe_path(self.settings.workspace, result["artifact"]).read_bytes()
            ).hexdigest()
            if actual != result["artifact_sha256"]:
                raise ValueError("Artifact changed; review rejected")
            reference = manifest["jobs"][index]
            if (
                hashlib.sha256(Path(reference["path"]).read_bytes()).hexdigest()
                != reference["sha256"]
            ):
                raise ValueError("Frozen reference changed; review rejected")
            status = review_status(report, self.design(thread_id, report.image_id)["plan"], actual)
            # Keep immutable evidence and project the latest explicit verdict.
            self.journal.put(
                "explicit_review",
                digest({"run": thread_id, "report": report.model_dump()}),
                report.model_dump(),
            )
            result.update(
                review_status=status, review=report.model_dump(), reviewer="agent_or_operator"
            )
            result.pop("review_error", None)
            self.journal.put("job_result", key, result)
        return self.status(thread_id)

    def revision(
        self,
        parent_thread_id: str,
        updates: list[RevisionUpdate],
        legacy_revision_budget: int | None = None,
        product_context: ProductContext | None = None,
    ):
        parent = self.manifest(parent_thread_id)
        if (
            parent["version"] == 2
            and parent.get("alignment_policy") != REFERENCE_POLICY
            and product_context is None
        ):
            raise ValueError(
                "Historical redesign revision requires an explicit corrected product_context"
            )
        if not updates or len({u.image_id for u in updates}) != len(updates):
            raise ValueError("Supply unique image IDs and complete replacement deltas")
        if legacy_revision_budget is not None and legacy_revision_budget < 0:
            raise ValueError("Legacy revision budget must be nonnegative if set")
        by_id = {update.image_id: update for update in updates}
        for image_id in by_id:
            self.image_index(parent, image_id)
        with portalocker.Lock(
            str(safe_path(self.settings.workspace, ".replicator/execution.lock", exists=False)),
            timeout=0,
        ):
            child = copy.deepcopy(parent)
            child.pop("thread_id")
            child.update(
                version=2,
                alignment_policy=REFERENCE_POLICY,
                parent_thread_id=parent_thread_id,
                product_context=(
                    product_context.model_dump()
                    if product_context is not None
                    else parent.get("product_context", ProductContext().model_dump())
                ),
            )
            child["options"] = RunOptions.model_validate(parent["options"]).model_dump()
            if parent["version"] == 1:
                child["options"]["max_visual_revisions"] = legacy_revision_budget
            jobs, reservations = [], []
            for index, job in enumerate(parent["jobs"]):
                if job["image_id"] not in by_id:
                    continue
                link = self.journal.get("run_job", result_key(parent_thread_id, index))
                record = self.journal.get("image", link["key"]) if link else None
                if not record or record["status"] != "downloaded":
                    raise ValueError(
                        "Revision requires a completed original image; "
                        "recover unresolved submissions first"
                    )
                if parent["version"] == 2:
                    result = self.journal.get("job_result", result_key(parent_thread_id, index))
                    if not result or result["generation_status"] != "generated":
                        raise ValueError("Revision requires a postprocessed artifact")
                    parent_artifact = result["artifact"]
                else:
                    result = self.journal.get("run", parent_thread_id) or {}
                    if result.get("status") != "completed":
                        raise ValueError("Legacy revision requires a completed run")
                    parent_artifact = result["artifacts"][index]
                parent_sha = hashlib.sha256(
                    safe_path(self.settings.workspace, parent_artifact).read_bytes()
                ).hexdigest()
                if parent["version"] == 2 and parent_sha != result["artifact_sha256"]:
                    raise ValueError("Parent artifact changed; revision rejected")
                previous = job.get("revision") or {}
                root = previous.get("root_thread_id", parent_thread_id)
                budget_key = digest({"root": root, "image": job["image_id"]})
                limit = previous.get(
                    "limit", parent["options"].get("max_visual_revisions", legacy_revision_budget)
                )
                budget = self.journal.get("revision_budget", budget_key) or {
                    "limit": limit,
                    "children": [],
                }
                if budget["limit"] != limit:
                    raise ValueError(
                        "An existing lineage budget cannot be changed by preparing again"
                    )
                jobs.append(
                    {
                        **job,
                        "delta": by_id[job["image_id"]].delta.model_dump(),
                        "revision": {
                            "root_thread_id": root,
                            "parent_thread_id": parent_thread_id,
                            "parent_operation": link["key"],
                            "parent_artifact": parent_artifact,
                            "parent_artifact_sha256": parent_sha,
                            "limit": limit,
                            "depth": previous.get("depth", 0) + 1,
                        },
                    }
                )
                reservations.append((budget_key, budget))
            child["jobs"] = jobs
            child["options"]["selected_image_ids"] = [job["image_id"] for job in jobs]
            child["thread_id"] = digest(child)
            for _, budget in reservations:
                if (
                    child["thread_id"] not in budget["children"]
                    and budget["limit"] is not None
                    and len(budget["children"]) >= budget["limit"]
                ):
                    raise ValueError("Visual revision budget exhausted; original results retained")
            # Reserve all lineages and the manifest atomically, including concurrent retries.
            with self.journal.connect() as conn:
                for key, budget in reservations:
                    if child["thread_id"] not in budget["children"]:
                        budget["children"].append(child["thread_id"])
                    conn.execute(
                        "INSERT OR REPLACE INTO records VALUES(?,?,?)",
                        ("revision_budget", key, canonical(budget)),
                    )
                conn.execute(
                    "INSERT OR REPLACE INTO records VALUES(?,?,?)",
                    ("manifest", child["thread_id"], canonical(child)),
                )
        return self.status(child["thread_id"])

    async def execute(self, thread_id: str):
        manifest = self.manifest(thread_id)
        if thread_id in self.tasks:
            return self.status(thread_id)
        if manifest["version"] == 2 and manifest.get("alignment_policy") != REFERENCE_POLICY:
            receipts = [
                self.journal.get("run_job", result_key(thread_id, i))
                for i in range(len(manifest["jobs"]))
            ]
            if not any(link and self.journal.get("image", link["key"]) for link in receipts):
                raise ValueError(
                    "Obsolete redesign run has no submitted tasks; prepare a reference-first run"
                )
        self.settings.validate_execution()
        keys = read_keys(self.settings.project_root)

        async def worker():
            provider = None
            phase = "provider_initialization"
            try:
                self.journal.put("run", thread_id, {"status": "running", "phase": phase})
                provider = Provider(self.settings, keys)
                phase = "execution"
                self.journal.put("run", thread_id, {"status": "running", "phase": phase})
                engine = ImageWorkflow if manifest["version"] == 2 else Workflow
                result = await engine(self.settings, self.journal, provider).execute(manifest)
                self.journal.put(
                    "run",
                    thread_id,
                    (
                        result
                        if manifest["version"] == 2
                        else {"status": "completed", "artifacts": result["artifacts"]}
                    ),
                )
            except asyncio.CancelledError:
                self.journal.put("run", thread_id, {"status": "interrupted"})
                raise
            except Exception as exc:
                # Never expose validation inputs, provider payloads or credential-bearing URLs.
                detail = (
                    str(exc)
                    if phase == "execution"
                    and isinstance(exc, (ProviderFailure, SubmissionUnknown))
                    else ("Local validation or workflow error; inspect inputs and checkpoints")
                )
                LOGGER.error(
                    "Background run %s failed in %s (%s)", thread_id, phase, type(exc).__name__
                )
                self.journal.put(
                    "run",
                    thread_id,
                    {
                        "status": "blocked",
                        "phase": phase,
                        "error": type(exc).__name__,
                        "detail": detail,
                    },
                )
            finally:
                try:
                    if provider is not None:
                        await provider.close()
                except Exception as exc:
                    # Cleanup must not mask a saved result or strand the task registry.
                    LOGGER.error(
                        "Background run %s failed in provider_cleanup (%s)",
                        thread_id,
                        type(exc).__name__,
                    )
                finally:
                    self.tasks.pop(thread_id, None)

        def finished(task):
            if task.cancelled():
                # Cancellation before the coroutine's first step skips its finally block.
                if self.tasks.get(thread_id) is task:
                    self.tasks.pop(thread_id, None)
                    try:
                        self.journal.put("run", thread_id, {"status": "interrupted"})
                    except Exception as exc:
                        LOGGER.error("Run cancellation journal failed (%s)", type(exc).__name__)
            elif (error := task.exception()) is not None:
                # Observe failures even when the journal itself cannot be written.
                LOGGER.error(
                    "Background run %s worker failed (%s)", thread_id, type(error).__name__
                )

        self.tasks[thread_id] = asyncio.create_task(worker())
        self.tasks[thread_id].add_done_callback(finished)
        return {"thread_id": thread_id, "status": "scheduled"}

    async def close(self):
        running = list(self.tasks.values())
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)


def create_server(
    settings: Settings,
    *,
    task_workspaces: bool = False,
    allowed_roots: tuple[Path, ...] = (),
    state_dir: Path | None = None,
) -> MCPServer:
    router = WorkspaceRouter(
        settings, task_workspaces=task_workspaces, allowed_roots=allowed_roots, state_dir=state_dir
    )

    @asynccontextmanager
    async def lifespan(server):
        try:
            yield router
        finally:
            await router.close()

    server = MCPServer(
        "ecommerce-image-replicator",
        instructions=INSTRUCTIONS,
        version=version("ecommerce-image-replicator-mcp"),
        lifespan=lifespan,
    )

    @server.resource("replicator://input-contract", mime_type="application/json")
    def input_contract() -> str:
        return canonical(
            {
                "instructions": INSTRUCTIONS,
                "workspace_mode": "task" if task_workspaces else "fixed",
                "default_workspace": None if task_workspaces else str(settings.workspace),
                "allowed_roots": [str(p) for p in router.allowed],
                "state_directory": str(router.state_dir),
                "task_identity": "run_id routes to immutable workspace/thread_id binding",
                "delta_item_schema": Delta.model_json_schema(),
                "product_context_schema": ProductContext.model_json_schema(),
                "review_schema": ReviewReport.model_json_schema(),
                "analysis_recovery_update_schema": AnalysisRecoveryUpdate.model_json_schema(),
                "analysis_recovery_policy": "explicit-pre-image-child-v1",
                "alignment_policy": REFERENCE_POLICY,
                "edit_boundary": edit_boundary(),
                "generation_image_roles": ["original_reference", "user_product_photos"],
                "review_image_roles": [
                    "original_reference",
                    "generated_output",
                    "user_product_photos",
                ],
                "ordering": "natural filename order within each reference folder",
                "structured_output": True,
                "execution_limit_policy": "opt-in-v1",
                "operational_limit_policy": "opt-in-v1",
                "download_hosts": settings.download_hosts,
                "input_bytes": settings.max_input_bytes,
                "input_pixels": settings.max_input_pixels,
                "download_bytes": settings.max_download_bytes,
                "poll_timeout": settings.poll_timeout,
                "http_timeout": settings.http_timeout,
                "default_concurrency": None,
                "default_max_visual_revisions": None,
                "unlimited_value": None,
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
            "texts (product/brand copy in original regions), design.product_attributes and/or "
            "design.brand_style. scene/instruction may only add product/brand notes. Normalized "
            "0..1000 text boxes identify original regions; they cannot authorize a new layout. "
            "Preserve composition, objects and interactions, including stains, hands and actions, "
            "while applying requested product attributes and global brand color/art style."
        )

    @server.tool(structured_output=True)
    def inspect_inputs(workspace: str | None = None) -> dict[str, Any]:
        """Read input order in an explicit workspace (or fixed default); no API calls."""
        try:
            service = router.for_workspace(workspace)
            root = service.settings.workspace
            return {
                "workspace": str(root),
                "groups": discover(root),
                "images": inspect_images(root, service.settings.max_input_bytes),
            }
        except Exception as exc:
            raise ToolError(
                f"Input inspection failed ({type(exc).__name__}); check workspace"
            ) from None

    @server.tool(structured_output=True)
    def prepare_run(
        options: RunOptions | None = None, workspace: str | None = None
    ) -> dict[str, Any]:
        """Freeze inputs and return a workspace-bound run_id; no API calls."""
        try:
            service = router.for_workspace(workspace)
            manifest = freeze(
                service.settings.workspace,
                options or RunOptions(),
                max_input_bytes=service.settings.max_input_bytes,
                max_input_pixels=service.settings.max_input_pixels,
            )
            thread_id = manifest["thread_id"]
            service.journal.put("manifest", thread_id, manifest)
            return router.expose(service, service.status(thread_id))
        except Exception as exc:
            raise ToolError(
                f"Preparation failed ({type(exc).__name__}); check workspace and input contract"
            ) from None

    @server.tool(structured_output=True)
    def import_run(workspace: str, thread_id: str) -> dict[str, Any]:
        """Bind an existing task without generating; use when resuming legacy tasks in task mode."""
        try:
            root = router.checked_root(Path(workspace))
            safe_path(root, ".replicator/journal.sqlite")
            service = router.for_workspace(str(root))
            return router.expose(service, service.status(thread_id))
        except Exception as exc:
            raise ToolError(
                f"Task import failed ({type(exc).__name__}); preserve original workspace"
            ) from None

    @server.tool(structured_output=True)
    def preflight_run(
        image_ids: list[str] | None = None, thread_id: str | None = None, run_id: str | None = None
    ) -> dict[str, Any]:
        """Inspect per-image cached analysis/copy; local preparation only, no provider calls."""
        try:
            service, local_id = router.resolve(run_id=run_id, thread_id=thread_id)
            return router.expose(service, service.preflight(local_id, image_ids))
        except RecoveryRejected as exc:
            raise ToolError(str(exc)) from None
        except Exception as exc:
            raise ToolError(
                f"Preflight rejected ({type(exc).__name__}); "
                "check binding or wait for active execution"
            ) from None

    @server.tool(structured_output=True)
    def prepare_analysis_recovery(
        updates: list[AnalysisRecoveryUpdate],
        request_id: str,
        thread_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Prepare linked recovery for selected blocked jobs with no image receipt; never executes.

        delta is a complete per-image replacement. retry_kinds opens a fresh finite analysis
        budget only for the selected failed kinds. Use stable request_id on retries.
        """
        try:
            service, local_id = router.resolve(run_id=run_id, thread_id=thread_id)
            report = router.expose(service, service.recover_analysis(local_id, updates, request_id))
            if report["status"] == "preflight_failed":
                safe = {key: value for key, value in report.items() if key != "preflight"}
                allowed = {
                    "image_id",
                    "index",
                    "status",
                    "phase",
                    "error_code",
                    "copy_status",
                    "replacement_indexes",
                    "analysis",
                    "recovery_action",
                }
                safe["preflight"] = {
                    "jobs": [
                        {key: value for key, value in row.items() if key in allowed}
                        for row in report["preflight"]["jobs"]
                    ]
                }
                error_result: Any = CallToolResult(
                    content=[TextContent(type="text", text=canonical(safe))],
                    structured_content=safe,
                    is_error=True,
                )
                return error_result
            return report
        except RecoveryRejected as exc:
            raise ToolError(str(exc)) from None
        except Exception as exc:
            raise ToolError(
                f"Recovery preparation rejected ({type(exc).__name__}); "
                "preserve original run and inspect preflight"
            ) from None

    @server.tool(structured_output=True)
    async def execute_run(
        thread_id: str | None = None, run_id: str | None = None
    ) -> dict[str, Any]:
        """Start/resume the bound run. This authorizes paid LLM and image API calls."""
        try:
            service, local_id = router.resolve(run_id=run_id, thread_id=thread_id)
            # Persist identity before crossing the paid boundary, even for legacy callers.
            router.bind(service, local_id)
            return router.expose(service, await service.execute(local_id))
        except Exception as exc:
            raise ToolError(
                f"Execution rejected ({type(exc).__name__}); check task binding and budgets"
            ) from None

    @server.tool(structured_output=True)
    def get_run(thread_id: str | None = None, run_id: str | None = None) -> dict[str, Any]:
        """Read bound task progress and workspace-relative artifacts; no supplier calls."""
        try:
            service, local_id = router.resolve(run_id=run_id, thread_id=thread_id)
            return router.expose(service, service.status(local_id))
        except Exception as exc:
            raise ToolError(
                f"Task lookup failed ({type(exc).__name__}); check task binding"
            ) from None

    @server.tool(structured_output=True)
    def get_design(
        image_id: str, thread_id: str | None = None, run_id: str | None = None
    ) -> dict[str, Any]:
        """Read design inside the bound task; no API calls."""
        try:
            service, local_id = router.resolve(run_id=run_id, thread_id=thread_id)
            return service.design(local_id, image_id)
        except Exception as exc:
            raise ToolError(f"Design inspection failed ({type(exc).__name__})") from None

    @server.tool(structured_output=True)
    def record_review(
        report: ReviewReport, thread_id: str | None = None, run_id: str | None = None
    ) -> dict[str, Any]:
        """Record artifact-bound checks in the task's original workspace; no API calls."""
        try:
            service, local_id = router.resolve(run_id=run_id, thread_id=thread_id)
            return router.expose(service, service.record_review(local_id, report))
        except Exception as exc:
            raise ToolError(f"Review rejected ({type(exc).__name__})") from None

    @server.tool(structured_output=True)
    def prepare_revision(
        updates: list[RevisionUpdate],
        parent_thread_id: str | None = None,
        legacy_revision_budget: int | None = None,
        product_context: ProductContext | None = None,
        parent_run_id: str | None = None,
    ) -> dict[str, Any]:
        """Freeze a revision in the parent's workspace; return a new run_id, no API calls.

        Deltas replace the parent's delta completely. v2 keeps its original revision budget.
        """
        try:
            service, local_id = router.resolve(run_id=parent_run_id, thread_id=parent_thread_id)
            result = service.revision(local_id, updates, legacy_revision_budget, product_context)
            return {
                **router.expose(service, result),
                "parent_run_id": router.bind(service, local_id),
            }
        except Exception as exc:
            raise ToolError(
                f"Revision preparation failed ({type(exc).__name__}); check parent, IDs and budget"
            ) from None

    @server.tool(structured_output=True)
    async def reconcile_submission(
        index: int,
        task_id: str,
        thread_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Bind a verified supplier task_id to the bound unknown submission; never resubmit."""
        try:
            service, local_id = router.resolve(run_id=run_id, thread_id=thread_id)
            manifest = service.manifest(local_id)
            if index < 0 or index >= len(manifest["jobs"]):
                raise ValueError("Invalid job index")
            validate_task_id(task_id)
            link = service.journal.get("run_job", f"{local_id}:{index}")
            if not link:
                raise ValueError("No submission to reconcile")
            lock = portalocker.Lock(
                str(
                    safe_path(
                        service.settings.workspace, ".replicator/execution.lock", exists=False
                    )
                ),
                timeout=0,
            )
            with lock:
                record = service.journal.get("image", link["key"])
                if record["status"] not in {"unknown", "submitting"}:
                    raise ValueError("Only unknown submissions may be reconciled")
                provider = Provider(service.settings, read_keys(settings.project_root))
                try:
                    await provider.query(task_id)
                finally:
                    await provider.close()
                record.update(status="pending", task_id=task_id)
                service.journal.put("image", link["key"], record)
            return router.expose(service, service.status(local_id))
        except Exception as exc:
            raise ToolError(f"Reconciliation failed ({type(exc).__name__})") from None

    return server


def positive_limit(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Limit must be a positive integer") from None
    if number <= 0:
        raise argparse.ArgumentTypeError("Limit must be a positive integer")
    return number


def main():
    parser = argparse.ArgumentParser(description="Ecommerce image replicator MCP stdio server")
    parser.add_argument(
        "--project-root",
        required=True,
        type=Path,
        help="Installation root containing the private .env",
    )
    parser.add_argument(
        "--workspace", type=Path, help="Optional fixed business workspace (legacy mode)"
    )
    parser.add_argument("--allow-workspace-root", type=Path, action="append", default=[])
    parser.add_argument(
        "--state-dir", type=Path, help="Persistent task index directory; defaults to project root"
    )
    parser.add_argument(
        "--max-batch-images",
        type=positive_limit,
        default=None,
        help="Optional positive limit; omitted means unlimited",
    )
    parser.add_argument(
        "--max-request-bytes",
        type=positive_limit,
        default=None,
        help="Optional positive limit; omitted means unlimited",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=positive_limit,
        default=None,
        help="Optional positive limit; omitted means unlimited",
    )
    parser.add_argument("--download-host", action="append", default=None)
    for flag in (
        "max-input-bytes",
        "max-input-pixels",
        "max-download-bytes",
        "poll-timeout",
        "http-timeout",
    ):
        parser.add_argument(
            "--" + flag,
            type=positive_limit,
            default=None,
            help="Optional positive limit; omitted means unlimited",
        )
    args = parser.parse_args()
    settings = Settings(
        args.project_root.resolve(strict=True),
        args.workspace.absolute() if args.workspace else args.project_root.resolve(strict=True),
        args.max_batch_images,
        args.max_request_bytes,
        args.max_output_tokens,
        tuple(args.download_host) if args.download_host is not None else None,
        max_input_bytes=args.max_input_bytes,
        max_input_pixels=args.max_input_pixels,
        max_download_bytes=args.max_download_bytes,
        poll_timeout=args.poll_timeout,
        http_timeout=args.http_timeout,
    )
    try:
        server = create_server(
            settings,
            task_workspaces=args.workspace is None,
            allowed_roots=tuple(args.allow_workspace_root),
            state_dir=args.state_dir,
        )
    except StartupError as exc:
        print(f"Startup error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    server.run(transport="stdio")
