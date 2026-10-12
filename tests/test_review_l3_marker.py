"""SENAR Rule 10.15 - reviews table + ADR metric."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture()
def conn(tmp_path):
    db = tmp_path / "test.db"
    from project_backend import SQLiteBackend  # type: ignore

    be = SQLiteBackend(str(db))
    yield be
    be.close()


def _columns(c: sqlite3.Connection, table: str) -> set[str]:
    cur = c.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def test_reviews_table_exists_after_migration(conn):
    cols = _columns(conn._conn, "reviews")
    assert {
        "id",
        "task_slug",
        "run_type",
        "critical_findings",
        "warnings",
        "run_at",
        "notes",
    } <= cols


def test_review_record_and_list(conn):
    conn.task_add(story_slug=None, slug="rev-task-1", title="Some task", goal="g")
    rid = conn.review_record(
        task_slug="rev-task-1",
        run_type="L3",
        critical_findings=2,
        warnings=1,
        notes="found nullpointer in foo",
    )
    assert rid > 0
    rows = conn.review_list(task_slug="rev-task-1")
    assert len(rows) == 1
    r = rows[0]
    assert r["run_type"] == "L3"
    assert r["critical_findings"] == 2
    assert r["warnings"] == 1


def test_review_run_type_check(conn):
    conn.task_add(story_slug=None, slug="rev-task-2", title="t", goal="g")
    with pytest.raises(sqlite3.IntegrityError):
        conn.review_record(task_slug="rev-task-2", run_type="L9")


def test_review_metrics_empty(conn):
    rm = conn.review_metrics()
    assert rm == {"l3_reviewed_tasks": 0, "l3_critical_findings": 0, "adr_pct": 0.0}


def test_review_metrics_adr_calculation(conn):
    for slug in ("rev-a", "rev-b", "rev-c"):
        conn.task_add(story_slug=None, slug=slug, title="t", goal="g")
    conn.review_record(task_slug="rev-a", run_type="L1", critical_findings=10)
    conn.review_record(task_slug="rev-a", run_type="L3", critical_findings=3)
    conn.review_record(task_slug="rev-b", run_type="L3", critical_findings=1)
    conn.review_record(task_slug="rev-c", run_type="L3", critical_findings=0)
    rm = conn.review_metrics()
    assert rm["l3_reviewed_tasks"] == 3
    assert rm["l3_critical_findings"] == 4
    assert rm["adr_pct"] == round(4 / 3 * 100, 2)


def test_review_list_filter_by_type(conn):
    conn.task_add(story_slug=None, slug="rev-d", title="t", goal="g")
    conn.review_record(task_slug="rev-d", run_type="L1", critical_findings=0)
    conn.review_record(task_slug="rev-d", run_type="L3", critical_findings=2)
    l3_only = conn.review_list(task_slug="rev-d", run_type="L3")
    assert len(l3_only) == 1
    assert l3_only[0]["run_type"] == "L3"


def test_review_parser_registered():
    from project_parser import build_parser

    p = build_parser()
    args = p.parse_args(
        ["review", "record", "--task", "x", "--type", "L3", "--critical", "2"]
    )
    assert args.command == "review"
    assert args.review_cmd == "record"
    assert args.run_type == "L3"
    assert args.critical == 2
