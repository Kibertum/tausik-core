"""blocked-is-a-status-without-a-question-to-unblock-it — the v77 contract.

A block without a QUESTION to the owner and a checkable UNBLOCK CRITERION is
a task abandoned with a note to self; the live corpus carried that shape
since 1.8. The tests here hold the three new invariants:

1. `task block` refuses to write a block without both fields, and the
   question may not restate the title (a ritual question is no question).
2. `tausik status` surfaces the open questions as the FIRST block on both
   channels — not a "blocked: N" count — and pre-v77 rows render as DEBT.
3. `task unblock` is never silent: the caller states which criterion is met,
   and WHO unblocked is recorded in the row.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import backend_migrations as bm  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from service_task import BLOCK_QUESTION_UNSET  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402
from test_migrations import V1_SCHEMA  # noqa: E402

_V77 = 77


@pytest.fixture
def svc(tmp_path, monkeypatch):
    import state_triggers

    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: False)
    (tmp_path / ".tausik").mkdir()
    service = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    service.epic_add("e1", "Epic")
    service.story_add("e1", "s1", "Story")
    service.task_add("s1", "t1", "Decide the export format", complexity="simple", role="developer")
    service.task_add("s1", "t2", "Second task", complexity="simple", role="developer")
    yield service
    service.be.close()


# --- AC-1: both fields are required, and the refusal names them -------------


def test_block_without_question_names_both_required_flags(svc):
    svc.task_start("t1", _internal_force=True)
    with pytest.raises(ServiceError) as err:
        svc.task_block("t1", unblock_criteria="format decided")
    assert "--question" in str(err.value)
    assert (
        "--unblock-when" not in str(err.value).split("missing")[0]
    )  # only the missing one is named missing
    assert svc.be.task_get("t1")["status"] == "active"


def test_block_without_criterion_refuses_even_with_a_good_question(svc):
    svc.task_start("t1", _internal_force=True)
    with pytest.raises(ServiceError) as err:
        svc.task_block("t1", question="owner: JSON or YAML for the export contract?")
    assert "--unblock-when" in str(err.value)
    assert svc.be.task_get("t1")["status"] == "active"


# --- AC-1/AC-4: the happy path stores fields the status can render ----------


def test_block_persists_question_and_criteria_and_status_leads_with_them(svc):
    svc.task_start("t1", _internal_force=True)
    svc.task_block(
        "t1",
        "waiting on the owner",
        question="owner: JSON or YAML for the export contract?",
        unblock_criteria="format decision recorded in the SPEC",
    )
    row = svc.be.task_get("t1")
    assert row["status"] == "blocked"
    assert row["blocked_question"] == "owner: JSON or YAML for the export contract?"
    assert row["unblock_criteria"] == "format decision recorded in the SPEC"

    from status_view import build_status_view, status_primary_lines

    view = build_status_view(svc, tausik_dir=None, include_rich=False)
    questions = view["data"]["open_questions"]
    assert [q["slug"] for q in questions] == ["t1"]
    assert questions[0]["no_question_recorded"] is False

    lines = status_primary_lines(view)
    assert lines[0].startswith("Open question to the owner"), lines[0]
    assert "owner: JSON or YAML" in lines[1]
    assert "unblock when: format decision recorded" in " ".join(lines)


def test_reblocking_an_already_blocked_task_updates_the_fields(svc):
    """The migration path for live debt: the question already lived in prose."""
    svc.task_start("t1", _internal_force=True)
    svc.task_block(
        "t1", question="owner: keep the CSV exporter?", unblock_criteria="exporter decision"
    )
    svc.task_block(
        "t1",
        question="owner: keep the CSV exporter or retire it for Parquet?",
        unblock_criteria="exporter decision recorded in ADR",
    )
    row = svc.be.task_get("t1")
    assert row["status"] == "blocked"
    assert "Parquet" in row["blocked_question"]
    assert "ADR" in row["unblock_criteria"]


# --- AC-6 negative: a question that restates the title is a ritual ----------


@pytest.mark.parametrize(
    ("title", "question", "restates"),
    [
        ("Decide the export format", "Decide the export format", True),
        ("Decide the export format", "decide  THE export format!", True),
        ("Decide the export format", "Blocking this: decide the export format now", True),
        # A real question may SHARE the subject with the title — that is not
        # a restatement; containment of the FULL normalized title is.
        ("Decide the export format", "owner: which format wins, JSON or YAML?", False),
    ],
)
def test_question_may_not_restate_the_title(svc, monkeypatch, title, question, restates):
    monkeypatch.setattr(
        svc.be, "task_get", lambda slug: {"slug": slug, "title": title, "status": "active"}
    )
    monkeypatch.setattr(svc.be, "task_update", lambda slug, **f: 1)
    monkeypatch.setattr(svc.be, "task_append_notes", lambda slug, note: 1)
    if restates:
        with pytest.raises(ServiceError) as err:
            svc.task_block("t1", question=question, unblock_criteria="c")
        assert "restates the task title" in str(err.value)
    else:
        assert "blocked" in svc.task_block("t1", question=question, unblock_criteria="c")


# --- AC-3: silent unblocking is forbidden; WHO unblocked is recorded --------


def test_unblock_without_a_statement_is_refused_and_quotes_the_criterion(svc):
    svc.task_start("t1", _internal_force=True)
    svc.task_block(
        "t1", question="owner: which format?", unblock_criteria="SPEC records the format"
    )
    with pytest.raises(ServiceError) as err:
        svc.task_unblock("t1")
    assert "Silent unblocking is forbidden" in str(err.value)
    assert "SPEC records the format" in str(err.value)
    assert svc.be.task_get("t1")["status"] == "blocked"


def test_unblock_records_who_stated_the_criterion_met(svc):
    svc.task_start("t1", _internal_force=True)
    svc.task_block(
        "t1", question="owner: which format?", unblock_criteria="SPEC records the format"
    )
    svc.task_unblock("t1", criterion_met="SPEC v2 §3 records JSON", by="architect@review")
    row = svc.be.task_get("t1")
    assert row["status"] == "active"
    assert row["unblocked_by"] == "architect@review"
    assert row["unblocked_at"]
    assert "architect@review" in (row["notes"] or "")


# --- AC-5 negative: the migration backfills old blocks as DEBT, not norm ----


def _db_at_v76(tmp_path, name="v76.db"):
    conn = sqlite3.connect(str(tmp_path / name))
    conn.isolation_level = None
    conn.executescript(V1_SCHEMA)
    removed = {v: bm.MIGRATIONS.pop(v) for v in sorted(bm.MIGRATIONS) if v >= _V77}
    try:
        assert bm.run_migrations(conn, 1) == _V77 - 1
    finally:
        bm.MIGRATIONS.update(removed)
    return conn


def test_migration_v77_backfills_blocked_rows_with_the_debt_marker(tmp_path):
    conn = _db_at_v76(tmp_path)
    try:
        conn.execute(
            "INSERT INTO tasks(slug, title, status, created_at, updated_at) "
            "VALUES ('legacy-block','Old block','blocked','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO tasks(slug, title, status, created_at, updated_at) "
            "VALUES ('legacy-active','Old active','active','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')"
        )
        bm.run_migrations(conn, _V77 - 1)
        blocked = conn.execute(
            "SELECT blocked_question, unblock_criteria FROM tasks WHERE slug='legacy-block'"
        ).fetchone()
        assert tuple(blocked) == (BLOCK_QUESTION_UNSET, BLOCK_QUESTION_UNSET)
        # NULL means "never blocked" — an active row must not carry the marker.
        active = conn.execute(
            "SELECT blocked_question, unblock_criteria FROM tasks WHERE slug='legacy-active'"
        ).fetchone()
        assert tuple(active) == (None, None)
    finally:
        conn.close()


def test_status_renders_a_marker_question_as_debt_not_as_an_answer(svc):
    svc.task_start("t1", _internal_force=True)
    svc.be.task_update(
        "t1",
        status="blocked",
        blocked_question=BLOCK_QUESTION_UNSET,
        unblock_criteria=BLOCK_QUESTION_UNSET,
    )
    from status_view import build_status_view, status_primary_lines

    view = build_status_view(svc, tausik_dir=None, include_rich=False)
    entry = view["data"]["open_questions"][0]
    assert entry["no_question_recorded"] is True
    assert entry["question"] is None
    debt_lines = [ln for ln in status_primary_lines(view) if "DEBT" in ln]
    assert debt_lines and "re-block" in debt_lines[0]
