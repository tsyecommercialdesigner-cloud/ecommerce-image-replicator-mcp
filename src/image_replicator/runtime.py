"""Initialize state without replacing the workspace owner's Windows access policy."""

import sqlite3
import sys
from pathlib import Path

from .inputs import safe_path
from .storage import Journal


class StartupError(Exception):
    """Actionable startup failure safe to print on stderr."""


def open_journal(workspace: Path) -> Journal:
    try:
        root = workspace.resolve(strict=True)
        runtime = safe_path(root, ".replicator", exists=False)
        # Windows 0o700 installs a protected OWNER RIGHTS ACL. With an elevated
        # creator, the owner can be Administrators, locking out its medium token.
        # Inherit the operator-controlled workspace ACL instead; POSIX stays private.
        if sys.platform == "win32":
            runtime.mkdir(exist_ok=True)
        else:
            runtime.mkdir(exist_ok=True, mode=0o700)
        return Journal(safe_path(root, ".replicator/journal.sqlite", exists=False))
    except PermissionError:
        raise StartupError(
            "Workspace runtime access denied. Check permissions on --workspace and "
            "its .replicator directory for the account running the Host. Existing ACLs "
            "are not changed automatically. Preserve .replicator and its databases; "
            "see MANUAL.md for targeted permission repair."
        ) from None
    except FileNotFoundError:
        raise StartupError(
            "Workspace directory not found. Create the --workspace directory first "
            "using the same account as the Host."
        ) from None
    except sqlite3.OperationalError:
        raise StartupError(
            "Cannot initialize workspace journal. Check .replicator read/write access, "
            "available disk space and database locks. Preserve existing state; "
            "do not delete the database to resolve startup errors."
        ) from None
