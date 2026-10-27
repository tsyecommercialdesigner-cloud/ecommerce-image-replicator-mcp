import os
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import pytest

from image_replicator import runtime


def test_server_version_matches_installed_distribution(tmp_path):
    from image_replicator.config import Settings
    from image_replicator.server import create_server

    server = create_server(Settings(project_root=tmp_path, workspace=tmp_path))
    assert server.version == version("ecommerce-image-replicator-mcp")


def test_existing_journal_and_private_configuration_preserved(tmp_path):
    config = tmp_path / ".env"
    config.write_text("fixture-only", encoding="utf-8")
    journal = runtime.open_journal(tmp_path)
    journal.put("fixture", "task", {"task_id": "preserve-me"})
    reopened = runtime.open_journal(tmp_path)
    assert reopened.get("fixture", "task") == {"task_id": "preserve-me"}
    assert config.read_text(encoding="utf-8") == "fixture-only"


def test_permission_failure_is_actionable_and_does_not_repair_acl(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("private error content")

    monkeypatch.setattr(runtime, "safe_path", denied)
    with pytest.raises(runtime.StartupError, match="Existing ACLs") as caught:
        runtime.open_journal(tmp_path)
    assert "private error content" not in str(caught.value)
    assert not (tmp_path / ".replicator").exists()


def test_permission_failure_cli_is_stderr_only(tmp_path, monkeypatch, capsys):
    from image_replicator import server

    def denied(*args, **kwargs):
        raise PermissionError("private error content")

    monkeypatch.setattr(runtime, "safe_path", denied)
    monkeypatch.setattr(
        sys, "argv", ["server", "--project-root", str(tmp_path), "--workspace", str(tmp_path)]
    )
    with pytest.raises(SystemExit) as caught:
        server.main()
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "Workspace runtime access denied" in captured.err
    assert "private error content" not in captured.err


def test_missing_workspace_cli_exits_nonzero_without_stdout(tmp_path):
    project = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "image_replicator",
            "--project-root",
            str(project),
            "--workspace",
            str(tmp_path / "missing"),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 2
    assert not result.stdout
    assert "Workspace directory not found" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.skipif(sys.platform != "win32", reason="Windows ACL inheritance")
def test_windows_runtime_inherits_parent_acl(tmp_path):
    import win32api
    import win32con
    import win32security

    # A dedicated test workspace with an explicit inheritable user grant.
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        user = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
    finally:
        token.Close()
    parent_acl = win32security.ACL()
    parent_acl.AddAccessAllowedAceEx(win32security.ACL_REVISION, 3, 0x1F01FF, user)
    win32security.SetNamedSecurityInfo(
        str(tmp_path),
        win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
        None,
        None,
        parent_acl,
        None,
    )
    runtime.open_journal(tmp_path)
    security = win32security.GetFileSecurity(
        str(tmp_path / ".replicator"), win32security.DACL_SECURITY_INFORMATION
    )
    control, _ = security.GetSecurityDescriptorControl()
    assert not control & win32security.SE_DACL_PROTECTED
    acl = security.GetSecurityDescriptorDacl()
    assert any(
        acl.GetAce(i)[2] == user and acl.GetAce(i)[1] & 0x1F01FF == 0x1F01FF
        for i in range(acl.GetAceCount())
    )


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_posix_runtime_remains_private(tmp_path):
    runtime.open_journal(tmp_path)
    assert os.stat(tmp_path / ".replicator").st_mode & 0o777 == 0o700
