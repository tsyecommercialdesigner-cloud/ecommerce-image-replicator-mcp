"""Independent image graphs with explicit visual acceptance and legacy-safe receipts."""

import asyncio
import hashlib
import logging
import traceback
from pathlib import Path

import portalocker
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from .analysis import prepare_reference
from .design import (
    effective_delta,
    generation_inputs,
    generation_prompt,
    resolve_copy,
    resolve_design,
    review_body,
    review_status,
)
from .inputs import safe_path
from .models import REFERENCE_POLICY, GraphState
from .models import ReferenceReviewReport as ReviewReport
from .provider import ProviderFailure, SubmissionUnknown
from .storage import atomic_write, canonical, digest, strict_json
from .workflow import Workflow


def result_key(thread_id: str, index: int) -> str:
    return f"{thread_id}:{index}"


def aggregate(jobs: list[dict]) -> dict:
    generated = [job for job in jobs if job.get("generation_status") == "generated"]
    if len(generated) != len(jobs):
        status = "partial" if generated else "blocked"
    elif any(job["review_status"] == "needs_revision" for job in jobs):
        status = "needs_revision"
    elif all(job["review_status"] == "accepted" for job in jobs):
        status = "accepted"
    else:
        status = "review_required"
    return {
        "status": status,
        "generation_complete": len(generated) == len(jobs),
        "artifacts": [job["artifact"] for job in generated],
    }


def diagnosed_stage(handler, name: str):
    async def run(state):
        try:
            return await handler(state)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if not hasattr(exc, "diagnostic"):
                exc.__dict__["diagnostic"] = {
                    "phase": name,
                    "error_code": f"{name}_failed",
                    "recovery_action": (
                        "preflight_run_then_prepare_analysis_recovery"
                        if name in {"analyze_missing", "resolve_design"}
                        else "inspect_original_operation_before_retry"
                    ),
                }
            raise

    return run


class ImageWorkflow(Workflow):
    async def prepare_images(self, state: GraphState):
        job = state.manifest["jobs"][0]
        # Distinct identities may contain identical bytes. Avoid replacing a file
        # another image pipeline is reading (not permitted by Windows sharing modes).
        return {"prepared": [await asyncio.to_thread(prepare_reference, self.root, job)]}

    async def describe(self, state: GraphState, kind: str):
        job = state.prepared[0]
        delta = effective_delta(state.manifest["product_context"], job["delta"])
        field = "texts" if kind == "text" else "scene"
        output = "text_descriptions" if kind == "text" else "visual_descriptions"
        if delta[field] is not None:
            return {output: [{"image_id": job["image_id"], field: delta[field]}]}
        return await super().describe(state, kind)

    async def analyze_missing(self, state: GraphState):
        # Reject bad per-image copy before spending on scene analysis or drawing.
        text = await self.describe_text(state)
        delta = effective_delta(state.manifest["product_context"], state.prepared[0]["delta"])
        resolve_copy(text["text_descriptions"][0]["texts"], delta["text_replacements"] or [])
        visual = await self.describe_visual(state)
        return {**text, **visual}

    async def compose(self, state: GraphState):
        job = state.prepared[0]
        plan = resolve_design(
            job,
            state.manifest["product_context"],
            state.text_descriptions[0],
            state.visual_descriptions[0],
        )
        job = {
            **job,
            "generation_paths": generation_inputs(self.root, job, plan, state.manifest["products"]),
        }
        prompt = generation_prompt(plan, job["transform"])
        # Persist an inspectable contract before the paid image boundary.
        path = self.local(f".replicator/designs/{digest(plan)}.json")
        atomic_write(path, canonical(plan).encode())
        self.journal.put(
            "design",
            result_key(state.thread_id, job["run_index"]),
            {"plan": plan, "path": str(path.relative_to(self.root))},
        )
        return {"designs": [plan], "prompts": [prompt], "prepared": [job]}

    def operation_key(self, state: GraphState, index: int):
        job = state.prepared[index]
        return digest(
            {
                "version": 2,
                "image_id": job["image_id"],
                "sha256": job["sha256"],
                "prompt": state.prompts[index],
                "products": [p["sha256"] for p in state.manifest["products"]],
                "model": state.manifest["options"]["image_model"],
                "revision": job.get("revision"),
            }
        )

    def guard_unresolved(self, state: GraphState):
        job = state.prepared[0]
        operation = self.operation_key(state, 0)
        for thread_id, manifest in self.journal.records("manifest"):
            for index, previous in enumerate(manifest["jobs"]):
                if Path(previous["source"]).as_posix() != Path(job["source"]).as_posix():
                    continue
                link = self.journal.get("run_job", result_key(thread_id, index))
                if not link or link["key"] == operation:
                    continue
                receipt = self.journal.get("image", link["key"])
                if receipt and receipt["status"] in {"unknown", "submitting", "pending", "success"}:
                    raise SubmissionUnknown(
                        "An earlier image operation is unresolved; "
                        "resume/reconcile its original thread before creating another"
                    )

    async def generate_image(self, state: GraphState):
        self.guard_unresolved(state)
        return {"generated": [await self.generate_one(state, 0)]}

    async def finish(self, state: GraphState):
        result = await super().finish(state)
        artifact = safe_path(self.root, result["artifacts"][0])
        key = result_key(state.thread_id, state.prepared[0]["run_index"])
        self.journal.put(
            "job_result",
            key,
            {
                "generation_status": "generated",
                "review_status": "review_required",
                "artifact": result["artifacts"][0],
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "reference_sha256": state.prepared[0]["sha256"],
                "postprocess": self.journal.get("postprocess", state.generated[0]["key"]),
            },
        )
        return result

    async def review(self, state: GraphState):
        key = result_key(state.thread_id, state.prepared[0]["run_index"])
        result = self.journal.get("job_result", key)
        plan = state.designs[0]
        if state.manifest.get("alignment_policy") != REFERENCE_POLICY:
            result.update(
                review_status="review_required",
                review_error="Historical redesign review is not replication acceptance",
            )
            self.journal.put("job_result", key, result)
            return {}
        if state.manifest["options"]["review_mode"] == "manual":
            return {}
        body = review_body(
            plan,
            Path(state.prepared[0]["path"]),
            safe_path(self.root, result["artifact"]),
            result["artifact_sha256"],
            state.manifest["products"],
            self.settings.max_output_tokens,
        )
        cache_key = digest(body)
        record = self.journal.get("review", cache_key)
        try:
            if record is None:
                if self.settings.request_exceeds_limit(len(canonical(body).encode())):
                    raise ValueError("Review request exceeds configured byte limit")
                # One vision request per artifact/plan; incomplete reviews need manual review.
                self.journal.put("review", cache_key, {"status": "started", "attempts": 1})
                raw = await self.provider.analyze(body)
                atomic_write(self.local(f".replicator/reviews/{cache_key}.json"), raw.encode())
                report = ReviewReport.model_validate(strict_json(raw))
                status = review_status(report, plan, result["artifact_sha256"])
                record = {
                    "status": "reviewed",
                    "attempts": 1,
                    "report": report.model_dump(),
                    "review_status": status,
                }
                self.journal.put("review", cache_key, record)
            if record["status"] == "reviewed":
                report = ReviewReport.model_validate(record["report"])
                result.update(
                    review_status=review_status(report, plan, result["artifact_sha256"]),
                    review=report.model_dump(),
                    reviewer="vision_model",
                )
            else:
                result["review_error"] = "Prior review incomplete; submit an explicit review"
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            result["review_error"] = (
                str(exc)
                if isinstance(exc, ProviderFailure)
                else "Review unavailable or invalid; submit an explicit review"
            )
        self.journal.put("job_result", key, result)
        return {}

    def compile(self, saver):
        graph = StateGraph(GraphState)
        for name, handler in (
            ("preprocess", self.prepare_images),
            ("analyze_missing", self.analyze_missing),
            ("resolve_design", self.compose),
            ("generate", self.generate_image),
            ("postprocess", self.finish),
            ("review", self.review),
        ):
            graph.add_node(name, diagnosed_stage(handler, name))
        graph.add_edge(START, "preprocess")
        graph.add_edge("preprocess", "analyze_missing")
        graph.add_edge("analyze_missing", "resolve_design")
        graph.add_edge("resolve_design", "generate")
        graph.add_edge("generate", "postprocess")
        graph.add_edge("postprocess", "review")
        graph.add_edge("review", END)
        return graph.compile(checkpointer=saver)

    async def execute(self, manifest: dict):
        lock = portalocker.Lock(str(self.local(".replicator/execution.lock")), timeout=0)
        try:
            lock.acquire()
        except portalocker.LockException:
            raise ValueError("Workspace already has an active workflow; resume later") from None
        try:
            self.allow_new_submissions = manifest.get("alignment_policy") == REFERENCE_POLICY
            self.journal.put("manifest", manifest["thread_id"], manifest)
            async with AsyncSqliteSaver.from_conn_string(
                str(self.local(".replicator/checkpoints-v2.sqlite"))
            ) as saver:
                graph = self.compile(saver)
                semaphore = asyncio.Semaphore(
                    manifest["options"].get("concurrency") or len(manifest["jobs"])
                )

                async def one(index, job):
                    async with semaphore:
                        key = result_key(manifest["thread_id"], index)
                        try:
                            if not self.allow_new_submissions:
                                link = self.journal.get("run_job", key)
                                if not link or not self.journal.get("image", link["key"]):
                                    raise ProviderFailure(
                                        "Historical redesign run is recovery-only; "
                                        "prepare a reference-first run"
                                    )
                            recovery = self.journal.get("analysis_recovery_link", key)
                            if recovery:
                                return {
                                    **(self.journal.get("job_result", key) or {}),
                                    **recovery,
                                    "generation_status": "blocked",
                                    "review_status": "not_ready",
                                }
                            local_result = self.journal.get("job_result", key) or {}
                            if local_result.get("postprocess_recovered"):
                                artifact = safe_path(self.root, local_result["artifact"])
                                if (
                                    hashlib.sha256(artifact.read_bytes()).hexdigest()
                                    != local_result["artifact_sha256"]
                                ):
                                    raise ValueError("Artifact changed after local recovery")
                                # Local recovery supersedes a pending postprocess checkpoint.
                                # Preserve subsequent explicit reviews and never replay its graph.
                                return local_result
                            config = {
                                "configurable": {
                                    "thread_id": digest(
                                        {"run": manifest["thread_id"], "image": job["image_id"]}
                                    )
                                }
                            }
                            snapshot = await graph.aget_state(config)
                            if not snapshot.values or snapshot.next:
                                initial = (
                                    None
                                    if snapshot.values
                                    else GraphState(
                                        manifest["thread_id"],
                                        {**manifest, "jobs": [{**job, "run_index": index}]},
                                    )
                                )
                                await graph.ainvoke(initial, config)
                            result = self.journal.get("job_result", key)
                            artifact = safe_path(self.root, result["artifact"])
                            if (
                                hashlib.sha256(artifact.read_bytes()).hexdigest()
                                != result["artifact_sha256"]
                            ):
                                raise ValueError("Artifact changed after generation")
                            if result["generation_status"] == "blocked":
                                result.update(
                                    generation_status="generated", review_status="review_required"
                                )
                                result.pop("error", None)
                                result.pop("detail", None)
                                self.journal.put("job_result", key, result)
                            return result
                        except asyncio.CancelledError:
                            raise
                        except Exception as exc:
                            if not isinstance(exc, (ProviderFailure, SubmissionUnknown)):
                                logging.getLogger(__name__).error(
                                    "Local workflow error %s; frames=%s",
                                    type(exc).__name__,
                                    [
                                        (Path(frame.filename).name, frame.name, frame.lineno)
                                        for frame in traceback.extract_tb(exc.__traceback__)
                                    ],
                                )
                            result = {
                                **(self.journal.get("job_result", key) or {}),
                                "generation_status": "blocked",
                                "review_status": "not_ready",
                                "error": type(exc).__name__,
                                **getattr(exc, "diagnostic", {}),
                                "detail": str(exc)
                                if isinstance(exc, (ProviderFailure, SubmissionUnknown))
                                else "Local validation or workflow error; "
                                "inspect frozen inputs and checkpoints",
                            }
                            self.journal.put("job_result", key, result)
                            return result

                results = await asyncio.gather(
                    *(one(i, job) for i, job in enumerate(manifest["jobs"]))
                )
                return aggregate(results)
        finally:
            lock.release()
