import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PureWindowsPath

import pytest

from image_replicator.inputs import comparable_path, safe_path
from image_replicator.storage import atomic_write


@pytest.mark.skipif(os.name != "nt", reason="CPython Windows realpath implementation")
@pytest.mark.parametrize("errors", [(2, 3), (3, 2)])
def test_realpath_race_does_not_reject_contained_missing_output(tmp_path, monkeypatch, errors):
    import ntpath

    root = tmp_path.resolve()
    target = root / "concurrent/new/output.png"
    original = ntpath._getfinalpathname
    fallback = ntpath._getfinalpathname_nonstrict
    count = 0

    def probe(path):
        nonlocal count
        if ntpath.normcase(path) == ntpath.normcase(str(target)):
            error = FileNotFoundError("controlled missing-file/directory race")
            error.winerror = errors[min(count, 1)]
            count += 1
            raise error
        return original(path)

    def nonstrict(path, **kwargs):
        if ntpath.normcase(path) == ntpath.normcase(str(target)):
            return "\\\\?\\" + str(target)
        return fallback(path, **kwargs)

    monkeypatch.setattr(ntpath, "_getfinalpathname", probe)
    monkeypatch.setattr(ntpath, "_getfinalpathname_nonstrict", nonstrict)
    # Exercise the real stdlib algorithm, including its prefix retention branch.
    assert str(target.resolve(strict=False)).startswith("\\\\?\\")
    count = 0
    result = safe_path(root, "concurrent/new/output.png", exists=False)
    assert result == target
    assert result.relative_to(root) == Path("concurrent/new/output.png")


@pytest.mark.parametrize(
    "root,target",
    [
        (r"C:\work", r"\\?\C:\work\out.png"),
        (r"\\?\C:\work", r"C:\work\out.png"),
        (r"\\server\share\work", r"\\?\UNC\server\share\work\out.png"),
        (r"\\?\UNC\server\share\work", r"\\server\share\work\out.png"),
    ],
)
def test_regular_and_extended_namespaces_compare_equally(root, target):
    assert comparable_path(PureWindowsPath(target)).is_relative_to(
        comparable_path(PureWindowsPath(root))
    )


@pytest.mark.parametrize(
    "target",
    [
        r"\\?\C:\outside\out.png",
        r"\\?\D:\work\out.png",
        r"\\?\UNC\other\share\work\out.png",
        r"\\?\UNC\server\other\work\out.png",
    ],
)
def test_namespace_normalization_cannot_turn_outside_into_inside(target):
    assert not comparable_path(PureWindowsPath(target)).is_relative_to(
        comparable_path(PureWindowsPath(r"C:\work"))
    )


@pytest.mark.parametrize(
    "path",
    [
        r"\\?\GLOBALROOT\Device\HarddiskVolume1\work",
        r"\\.\PhysicalDrive0",
        r"\\?\C:\work\ambiguous.",
        r"\\?\C:\work\ambiguous ",
    ],
)
def test_device_and_ambiguous_namespaces_are_rejected(path):
    with pytest.raises(ValueError):
        comparable_path(PureWindowsPath(path))


def test_resolved_outside_target_is_still_rejected(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    candidate = root / "image.png"
    outside = tmp_path / "outside.png"
    original = Path.resolve

    def resolve(path, **kwargs):
        if path == candidate:
            return outside
        return original(path, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    with pytest.raises(ValueError, match="escapes"):
        safe_path(root, "image.png", exists=False)


@pytest.mark.skipif(os.name != "nt", reason="Windows extended root and junctions")
def test_extended_root_binding_is_preserved_and_junction_is_rejected(tmp_path):
    import subprocess

    root = tmp_path.resolve()
    extended = Path("\\\\?\\" + str(root))
    result = safe_path(extended, "new/image.png", exists=False)
    assert result == extended / "new/image.png"
    assert result.relative_to(extended) == Path("new/image.png")
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    link = tmp_path / "redirect"
    try:
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True
        )
        with pytest.raises(ValueError, match="Symlink"):
            safe_path(root, "redirect/image.png", exists=False)
    finally:
        if link.is_junction():
            link.rmdir()
        outside.rmdir()


@pytest.mark.parametrize("relative", ["../outside", "/outside"])
def test_traversal_and_absolute_paths_remain_rejected(tmp_path, relative):
    with pytest.raises(ValueError):
        safe_path(tmp_path, relative, exists=False)


@pytest.mark.skipif(os.name != "nt", reason="Windows drive-relative and alternate streams")
@pytest.mark.parametrize("relative", ["C:out.png", "out.png:stream", "\\rooted.png"])
def test_windows_nonrelative_paths_are_rejected(tmp_path, relative):
    with pytest.raises(ValueError):
        safe_path(tmp_path, relative, exists=False)


def test_parallel_directory_creation_and_atomic_writes_remain_contained(tmp_path):
    for batch in range(5):

        def one(index, batch=batch):
            relative = f"batch-{batch}/group-{index % 6}/{index}.png"
            path = safe_path(tmp_path, relative, exists=False)
            atomic_write(path, str(index).encode())
            assert safe_path(tmp_path, relative).read_bytes() == str(index).encode()
            assert path.relative_to(tmp_path) == Path(relative)

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(one, range(40)))


@pytest.mark.skipif(os.name != "nt", reason="Preserve Windows extended-root task identities")
def test_existing_extended_root_run_binding_survives_router_restart(workspace):
    from image_replicator.config import Settings
    from image_replicator.inputs import freeze
    from image_replicator.models import RunOptions
    from image_replicator.routing import WorkspaceRouter

    extended = Path("\\\\?\\" + str(workspace.resolve()))
    settings = Settings(workspace, workspace)
    router = WorkspaceRouter(settings, task_workspaces=True, allowed_roots=(workspace,))
    service = router.for_workspace(str(extended))
    manifest = freeze(service.settings.workspace, RunOptions())
    service.journal.put("manifest", manifest["thread_id"], manifest)
    run_id = router.bind(service, manifest["thread_id"])
    restarted = WorkspaceRouter(settings, task_workspaces=True, allowed_roots=(workspace,))
    recovered, thread_id = restarted.resolve(run_id=run_id)
    assert thread_id == manifest["thread_id"]
    assert recovered.settings.workspace == extended
    assert restarted.bind(recovered, thread_id) == run_id
