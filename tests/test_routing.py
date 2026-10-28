import asyncio
import copy
import shutil

import portalocker
import pytest
from test_workflow import FakeProvider

from image_replicator.config import Settings
from image_replicator.inputs import freeze, inspect_images
from image_replicator.models import RunOptions
from image_replicator.provider import SubmissionUnknown
from image_replicator.routing import WorkspaceRouter
from image_replicator.storage import canonical
from image_replicator.workflow_v2 import ImageWorkflow


@pytest.fixture
def projects(workspace):
    a = workspace / "project-a"
    b = workspace / "project-b"
    for root in (a, b):
        root.mkdir()
        for name in ("references", "products", "brief", "prompts"):
            shutil.copytree(workspace / name, root / name)
        (root / "prompts/images_1.json").write_text(
            canonical([{"texts": [], "scene": "fixture"}] * 3), encoding="utf-8"
        )
    settings = Settings(workspace, workspace, 10, 10_000_000, 8000, poll_seconds=0)
    return settings, a, b


def prepare(router, root, **options):
    service = router.for_workspace(str(root))
    manifest = freeze(root, RunOptions(**options))
    service.journal.put("manifest", manifest["thread_id"], manifest)
    return service, manifest, router.bind(service, manifest["thread_id"])


def test_same_legacy_id_is_isolated_and_stable_across_restart(projects):
    settings, a, b = projects
    router = WorkspaceRouter(settings, task_workspaces=True)
    sa, manifest, ra = prepare(router, a)
    sb = router.for_workspace(str(b))
    # Historical IDs are local identities; force an exact collision, not just filenames.
    sb.journal.put("manifest", manifest["thread_id"], copy.deepcopy(manifest))
    rb = router.bind(sb, manifest["thread_id"])
    assert ra != rb
    sa.journal.put("run", manifest["thread_id"], {"status": "prepared", "marker": "a"})
    sb.journal.put("run", manifest["thread_id"], {"status": "prepared", "marker": "b"})
    restarted = WorkspaceRouter(settings, task_workspaces=True)
    for run_id, expected, root in ((ra, "a", a), (rb, "b", b)):
        service, thread = restarted.resolve(run_id=run_id)
        assert service.settings.workspace == root
        assert service.status(thread)["marker"] == expected
        assert restarted.bind(service, thread) == run_id
    with pytest.raises(ValueError, match="Legacy"):
        restarted.resolve(thread_id=manifest["thread_id"])
    with pytest.raises(ValueError, match="exactly one"):
        restarted.resolve(run_id=ra, thread_id=manifest["thread_id"])


def test_fixed_workspace_retains_legacy_id_and_rejects_switch(projects):
    settings, a, b = projects
    from dataclasses import replace

    router = WorkspaceRouter(replace(settings, workspace=a))
    service, manifest, run_id = prepare(router, a)
    assert router.resolve(thread_id=manifest["thread_id"])[0] is service
    assert router.resolve(run_id=run_id)[0] is service
    with pytest.raises(ValueError, match="Fixed-workspace"):
        router.for_workspace(str(b))


def test_binding_tampering_and_policy_changes_are_rejected(projects):
    settings, a, b = projects
    router = WorkspaceRouter(settings, task_workspaces=True, allowed_roots=(a,))
    _, _, run_id = prepare(router, a)
    with pytest.raises(ValueError, match="outside"):
        router.for_workspace(str(b))
    with pytest.raises(ValueError):
        router.for_workspace(str(a / ".." / "project-b"))
    with pytest.raises(ValueError):
        router.for_workspace("relative")
    narrowed = WorkspaceRouter(settings, task_workspaces=True, allowed_roots=(b,))
    with pytest.raises(ValueError, match="outside"):
        narrowed.resolve(run_id=run_id)
    binding = router.registry.get("binding", run_id)
    binding["workspace"] = str(b)
    router.registry.put("binding", run_id, binding)
    with pytest.raises(ValueError, match="binding"):
        router.resolve(run_id=run_id)


def test_missing_state_is_not_recreated(projects):
    settings, a, _ = projects
    router = WorkspaceRouter(settings, task_workspaces=True)
    _, _, run_id = prepare(router, a)
    journal = a / ".replicator/journal.sqlite"
    journal.rename(journal.with_suffix(".saved"))
    with pytest.raises(FileNotFoundError):
        router.resolve(run_id=run_id)
    assert not journal.exists()


def test_concurrent_registry_writers_keep_binding(projects):
    from concurrent.futures import ThreadPoolExecutor

    settings, a, _ = projects
    router = WorkspaceRouter(settings, task_workspaces=True)
    _, manifest, run_id = prepare(router, a)

    def bind(_):
        other = WorkspaceRouter(settings, task_workspaces=True)
        return other.bind(other.for_workspace(str(a)), manifest["thread_id"])

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert set(pool.map(bind, range(12))) == {run_id}


def test_concurrent_workspace_selection_uses_one_service(projects):
    from concurrent.futures import ThreadPoolExecutor

    settings, a, _ = projects
    router = WorkspaceRouter(settings, task_workspaces=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        selected = list(pool.map(lambda _: router.for_workspace(str(a)), range(12)))
    assert all(service is selected[0] for service in selected)


def test_workspace_link_is_rejected(projects):
    import os
    import subprocess

    settings, a, _ = projects
    link = a.parent / "alias"
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(a)], check=True, capture_output=True
        )
    else:
        link.symlink_to(a, target_is_directory=True)
    try:
        with pytest.raises(ValueError, match="symlinks and junctions"):
            WorkspaceRouter(settings, task_workspaces=True).for_workspace(str(link))
    finally:
        if os.name == "nt":
            link.rmdir()
        else:
            link.unlink()


async def test_revision_and_review_stay_in_parent_workspace(projects):
    from test_adaptation import make_report

    from image_replicator.models import Delta, RevisionUpdate

    settings, a, b = projects
    router = WorkspaceRouter(settings, task_workspaces=True)
    sa, ma, ra = prepare(router, a, max_visual_revisions=1)
    sb, mb, rb = prepare(router, b, max_visual_revisions=1)
    await ImageWorkflow(sa.settings, sa.journal, FakeProvider()).execute(ma)
    sa.record_review(ma["thread_id"], make_report(sa, ma))
    child = router.expose(
        sa,
        sa.revision(
            ma["thread_id"],
            [
                RevisionUpdate(
                    image_id=ma["jobs"][0]["image_id"], delta=Delta(texts=[], scene="Revised")
                )
            ],
        ),
    )
    restarted = WorkspaceRouter(settings, task_workspaces=True)
    assert restarted.resolve(run_id=child["run_id"])[0].settings.workspace == a
    assert child["run_id"] not in {ra, rb}
    assert not sb.journal.records("revision_budget")
    assert sb.status(mb["thread_id"])["status"] == "prepared"


async def test_projects_execute_concurrently_and_replay_without_new_posts(projects, monkeypatch):
    settings, a, b = projects
    router = WorkspaceRouter(settings, task_workspaces=True)
    pairs = [prepare(router, root) for root in (a, b)]
    reached = set()
    both = asyncio.Event()

    class Provider(FakeProvider):
        async def submit(self, body):
            reached.add(id(self))
            if len(reached) == 2:
                both.set()
            await asyncio.wait_for(both.wait(), timeout=10)
            return await super().submit(body)

    providers = [Provider(), Provider()]

    async def execute(pair, provider):
        service, manifest, _ = pair
        return await ImageWorkflow(service.settings, service.journal, provider).execute(manifest)

    results = await asyncio.gather(
        *(execute(pair, p) for pair, p in zip(pairs, providers, strict=True))
    )
    assert all(r["generation_complete"] for r in results)
    assert all(len(p.submissions) == 3 for p in providers)
    restarted = WorkspaceRouter(settings, task_workspaces=True)
    for (_, manifest, run_id), provider, root in zip(pairs, providers, (a, b), strict=True):
        service, thread = restarted.resolve(run_id=run_id)
        result = await ImageWorkflow(service.settings, service.journal, provider).execute(manifest)
        assert result["generation_complete"]
        assert len(provider.submissions) == 3
        for artifact in service.status(thread)["artifacts"]:
            assert (root / artifact).is_file()
        assert service.settings.workspace == root


async def test_workspace_lock_does_not_block_other_project(projects):
    settings, a, b = projects
    router = WorkspaceRouter(settings, task_workspaces=True)
    sa, ma, _ = prepare(router, a)
    sb, mb, _ = prepare(router, b)
    pa, pb = FakeProvider(), FakeProvider()
    with portalocker.Lock(str(a / ".replicator/execution.lock"), timeout=0):
        with pytest.raises(ValueError, match="active workflow"):
            await ImageWorkflow(sa.settings, sa.journal, pa).execute(ma)
        result = await ImageWorkflow(sb.settings, sb.journal, pb).execute(mb)
    assert not pa.submissions
    assert result["generation_complete"]
    assert len(pb.submissions) == 3


async def test_unknown_receipt_survives_restart_and_other_project_is_independent(projects):
    settings, a, b = projects
    router = WorkspaceRouter(settings, task_workspaces=True)
    sa, ma, ra = prepare(router, a)
    sb, mb, _ = prepare(router, b)
    pa, pb = FakeProvider(), FakeProvider()
    pa.submit_error = SubmissionUnknown("fixture timeout")
    await ImageWorkflow(sa.settings, sa.journal, pa).execute(ma)
    assert len(pa.submissions) == 3
    restarted = WorkspaceRouter(settings, task_workspaces=True)
    recovered, _ = restarted.resolve(run_id=ra)
    await ImageWorkflow(recovered.settings, recovered.journal, pa).execute(ma)
    assert len(pa.submissions) == 3
    result = await ImageWorkflow(sb.settings, sb.journal, pb).execute(mb)
    assert result["generation_complete"] and len(pb.submissions) == 3


async def test_service_shutdown_restart_resumes_pending_ids_in_both_projects(projects, monkeypatch):
    settings, a, b = projects
    release = asyncio.Event()

    class PendingProvider(FakeProvider):
        def __init__(self):
            super().__init__()
            self.queried = asyncio.Event()

        async def query(self, task_id):
            self.queried.set()
            await release.wait()
            return await super().query(task_id)

        async def close(self):
            pass

    providers = {root: PendingProvider() for root in (a, b)}
    monkeypatch.setattr("image_replicator.server.read_keys", lambda _: {})
    monkeypatch.setattr(
        "image_replicator.server.Provider", lambda config, _: providers[config.workspace]
    )
    router = WorkspaceRouter(settings, task_workspaces=True)
    pairs = [
        prepare(router, root, selected_image_ids=[inspect_images(root)[0]["image_id"]])
        for root in (a, b)
    ]
    for service, manifest, _ in pairs:
        await service.execute(manifest["thread_id"])
        await service.execute(manifest["thread_id"])  # duplicate scheduling is idempotent
        assert len(service.tasks) == 1
    await asyncio.wait_for(asyncio.gather(*(p.queried.wait() for p in providers.values())), 15)
    await router.close()
    assert all(len(p.submissions) == 1 for p in providers.values())
    release.set()
    restarted = WorkspaceRouter(settings, task_workspaces=True)
    for _, _, run_id in pairs:
        service, thread = restarted.resolve(run_id=run_id)
        await service.execute(thread)
    await asyncio.wait_for(
        asyncio.gather(
            *(task for s in restarted.services.values() for task in list(s.tasks.values()))
        ),
        15,
    )
    assert all(len(p.submissions) == 1 for p in providers.values())
    for _, _, run_id in pairs:
        service, thread = restarted.resolve(run_id=run_id)
        assert service.status(thread)["generation_complete"]
    await restarted.close()
