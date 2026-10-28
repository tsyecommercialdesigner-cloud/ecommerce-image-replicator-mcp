import asyncio

import pytest

from image_replicator.config import Settings
from image_replicator.inputs import freeze
from image_replicator.models import RunOptions
from image_replicator.server import Service


@pytest.fixture
def service(workspace, monkeypatch):
    monkeypatch.setattr("image_replicator.server.read_keys", lambda _: {})
    instance = Service(Settings(workspace, workspace))
    manifest = freeze(workspace, RunOptions())
    instance.journal.put("manifest", manifest["thread_id"], manifest)
    return instance, manifest["thread_id"]


@pytest.mark.parametrize("real_http_client", [False, True])
async def test_provider_initialization_failure_is_visible_and_retryable(
    service, monkeypatch, real_http_client, caplog
):
    instance, thread = service
    secret = "fixture-proxy-password-do-not-log"
    if real_http_client:
        # Real httpx environment parsing, without making any HTTP request.
        monkeypatch.setenv("HTTPS_PROXY", f"unsupported://user:{secret}@example.invalid")
    else:

        def failing_provider(*_):
            raise ValueError(secret)

        monkeypatch.setattr("image_replicator.server.Provider", failing_provider)
    assert (await instance.execute(thread))["status"] == "scheduled"
    await asyncio.gather(*list(instance.tasks.values()), return_exceptions=True)
    status = instance.status(thread)
    assert status["status"] == "blocked"
    assert status["phase"] == "provider_initialization"
    assert status["error"] == "ValueError"
    assert secret not in str(status)
    assert secret not in caplog.text
    assert not instance.tasks
    assert all(job["status"] == "not_submitted" for job in status["jobs"])

    class Provider:
        async def close(self):
            pass

    class Engine:
        def __init__(self, *_):
            pass

        async def execute(self, manifest):
            assert manifest["thread_id"] == thread
            return {"status": "completed"}

    monkeypatch.setattr("image_replicator.server.Provider", lambda *_: Provider())
    monkeypatch.setattr("image_replicator.server.ImageWorkflow", Engine)
    # The frozen identity is reused, without prepare_run or supplier submission.
    assert (await instance.execute(thread))["status"] == "scheduled"
    await asyncio.gather(*list(instance.tasks.values()))
    assert instance.status(thread)["status"] == "completed"
    await instance.close()


@pytest.mark.parametrize("execution_fails", [False, True])
async def test_provider_cleanup_failure_does_not_pin_finished_task(
    service, monkeypatch, caplog, execution_fails
):
    instance, thread = service
    secret = "fixture-cleanup-secret-do-not-log"

    class Provider:
        async def close(self):
            raise RuntimeError(secret)

    class Engine:
        def __init__(self, *_):
            pass

        async def execute(self, _):
            if execution_fails:
                raise ValueError(secret)
            return {"status": "completed"}

    monkeypatch.setattr("image_replicator.server.Provider", lambda *_: Provider())
    monkeypatch.setattr("image_replicator.server.ImageWorkflow", Engine)
    await instance.execute(thread)
    await asyncio.gather(*list(instance.tasks.values()), return_exceptions=True)
    assert not instance.tasks
    status = instance.status(thread)
    assert status["status"] == ("blocked" if execution_fails else "completed")
    assert secret not in str(status)
    assert "provider_cleanup" in caplog.text
    assert secret not in caplog.text


async def test_shutdown_before_worker_starts_clears_registry_and_records_interruption(service):
    instance, thread = service
    await instance.execute(thread)
    await instance.close()  # No event-loop yield between scheduling and shutdown.
    assert not instance.tasks
    assert instance.status(thread)["status"] == "interrupted"


async def test_unwritable_journal_failure_is_observed_without_leaking_payload(
    service, monkeypatch, caplog
):
    instance, thread = service
    original = instance.journal.put
    secret = "fixture-journal-payload-do-not-log"

    def put(kind, key, value):
        if kind == "run":
            raise OSError(secret)
        return original(kind, key, value)

    monkeypatch.setattr(instance.journal, "put", put)
    await instance.execute(thread)
    tasks = list(instance.tasks.values())
    await asyncio.gather(*tasks, return_exceptions=True)
    assert not instance.tasks
    assert "worker failed (OSError)" in caplog.text
    assert secret not in caplog.text
