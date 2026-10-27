"""SQLite operation journal complements LangGraph's checkpoint database."""

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def strict_json(raw: str):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result

    def reject(value):
        raise ValueError("Non-finite JSON number")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject)


def atomic_write(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


class Journal:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS records (
                    kind TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
                    PRIMARY KEY(kind,key)
                );
            """)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        try:
            conn.execute("PRAGMA synchronous=FULL")
            with conn:
                yield conn
        finally:
            conn.close()

    def get(self, kind: str, key: str):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM records WHERE kind=? AND key=?", (kind, key)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, kind: str, key: str, value):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO records VALUES(?,?,?) ON CONFLICT(kind,key) "
                "DO UPDATE SET value=excluded.value",
                (kind, key, canonical(value)),
            )

    def records(self, kind: str):
        with self.connect() as conn:
            rows = conn.execute("SELECT key,value FROM records WHERE kind=?", (kind,)).fetchall()
        return [(key, json.loads(value)) for key, value in rows]
