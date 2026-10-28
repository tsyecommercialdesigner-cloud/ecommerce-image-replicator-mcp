"""Persistent task routing; never retarget a registered task from a tool argument."""

import asyncio
import os
import re
from dataclasses import replace
from pathlib import Path
from threading import RLock

from .config import Settings
from .inputs import safe_path
from .runtime import StartupError, open_journal
from .storage import Journal, canonical, digest


class WorkspaceRouter:
    def __init__(
        self, settings: Settings, *, task_workspaces=False, allowed_roots=(), state_dir=None
    ):
        self.settings = settings
        self.default = None if task_workspaces else settings.workspace
        self.allowed = tuple(self.canonical_root(p) for p in allowed_roots)
        self.state_dir = self.canonical_root(state_dir or settings.project_root)
        self._lock = RLock()
        self.services: dict = {}
        self._registry: Journal | None = None
        # Retain fixed-mode startup validation and legacy behavior.
        if self.default is not None:
            self.for_workspace()

    @staticmethod
    def canonical_root(value: Path) -> Path:
        path = Path(value)
        if not path.is_absolute() or ".." in path.parts:
            raise ValueError("Workspace must be an absolute directory without parent traversal")
        cursor = Path(path.anchor)
        for part in path.parts[1:]:
            cursor /= part
            if cursor.is_symlink() or cursor.is_junction():
                raise ValueError("Workspace symlinks and junctions are not allowed")
        try:
            root = path.resolve(strict=True)
        except FileNotFoundError:
            raise StartupError(
                "Workspace directory not found. Create the directory first."
            ) from None
        if not root.is_dir():
            raise ValueError("Workspace must be an existing directory")
        return root

    def checked_root(self, value: Path) -> Path:
        root = self.canonical_root(value)
        if self.allowed and not any(root.is_relative_to(parent) for parent in self.allowed):
            raise ValueError("Workspace is outside configured allowed roots")
        return root

    @property
    def registry(self):
        with self._lock:
            if self._registry is None:
                self._registry = open_journal(self.state_dir, filename="task-registry.sqlite")
            return self._registry

    def for_workspace(self, workspace: str | None = None):
        from .server import Service

        selected = Path(workspace) if workspace is not None else self.default
        if selected is None:
            raise ValueError("Supply an absolute workspace when no startup workspace is configured")
        root = self.checked_root(selected)
        if self.default is not None and root != self.checked_root(self.default):
            raise ValueError("Fixed-workspace server cannot select another workspace")
        key = os.path.normcase(str(root))
        with self._lock:
            if key not in self.services:
                self.services[key] = Service(replace(self.settings, workspace=root))
            return self.services[key]

    def bind(self, service, thread_id: str) -> str:
        service.manifest(thread_id)
        root = self.checked_root(service.settings.workspace)
        binding = {"workspace": os.path.normcase(str(root)), "thread_id": thread_id}
        run_id = "run_" + digest(binding)
        # No replace: a registered ID can never silently change its workspace.
        with self.registry.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO records VALUES(?,?,?)",
                ("binding", run_id, canonical(binding)),
            )
        if self.registry.get("binding", run_id) != binding:
            raise ValueError("Task binding conflict")
        return run_id

    def resolve(self, *, run_id: str | None = None, thread_id: str | None = None):
        if (run_id is None) == (thread_id is None):
            raise ValueError("Supply exactly one run_id or legacy thread_id")
        if run_id is None:
            if self.default is None:
                raise ValueError("Legacy thread_id needs a fixed workspace or import_run first")
            service = self.for_workspace()
            service.manifest(thread_id)
            return service, thread_id
        if not re.fullmatch(r"run_[a-f0-9]{64}", run_id):
            raise ValueError("Invalid run_id")
        binding = self.registry.get("binding", run_id)
        if binding is None or "run_" + digest(binding) != run_id:
            raise ValueError("Unknown or invalid task binding")
        root = self.checked_root(Path(binding["workspace"]))
        # Missing/moved state must not cause a fresh empty database to be created.
        safe_path(root, ".replicator/journal.sqlite")
        service = self.for_workspace(str(root))
        service.manifest(binding["thread_id"])
        return service, binding["thread_id"]

    def expose(self, service, result: dict) -> dict:
        thread_id = result["thread_id"]
        return {
            **result,
            "run_id": self.bind(service, thread_id),
            "workspace": str(service.settings.workspace),
        }

    async def close(self):
        await asyncio.gather(*(service.close() for service in self.services.values()))
