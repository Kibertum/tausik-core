"""Upgrading a TAUSIK 1.8 database reaches the current schema (github#51, gitlab#18).

Reported by the owner from a consumer project on 2026-09-14: `init_schema` on a
schema-44 database ran the cumulative creation scripts first, so
`CREATE TABLE IF NOT EXISTS actz_points` built the table in its CURRENT shape
(with `tz_ref`); then v53's `ALTER TABLE actz_points ADD COLUMN tz_ref` died on
"duplicate column name". And because the version stamp was written only after
the whole chain, v45–v52 stayed committed under a stamp of 44 — the next start
failed earlier still.

The database here is the real one: `tests/fixtures/schema_v44_tausik_1_8_0.sql`
is the DDL the v1.8.0 tag's own `init_schema` produced, frozen. The upgrade goes
through `backend_init.init_schema`, the consumer's path — not `run_migrations`
alone, which is the path the old tests exercised and the reason they were green.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import backend_migrations  # noqa: E402
from backend_init import init_schema  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402

FIXTURE = os.path.join(_ROOT, "tests", "fixtures", "schema_v44_tausik_1_8_0.sql")


def _v44(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(open(FIXTURE, encoding="utf-8").read())
    conn.commit()
    return conn


def _shape(conn: sqlite3.Connection) -> dict[str, set[str]]:
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    return {t: {r[1] for r in conn.execute(f"PRAGMA table_info({t})")} for t in tables}


def _version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0])


def test_the_fixture_is_a_1_8_database():
    conn = sqlite3.connect(":memory:")
    conn.executescript(open(FIXTURE, encoding="utf-8").read())
    assert _version(conn) == 44
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "actz_points" not in names  # v52 creates it; 1.8 never had it


def test_a_1_8_database_upgrades_to_the_fresh_shape(tmp_path):
    conn = _v44(str(tmp_path / "consumer.db"))
    init_schema(conn)
    assert _version(conn) == SCHEMA_VERSION
    fresh = sqlite3.connect(str(tmp_path / "fresh.db"))
    init_schema(fresh)
    upgraded, expected = _shape(conn), _shape(fresh)
    missing_tables = set(expected) - set(upgraded)
    assert not missing_tables, missing_tables
    missing_cols = {t: expected[t] - upgraded[t] for t in expected if expected[t] - upgraded[t]}
    assert not missing_cols, missing_cols
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_an_interrupted_upgrade_keeps_its_place_and_resumes(tmp_path, monkeypatch):
    """NEGATIVE: a chain that fails after v50 leaves the stamp at 50 — not 44 —
    and a second start completes it without duplicate columns or tables."""
    path = str(tmp_path / "consumer.db")
    conn = _v44(path)
    original = dict(backend_migrations.MIGRATIONS)
    broken = dict(original)
    broken[51] = ["SELECT no_such_function_breaks_v51()"]
    monkeypatch.setattr(backend_migrations, "MIGRATIONS", broken)
    with pytest.raises(sqlite3.OperationalError):
        init_schema(conn)
    assert _version(conn) == 50
    monkeypatch.setattr(backend_migrations, "MIGRATIONS", original)
    init_schema(conn)
    assert _version(conn) == SCHEMA_VERSION


def test_an_add_column_the_table_already_has_is_skipped_not_fatal(tmp_path):
    """NEGATIVE: the tolerance is narrow — an ALTER onto a MISSING table still fails."""
    conn = sqlite3.connect(str(tmp_path / "x.db"))
    conn.execute("CREATE TABLE t(a TEXT, b TEXT)")
    assert backend_migrations._column_already_there(conn, "ALTER TABLE t ADD COLUMN b TEXT")
    assert not backend_migrations._column_already_there(conn, "ALTER TABLE t ADD COLUMN c TEXT")
    assert not backend_migrations._column_already_there(conn, "ALTER TABLE nope ADD COLUMN c TEXT")


def test_a_database_the_1_9_0_upgrade_already_broke_is_carried_up(tmp_path, monkeypatch):
    """The consumer's actual state after 1.9.0: v45..v52 committed, stamp left
    at 44. The fixed chain replays from 45 and must reach the current version."""
    conn = _v44(str(tmp_path / "broken.db"))
    original = dict(backend_migrations.MIGRATIONS)
    upto52 = {k: v for k, v in original.items() if k <= 52}
    monkeypatch.setattr(backend_migrations, "MIGRATIONS", upto52)
    backend_migrations.run_migrations(conn, 44)
    conn.execute("UPDATE meta SET value='44' WHERE key='schema_version'")  # what 1.9.0 left
    conn.commit()
    monkeypatch.setattr(backend_migrations, "MIGRATIONS", original)
    init_schema(conn)
    assert _version(conn) == SCHEMA_VERSION
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
