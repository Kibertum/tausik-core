"""v78 keeps historical command-only verification rows powerless."""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backend_migrations as bm  # noqa: E402
from backend_schema import SCHEMA_SQL  # noqa: E402
from test_migrations import V1_SCHEMA  # noqa: E402

_V78 = 78


def test_v78_leaves_command_only_rows_without_structured_rights():
    conn = sqlite3.connect(":memory:")
    conn.isolation_level = None
    conn.executescript(V1_SCHEMA)
    removed = {v: bm.MIGRATIONS.pop(v) for v in sorted(bm.MIGRATIONS) if v >= _V78}
    try:
        assert bm.run_migrations(conn, 1) == _V78 - 1
    finally:
        bm.MIGRATIONS.update(removed)
    conn.execute(
        "INSERT INTO verification_runs "
        "(task_slug, scope, command, exit_code, files_hash, ran_at) "
        "VALUES ('legacy', 'standard', 'trigger=verify|sig=abc|files=a.py', "
        "0, 'hash', '2026-10-12T00:00:00Z')"
    )

    bm.run_migrations(conn, _V78 - 1)

    row = conn.execute(
        "SELECT run_trigger, run_files_json, gate_signature, replay_policy, "
        "presentation_policy FROM verification_runs WHERE task_slug='legacy'"
    ).fetchone()
    assert row == (None, None, None, None, None)
    conn.close()


def _fresh_or_migrated(mode: str) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.isolation_level = None
    if mode == "fresh":
        conn.executescript(SCHEMA_SQL)
        return conn
    conn.executescript(V1_SCHEMA)
    bm.run_migrations(conn, 1)
    return conn


@pytest.mark.parametrize("mode", ["fresh", "migrated"])
@pytest.mark.parametrize(
    ("column", "invalid"),
    [("replay_policy", "cached_forever"), ("presentation_policy", "reusable")],
)
def test_policy_constraints_match_on_fresh_and_migrated_databases(mode, column, invalid):
    conn = _fresh_or_migrated(mode)
    try:
        conn.execute(
            "INSERT INTO verification_runs "
            "(task_slug, scope, command, exit_code, files_hash, ran_at) "
            "VALUES ('constraint-probe', 'standard', 'audit', 0, 'hash', "
            "'2026-10-12T00:00:00Z')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(f"UPDATE verification_runs SET {column}=?", (invalid,))
    finally:
        conn.close()
