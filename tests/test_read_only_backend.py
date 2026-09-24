"""A check that reads the project database never migrates it
(test-run-migrates-the-live-project-db).

Session #266: a test of the CLAUDE.md state gate opened the developer's live
`.tausik/tausik.db` through the ordinary backend, `init_schema` migrated it, and
the deployed copy of the code then refused it as "newer than code" until the
next bootstrap. A reader has no business writing the schema.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import gate_claudemd_state  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


def _older_db(tmp_path) -> str:
    """A project database one schema version behind the code."""
    tausik = tmp_path / ".tausik"
    tausik.mkdir()
    db = str(tausik / "tausik.db")
    SQLiteBackend(db).close()
    conn = sqlite3.connect(db)
    conn.execute("UPDATE meta SET value=? WHERE key='schema_version'", (str(SCHEMA_VERSION - 1),))
    conn.commit()
    conn.close()
    return db


def _version(db: str) -> int:
    conn = sqlite3.connect(db)
    try:
        return int(conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0])
    finally:
        conn.close()


def test_a_read_only_backend_refuses_a_schema_mismatch_and_writes_nothing(tmp_path):
    db = _older_db(tmp_path)
    with pytest.raises(ServiceError, match="bootstrap"):
        SQLiteBackend(db, read_only=True)
    assert _version(db) == SCHEMA_VERSION - 1


def test_a_read_only_backend_reads_a_current_database(tmp_path):
    db = str(tmp_path / "cur.db")
    SQLiteBackend(db).close()
    be = SQLiteBackend(db, read_only=True)
    try:
        assert be.memory_list(None, 5) == []
        with pytest.raises(sqlite3.OperationalError):
            be._conn.execute("CREATE TABLE x (a)")
    finally:
        be.close()


def test_the_claudemd_gate_does_not_migrate_the_database_it_reads(tmp_path, monkeypatch):
    db = _older_db(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# CLAUDE.md\n", encoding="utf-8")
    monkeypatch.setattr("project_config.find_tausik_dir", lambda *a, **k: str(tmp_path / ".tausik"))
    outcome = gate_claudemd_state.run_claudemd_state_gate()
    assert _version(db) == SCHEMA_VERSION - 1
    assert "bootstrap" in str(outcome)


def test_the_ordinary_backend_still_migrates(tmp_path):
    db = _older_db(tmp_path)
    SQLiteBackend(db).close()
    assert _version(db) == SCHEMA_VERSION


def test_two_processes_upgrading_the_same_database_both_succeed(tmp_path):
    """The #266 race: two workers migrating one DB; the second must not die on a duplicate column."""
    import subprocess

    tausik = tmp_path / "race"
    tausik.mkdir()
    db = str(tausik / "tausik.db")
    SQLiteBackend(db).close()
    conn = sqlite3.connect(db)
    conn.execute("ALTER TABLE decisions DROP COLUMN rejected")
    conn.execute("UPDATE meta SET value=? WHERE key='schema_version'", (str(SCHEMA_VERSION - 1),))
    conn.commit()
    conn.close()
    scripts = os.path.join(os.path.dirname(__file__), "..", "scripts")
    code = (
        f"import sys; sys.path.insert(0, {os.path.abspath(scripts)!r}); "
        f"from project_backend import SQLiteBackend; SQLiteBackend({db!r}).close()"
    )
    procs = [
        subprocess.Popen([sys.executable, "-c", code], stderr=subprocess.PIPE) for _ in range(2)
    ]
    errors = [p.communicate(timeout=60)[1].decode("utf-8", "replace") for p in procs]
    assert all(p.returncode == 0 for p in procs), errors
    assert _version(db) == SCHEMA_VERSION
