"""v16r-reasoning-steps-table: RENAR structured reasoning trace.

Covers the v32 migration, CRUD + closed-kind enforcement (CHECK + service
validation), task_show integration, FTS5 searchability, and CLI parser wiring.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from backend_migrations import run_migrations  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

KINDS = ("intent", "premise", "action", "verification")


def _make_service(db_path: str) -> ProjectService:
    return ProjectService(SQLiteBackend(db_path))


@pytest.fixture
def svc(tmp_path):
    s = _make_service(str(tmp_path / "reason.db"))
    yield s
    s.be.close()


def _seed_task(svc, slug: str = "rt1") -> None:
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", slug, "Task 1", role="developer", goal="g")


# === AC1: migration v32 applies cleanly on a v31 DB ===


def test_schema_version_at_least_32():
    # reasoning_steps was introduced at v32; later migrations only add to it.
    assert SCHEMA_VERSION >= 32


def test_migration_v32_creates_table_triggers_clean(tmp_path):
    """A v31-shaped DB migrates forward with reasoning_steps + FTS + triggers
    and no FK violations."""
    path = str(tmp_path / "v31.db")
    conn = sqlite3.connect(path)
    conn.isolation_level = None  # autocommit — run_migrations drives its own BEGIN
    conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO meta VALUES('schema_version', '31')")
    conn.execute("CREATE TABLE tasks(slug TEXT PRIMARY KEY)")  # FK target

    new_ver = run_migrations(conn, 31)
    assert new_ver >= 32

    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "reasoning_steps" in tables
    assert "fts_reasoning_steps" in tables
    trigs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert {"reasoning_steps_ai", "reasoning_steps_ad"} <= trigs
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_fresh_backend_has_reasoning_steps(svc):
    """Fresh-DB schema (not migration path) also creates the table + triggers."""
    rows = svc.be._q(
        "SELECT name FROM sqlite_master WHERE type IN ('table','trigger') "
        "AND name LIKE '%reasoning_steps%'"
    )
    names = {r["name"] for r in rows}
    assert {"reasoning_steps", "fts_reasoning_steps"} <= names
    assert {"reasoning_steps_ai", "reasoning_steps_ad"} <= names


# === AC2: CRUD + closed kinds (seq auto-increment, ordering) ===


def test_add_and_list_steps_ordered(svc):
    _seed_task(svc)
    for i, kind in enumerate(KINDS, 1):
        msg = svc.reasoning_step_add("rt1", kind, f"step {kind}")
        assert f"#{i}" in msg and kind in msg
    steps = svc.reasoning_steps("rt1")
    assert [s["seq"] for s in steps] == [1, 2, 3, 4]
    assert [s["kind"] for s in steps] == list(KINDS)


def test_seq_is_per_task(svc):
    _seed_task(svc, "rt1")
    svc.task_add("s1", "rt2", "Task 2", role="developer", goal="g")
    svc.reasoning_step_add("rt1", "intent", "a")
    svc.reasoning_step_add("rt2", "intent", "b")
    svc.reasoning_step_add("rt1", "action", "c")
    assert [s["seq"] for s in svc.reasoning_steps("rt1")] == [1, 2]
    assert [s["seq"] for s in svc.reasoning_steps("rt2")] == [1]


def test_invalid_kind_rejected_at_service(svc):
    """NEGATIVE: service validates the closed list before touching the DB."""
    _seed_task(svc)
    with pytest.raises(ServiceError, match="Invalid reasoning kind"):
        svc.reasoning_step_add("rt1", "guess", "nope")


def test_invalid_kind_rejected_at_db(svc):
    """NEGATIVE: the closed list is also a hard DB CHECK — a backend insert
    bypassing the service still cannot store a bogus kind."""
    _seed_task(svc)
    with pytest.raises(sqlite3.IntegrityError):
        svc.be.reasoning_step_add("rt1", "bogus", "x")


def test_step_on_missing_task_raises(svc):
    """NEGATIVE: reason-step on a nonexistent task is a loud error, not a no-op."""
    with pytest.raises(ServiceError):
        svc.reasoning_step_add("ghost", "intent", "x")


# === AC3: task_show integration + FTS5 searchability ===


def test_task_show_includes_reasoning_trace(svc):
    _seed_task(svc)
    svc.reasoning_step_add("rt1", "premise", "FTS5 keeps the trace searchable")
    task = svc.task_show("rt1")
    assert "reasoning_steps" in task
    assert task["reasoning_steps"][0]["kind"] == "premise"


def test_fts_search_finds_step_content(svc):
    _seed_task(svc)
    svc.reasoning_step_add("rt1", "premise", "deterministic migration is additive")
    hits = svc.be._q(
        "SELECT rs.content FROM reasoning_steps rs "
        "JOIN fts_reasoning_steps f ON rs.id = f.rowid "
        "WHERE fts_reasoning_steps MATCH ?",
        ("additive",),
    )
    assert any("additive" in h["content"] for h in hits)


# === AC3: CLI parser wiring ===


def test_cli_parser_accepts_reason_step():
    from project_parser import build_parser

    parser = build_parser()
    ns = parser.parse_args(["task", "reason-step", "rt1", "premise", "because"])
    assert ns.kind == "premise"
    assert ns.content == "because"


def test_cli_parser_rejects_bad_kind():
    from project_parser import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit):  # argparse choices rejection
        parser.parse_args(["task", "reason-step", "rt1", "nope", "x"])
