import pytest

from image_replicator.storage import atomic_write


@pytest.mark.parametrize("code", [5, 32, 33])
def test_atomic_write_retries_transient_windows_denial(tmp_path, monkeypatch, code):
    import image_replicator.storage as storage

    target = tmp_path / "result"
    target.write_bytes(b"old")
    replace = storage.os.replace
    attempts = []

    def transient(source, destination):
        attempts.append(source)
        assert target.read_bytes() == b"old"
        if len(attempts) < 3:
            error = PermissionError("temporary sharing denial")
            error.winerror = code
            raise error
        replace(source, destination)

    monkeypatch.setattr(storage.os, "replace", transient)
    monkeypatch.setattr(storage.time, "sleep", lambda _: None)
    atomic_write(target, b"new")
    assert len(attempts) == 3
    assert target.read_bytes() == b"new"
    assert not list(tmp_path.glob(".write-*"))


def test_atomic_write_preserves_existing_file_on_permanent_denial(tmp_path, monkeypatch):
    import image_replicator.storage as storage

    target = tmp_path / "result"
    target.write_bytes(b"old")
    attempts = []

    def denied(*args):
        attempts.append(1)
        error = PermissionError("permanent access denial")
        error.winerror = 5
        raise error

    monkeypatch.setattr(storage.os, "replace", denied)
    monkeypatch.setattr(storage.time, "sleep", lambda _: None)
    with pytest.raises(PermissionError):
        atomic_write(target, b"new")
    assert len(attempts) == 4
    assert target.read_bytes() == b"old"
    assert not list(tmp_path.glob(".write-*"))
