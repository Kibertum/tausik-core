"""Tests for v14c-token-budget-task — cost/token budget per task.

Covers:
  * v27 schema migration adds 4 nullable columns
  * validate_task_add_inputs rejects negative cost/token budgets
  * task_add / task_update wire --cost-budget / --token-budget
  * usage_events_cost_rollup_for_task happy path + zero-event
  * record_cost_actual writes back + 1.5× warning
  * task_done flow surfaces the cost warning
  * task_cost_budget_check.py PostToolUse hook:
      - silent no-op variants (env skip, no DB, no active task,
        multi active, no budget set)
      - WARN at 1.5×, BLOCKER at 2.0×
      - throttle file dedupes within 30s
      - never raises on malformed stdin
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from typing import Any

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

HOOK_PATH = os.path.join(_SCRIPTS, "hooks", "task_cost_budget_check.py")


def _make_service(db_path: str) -> ProjectService:
    return ProjectService(SQLiteBackend(db_path))


@pytest.fixture
def svc(tmp_path):
    s = _make_service(str(tmp_path / "cb.db"))
    yield s
    s.be.close()


def _seed_active_task(
    s: ProjectService,
    slug: str = "t1",
    *,
    cost_budget_usd: float | None = None,
    token_budget: int | None = None,
) -> None:
    s.epic_add("e1", "Epic 1")
    s.story_add("e1", "s1", "Story 1")
    s.task_add(
        "s1",
        slug,
        "Task 1",
        role="developer",
        goal="g",
        cost_budget_usd=cost_budget_usd,
        token_budget=token_budget,
    )
    s.be.task_update(slug, acceptance_criteria="Done. Returns 400 on invalid input.")
    s.task_start(slug)
    # Pin started_at to a known anchor so injected usage_events with later
    # timestamps fall inside the rollup window deterministically.
    s.be.task_update(slug, started_at="2026-05-07T12:00:00Z")
    s.task_log(slug, "AC verified: 1. covered ✓")


# === Schema migration ===


class TestSchemaV27:
    def test_four_columns_added_nullable(self, tmp_path):
        path = str(tmp_path / "schema.db")
        be = SQLiteBackend(path)
        try:
            rows = be._q(  # type: ignore[attr-defined]
                "SELECT name, [notnull] AS notnull_flag FROM pragma_table_info('tasks')"
            )
        finally:
            be.close()
        cols = {row["name"]: row for row in rows}
        for name in (
            "cost_budget_usd",
            "cost_actual_usd",
            "token_budget",
            "tokens_actual",
        ):
            assert name in cols, f"Column {name!r} missing from tasks"
            assert cols[name]["notnull_flag"] == 0, (
                f"Column {name!r} should be nullable (notnull=0)"
            )


# === Validation ===


class TestValidation:
    def test_negative_cost_budget_rejected(self, svc):
        with pytest.raises(ServiceError, match="cost_budget_usd"):
            svc.task_add(None, "x", "X", goal="g", cost_budget_usd=-1.0)

    def test_negative_token_budget_rejected(self, svc):
        with pytest.raises(ServiceError, match="token_budget"):
            svc.task_add(None, "x", "X", goal="g", token_budget=-5)

    def test_zero_cost_budget_accepted(self, svc):
        # Zero is a degenerate but legal "no spend allowed" budget.
        svc.task_add(None, "x", "X", goal="g", cost_budget_usd=0.0)
        assert svc.be.task_get("x")["cost_budget_usd"] == 0.0

    def test_positive_cost_budget_persisted(self, svc):
        svc.task_add(None, "x", "X", goal="g", cost_budget_usd=2.50)
        assert svc.be.task_get("x")["cost_budget_usd"] == pytest.approx(2.50)

    def test_positive_token_budget_persisted(self, svc):
        svc.task_add(None, "x", "X", goal="g", token_budget=10000)
        assert svc.be.task_get("x")["token_budget"] == 10000

    def test_task_update_sets_cost_budget(self, svc):
        svc.task_add(None, "x", "X", goal="g")
        svc.task_update("x", cost_budget_usd=5.0)
        assert svc.be.task_get("x")["cost_budget_usd"] == pytest.approx(5.0)

    def test_task_update_rejects_negative_cost_budget(self, svc):
        svc.task_add(None, "x", "X", goal="g")
        with pytest.raises(ServiceError, match="cost_budget_usd"):
            svc.task_update("x", cost_budget_usd=-0.5)

    def test_task_update_rejects_negative_token_budget(self, svc):
        svc.task_add(None, "x", "X", goal="g")
        with pytest.raises(ServiceError, match="token_budget"):
            svc.task_update("x", token_budget=-1)


# === rollup_for_task helper ===


def _insert_usage_event(
    be: SQLiteBackend,
    *,
    session_id: int,
    slug: str,
    tokens_total: int,
    cost_usd: float,
    when: str,
) -> None:
    be.usage_event_append(
        session_id,
        slug,
        tokens_input=0,
        tokens_output=tokens_total,
        tokens_total=tokens_total,
        cost_usd=cost_usd,
        tool_calls=1,
        model_id="claude-opus-4-7",
        source="posttool",
        recorded_at=when,
    )


class TestRollupForTask:
    def test_zero_events_returns_zeros(self, svc):
        roll = svc.be.usage_events_cost_rollup_for_task("nope")
        assert roll["task_slug"] == "nope"
        assert roll["event_count"] == 0
        assert roll["tokens_total"] == 0
        assert roll["cost_usd"] == 0.0

    def test_sums_across_events_for_slug(self, svc):
        _seed_active_task(svc)
        sid = svc.be.session_start()
        _insert_usage_event(
            svc.be,
            session_id=sid,
            slug="t1",
            tokens_total=1000,
            cost_usd=0.50,
            when="2026-05-07T12:00:00Z",
        )
        _insert_usage_event(
            svc.be,
            session_id=sid,
            slug="t1",
            tokens_total=2000,
            cost_usd=1.25,
            when="2026-05-07T12:01:00Z",
        )
        roll = svc.be.usage_events_cost_rollup_for_task("t1")
        assert roll["event_count"] == 2
        assert roll["tokens_total"] == 3000
        assert roll["cost_usd"] == pytest.approx(1.75)

    def test_excludes_other_slug(self, svc):
        _seed_active_task(svc, slug="t1")
        # Sister task in a fresh story (single-active-task contract preserved
        # by leaving status=planning); FK requires the slug to exist.
        svc.story_add("e1", "s2", "Story 2")
        svc.task_add("s2", "other", "Other task", role="developer", goal="g")
        sid = svc.be.session_start()
        _insert_usage_event(
            svc.be,
            session_id=sid,
            slug="other",
            tokens_total=999,
            cost_usd=9.99,
            when="2026-05-07T12:00:00Z",
        )
        roll = svc.be.usage_events_cost_rollup_for_task("t1")
        assert roll["cost_usd"] == 0.0

    def test_since_filter_excludes_pre_window(self, svc):
        _seed_active_task(svc)
        sid = svc.be.session_start()
        _insert_usage_event(
            svc.be,
            session_id=sid,
            slug="t1",
            tokens_total=100,
            cost_usd=0.10,
            when="2026-05-07T11:00:00Z",
        )
        _insert_usage_event(
            svc.be,
            session_id=sid,
            slug="t1",
            tokens_total=200,
            cost_usd=0.20,
            when="2026-05-07T13:00:00Z",
        )
        roll = svc.be.usage_events_cost_rollup_for_task("t1", since="2026-05-07T12:00:00Z")
        assert roll["event_count"] == 1
        assert roll["cost_usd"] == pytest.approx(0.20)


# === record_cost_actual + task_done flow ===


class TestRecordCostActual:
    def test_writes_actuals_to_task_row(self, svc):
        _seed_active_task(svc, cost_budget_usd=1.00, token_budget=10000)
        sid = svc.be.session_start()
        _insert_usage_event(
            svc.be,
            session_id=sid,
            slug="t1",
            tokens_total=500,
            cost_usd=0.25,
            when="2026-05-07T13:00:00Z",
        )
        svc.task_done("t1", ac_verified=True, no_knowledge=True)
        task = svc.be.task_get("t1")
        # cost_actual_usd: at least our injected event; tokens too.
        assert task["cost_actual_usd"] is not None
        assert float(task["cost_actual_usd"]) >= 0.25
        assert task["tokens_actual"] is not None
        assert int(task["tokens_actual"]) >= 500

    def test_warning_when_cost_actual_above_1_5x_budget(self, svc):
        _seed_active_task(svc, cost_budget_usd=0.10)
        sid = svc.be.session_start()
        _insert_usage_event(
            svc.be,
            session_id=sid,
            slug="t1",
            tokens_total=0,
            cost_usd=1.00,  # 10× budget
            when="2026-05-07T13:00:00Z",
        )
        msg = svc.task_done("t1", ac_verified=True, no_knowledge=True)
        assert "cost_actual_usd" in msg
        assert "cost_budget_usd" in msg

    def test_warning_when_tokens_actual_above_1_5x_budget(self, svc):
        _seed_active_task(svc, token_budget=100)
        sid = svc.be.session_start()
        _insert_usage_event(
            svc.be,
            session_id=sid,
            slug="t1",
            tokens_total=500,  # 5× budget
            cost_usd=0.0,
            when="2026-05-07T13:00:00Z",
        )
        msg = svc.task_done("t1", ac_verified=True, no_knowledge=True)
        assert "tokens_actual" in msg
        assert "token_budget" in msg

    def test_no_warning_within_budget(self, svc):
        _seed_active_task(svc, cost_budget_usd=10.0)
        sid = svc.be.session_start()
        _insert_usage_event(
            svc.be,
            session_id=sid,
            slug="t1",
            tokens_total=100,
            cost_usd=0.10,
            when="2026-05-07T13:00:00Z",
        )
        msg = svc.task_done("t1", ac_verified=True, no_knowledge=True)
        assert "cost_actual_usd" not in msg
        assert "WARNING: cost" not in msg

    def test_no_warning_without_budget(self, svc):
        _seed_active_task(svc)
        sid = svc.be.session_start()
        _insert_usage_event(
            svc.be,
            session_id=sid,
            slug="t1",
            tokens_total=999999,
            cost_usd=999.0,
            when="2026-05-07T13:00:00Z",
        )
        msg = svc.task_done("t1", ac_verified=True, no_knowledge=True)
        assert "cost_actual_usd" not in msg


# === Hook: subprocess integration ===


def _run_hook(
    cwd: str,
    payload: dict[str, Any] | None = None,
    *,
    skip: bool = False,
) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": cwd}
    if skip:
        env["TAUSIK_SKIP_HOOKS"] = "1"
    return subprocess.run(
        [sys.executable, HOOK_PATH],
        input=json.dumps(payload or {}),
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        timeout=10,
    )


def _new_proj(tmp_path) -> tuple[str, str]:
    """Create a fresh project layout, return (proj_dir, db_path)."""
    proj = tmp_path / "proj"
    os.makedirs(proj / ".tausik")
    db_path = str(proj / ".tausik" / "tausik.db")
    return str(proj), db_path


class TestHookSilentNoOp:
    def test_noop_when_env_skip(self, tmp_path):
        proj, _ = _new_proj(tmp_path)
        result = _run_hook(proj, skip=True)
        assert result.returncode == 0
        assert result.stderr == ""

    def test_noop_when_no_db(self, tmp_path):
        # Project dir has no .tausik/tausik.db at all
        result = _run_hook(str(tmp_path))
        assert result.returncode == 0
        assert "TAUSIK cost-budget" not in result.stderr

    def test_noop_when_no_active_task(self, tmp_path):
        proj, db_path = _new_proj(tmp_path)
        s = _make_service(db_path)
        s.be.close()  # bare DB, no tasks
        result = _run_hook(proj)
        assert result.returncode == 0
        assert "TAUSIK cost-budget" not in result.stderr

    def test_noop_when_multiple_active_tasks(self, tmp_path):
        proj, db_path = _new_proj(tmp_path)
        s = _make_service(db_path)
        try:
            _seed_active_task(s, slug="t1", cost_budget_usd=0.10)
            # Manually insert a 2nd active row to bypass session capacity check.
            s.be._ex(  # type: ignore[attr-defined]
                "INSERT INTO tasks(slug,title,status,goal,acceptance_criteria,"
                "cost_budget_usd,started_at,attempts,created_at,updated_at) "
                "VALUES('t2','T2','active','g','Done.',0.10,'2026-05-07T13:00:00Z',1,"
                "'2026-05-07T13:00:00Z','2026-05-07T13:00:00Z')"
            )
        finally:
            s.be.close()
        result = _run_hook(proj)
        assert result.returncode == 0
        assert "TAUSIK cost-budget" not in result.stderr

    def test_noop_when_active_task_has_no_budget(self, tmp_path):
        proj, db_path = _new_proj(tmp_path)
        s = _make_service(db_path)
        try:
            _seed_active_task(s)  # no budgets
        finally:
            s.be.close()
        result = _run_hook(proj)
        assert result.returncode == 0
        assert "TAUSIK cost-budget" not in result.stderr

    def test_noop_within_budget(self, tmp_path):
        proj, db_path = _new_proj(tmp_path)
        s = _make_service(db_path)
        try:
            _seed_active_task(s, cost_budget_usd=10.0)
            sid = s.be.session_start()
            _insert_usage_event(
                s.be,
                session_id=sid,
                slug="t1",
                tokens_total=100,
                cost_usd=0.10,  # 1% of budget
                when="2026-05-07T13:30:00Z",
            )
        finally:
            s.be.close()
        result = _run_hook(proj)
        assert result.returncode == 0
        assert "TAUSIK cost-budget" not in result.stderr

    def test_never_raises_on_malformed_stdin(self, tmp_path):
        proj, db_path = _new_proj(tmp_path)
        s = _make_service(db_path)
        s.be.close()
        # Send literal garbage instead of JSON
        result = subprocess.run(
            [sys.executable, HOOK_PATH],
            input="this is not json {",
            capture_output=True,
            text=True,
            cwd=proj,
            env={**os.environ, "CLAUDE_PROJECT_DIR": proj},
            timeout=10,
        )
        assert result.returncode == 0


class TestHookWarnAndBlocker:
    def test_warn_at_1_5x_cost(self, tmp_path):
        proj, db_path = _new_proj(tmp_path)
        s = _make_service(db_path)
        try:
            _seed_active_task(s, cost_budget_usd=0.10)
            sid = s.be.session_start()
            _insert_usage_event(
                s.be,
                session_id=sid,
                slug="t1",
                tokens_total=0,
                cost_usd=0.16,  # 1.6× budget
                when="2026-05-07T13:30:00Z",
            )
        finally:
            s.be.close()
        result = _run_hook(proj)
        assert result.returncode == 0
        assert "[TAUSIK cost-budget WARN]" in result.stderr
        assert "t1" in result.stderr
        assert "BLOCKER" not in result.stderr

    def test_blocker_at_2x_cost(self, tmp_path):
        proj, db_path = _new_proj(tmp_path)
        s = _make_service(db_path)
        try:
            _seed_active_task(s, cost_budget_usd=0.10)
            sid = s.be.session_start()
            _insert_usage_event(
                s.be,
                session_id=sid,
                slug="t1",
                tokens_total=0,
                cost_usd=0.25,  # 2.5× budget
                when="2026-05-07T13:30:00Z",
            )
        finally:
            s.be.close()
        result = _run_hook(proj)
        assert result.returncode == 0
        assert "[TAUSIK cost-budget BLOCKER]" in result.stderr
        assert "2× hard cap reached" in result.stderr

    def test_warn_at_1_5x_tokens(self, tmp_path):
        proj, db_path = _new_proj(tmp_path)
        s = _make_service(db_path)
        try:
            _seed_active_task(s, token_budget=100)
            sid = s.be.session_start()
            _insert_usage_event(
                s.be,
                session_id=sid,
                slug="t1",
                tokens_total=170,  # 1.7× budget
                cost_usd=0.0,
                when="2026-05-07T13:30:00Z",
            )
        finally:
            s.be.close()
        result = _run_hook(proj)
        assert result.returncode == 0
        assert "[TAUSIK cost-budget WARN]" in result.stderr
        assert "tokens" in result.stderr

    def test_blocker_at_2x_tokens(self, tmp_path):
        proj, db_path = _new_proj(tmp_path)
        s = _make_service(db_path)
        try:
            _seed_active_task(s, token_budget=100)
            sid = s.be.session_start()
            _insert_usage_event(
                s.be,
                session_id=sid,
                slug="t1",
                tokens_total=250,  # 2.5× budget
                cost_usd=0.0,
                when="2026-05-07T13:30:00Z",
            )
        finally:
            s.be.close()
        result = _run_hook(proj)
        assert result.returncode == 0
        assert "[TAUSIK cost-budget BLOCKER]" in result.stderr


class TestHookThrottle:
    def test_dedupes_within_window(self, tmp_path):
        proj, db_path = _new_proj(tmp_path)
        s = _make_service(db_path)
        try:
            _seed_active_task(s, cost_budget_usd=0.10)
            sid = s.be.session_start()
            _insert_usage_event(
                s.be,
                session_id=sid,
                slug="t1",
                tokens_total=0,
                cost_usd=0.20,  # 2× budget — BLOCKER
                when="2026-05-07T13:30:00Z",
            )
        finally:
            s.be.close()
        # First run emits BLOCKER
        first = _run_hook(proj)
        assert "[TAUSIK cost-budget BLOCKER]" in first.stderr
        # Second run within the 30s window must be silent
        second = _run_hook(proj)
        assert "[TAUSIK cost-budget" not in second.stderr

    def test_throttle_file_is_atomic_write(self, tmp_path):
        """No `.cost_budget_throttle.json.tmp` leftover after emission."""
        proj, db_path = _new_proj(tmp_path)
        s = _make_service(db_path)
        try:
            _seed_active_task(s, cost_budget_usd=0.10)
            sid = s.be.session_start()
            _insert_usage_event(
                s.be,
                session_id=sid,
                slug="t1",
                tokens_total=0,
                cost_usd=0.20,
                when="2026-05-07T13:30:00Z",
            )
        finally:
            s.be.close()
        _run_hook(proj)
        leftover = os.path.join(proj, ".tausik", ".cost_budget_throttle.json.tmp")
        assert not os.path.exists(leftover)
        final = os.path.join(proj, ".tausik", ".cost_budget_throttle.json")
        assert os.path.exists(final)
        with open(final, encoding="utf-8") as f:
            data = json.load(f)
        # Throttle key is "<slug>:<level>"
        assert any(k.startswith("t1:") for k in data)


# === Hook unit-level: classify, format, throttle eligibility ===


class TestHookUnits:
    def test_classify_blocker_at_2x(self):
        sys.path.insert(0, os.path.join(_SCRIPTS, "hooks"))
        import importlib

        mod = importlib.import_module("task_cost_budget_check")
        assert mod._classify_level(2.0, 1.0) == "BLOCKER"
        assert mod._classify_level(2.5, 1.0) == "BLOCKER"

    def test_classify_warn_between_1_5x_and_2x(self):
        sys.path.insert(0, os.path.join(_SCRIPTS, "hooks"))
        import importlib

        mod = importlib.import_module("task_cost_budget_check")
        assert mod._classify_level(1.5, 1.0) == "WARN"
        assert mod._classify_level(1.9, 1.0) == "WARN"

    def test_classify_none_below_1_5x(self):
        sys.path.insert(0, os.path.join(_SCRIPTS, "hooks"))
        import importlib

        mod = importlib.import_module("task_cost_budget_check")
        assert mod._classify_level(0.0, 1.0) is None
        assert mod._classify_level(1.4999, 1.0) is None

    def test_classify_zero_budget_returns_none(self):
        sys.path.insert(0, os.path.join(_SCRIPTS, "hooks"))
        import importlib

        mod = importlib.import_module("task_cost_budget_check")
        assert mod._classify_level(100.0, 0.0) is None

    def test_should_emit_window(self, tmp_path):
        sys.path.insert(0, os.path.join(_SCRIPTS, "hooks"))
        import importlib

        mod = importlib.import_module("task_cost_budget_check")
        throttle: dict[str, float] = {}
        # First emission allowed
        assert mod._should_emit(throttle, "t1", "WARN", now=1000.0)
        throttle["t1:WARN"] = 1000.0
        # Within 30s window blocked
        assert not mod._should_emit(throttle, "t1", "WARN", now=1015.0)
        # Past 30s window allowed again
        assert mod._should_emit(throttle, "t1", "WARN", now=1031.0)

    def test_format_msg_for_cost_blocker(self):
        sys.path.insert(0, os.path.join(_SCRIPTS, "hooks"))
        import importlib

        mod = importlib.import_module("task_cost_budget_check")
        msg = mod._format_msg(
            "task-x",
            "BLOCKER",
            cost_actual=0.50,
            cost_budget=0.20,
            tokens_actual=0,
            token_budget=None,
            trigger="cost",
        )
        assert "BLOCKER" in msg
        assert "task-x" in msg
        assert "$0.5000" in msg
        assert "$0.2000" in msg


# === SQLiteBackend connection cleanup helper ===


def teardown_module(_module):
    # Best-effort cleanup of any sqlite3 connections that escaped fixtures.
    sqlite3.enable_callback_tracebacks(False)
