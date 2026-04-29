"""Tests for agent-units-recording: event-count query, hook, and task_done wiring."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "hooks", "task_call_counter.py"
)


def _make_service(db_path: str) -> ProjectService:
    return ProjectService(SQLiteBackend(db_path))


@pytest.fixture
def svc(tmp_path):
    s = _make_service(str(tmp_path / "rec.db"))
    yield s
    s.be.close()


def _seed_active_task(
    svc,
    slug: str = "t1",
    goal: str = "g",
    ac: str = "Done. Returns 400 on invalid input.",
) -> None:
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", slug, "Task 1", role="developer", goal=goal)
    svc.be.task_update(slug, acceptance_criteria=ac)
    svc.task_start(slug)
    # Pre-log AC verification so QG-2 doesn't block task_done in tests.
    svc.task_log(slug, "AC verified: 1. covered ✓")


# === Backend query: task_event_count_in_window ===


class TestEventCountWindow:
    def test_zero_when_no_started_at(self, svc):
        _seed_active_task(svc)
        # Wipe started_at to simulate edge case
        svc.be.task_update("t1", started_at=None)
        assert svc.be.task_event_count_in_window("t1") == 0

    def test_counts_events_in_window(self, svc):
        _seed_active_task(svc)
        # task_start already produced status_changed event(s); add a few more
        svc.be.event_add("task", "t1", "log_added", "irrelevant")
        svc.be.event_add("task", "t1", "log_added", "irrelevant 2")
        cnt = svc.be.task_event_count_in_window("t1")
        # at minimum: created + status_changed (planning→active) + 2 manual = 4
        assert cnt >= 4

    def test_excludes_other_tasks(self, svc):
        _seed_active_task(svc, slug="t1")
        svc.be.event_add("task", "other", "noise", "")
        cnt = svc.be.task_event_count_in_window("t1")
        # 'other' must not be counted under t1
        assert cnt >= 1
        assert all(
            e["entity_id"] == "t1"
            for e in svc.be.events_list(entity_type="task", entity_id="t1")
        )

    def test_returns_zero_for_unknown_task(self, svc):
        assert svc.be.task_event_count_in_window("does-not-exist") == 0


# === task_done wires call_actual ===


class TestTaskDoneRecordsActual:
    def test_writes_call_actual_from_events(self, svc):
        _seed_active_task(svc)
        svc.task_done("t1", ac_verified=True, no_knowledge=True)
        task = svc.be.task_get("t1")
        assert task["call_actual"] is not None
        assert task["call_actual"] >= 1

    def test_includes_meta_counter(self, svc):
        _seed_active_task(svc)
        # Simulate hook having incremented the per-task counter 5×.
        svc.be.meta_set("tool_calls:t1", "5")
        svc.task_done("t1", ac_verified=True, no_knowledge=True)
        task = svc.be.task_get("t1")
        assert task["call_actual"] >= 5  # events + 5 from meta

    def test_clears_meta_counter_after_done(self, svc):
        _seed_active_task(svc)
        svc.be.meta_set("tool_calls:t1", "12")
        svc.task_done("t1", ac_verified=True, no_knowledge=True)
        assert svc.be.meta_get("tool_calls:t1") == "0"

    def test_corrupt_meta_value_is_tolerated(self, svc):
        _seed_active_task(svc)
        svc.be.meta_set("tool_calls:t1", "garbage")
        # Must not raise — fallback to 0
        svc.task_done("t1", ac_verified=True, no_knowledge=True)
        task = svc.be.task_get("t1")
        assert task["call_actual"] is not None

    def test_budget_warning_when_exceeded(self, svc):
        _seed_active_task(svc)
        svc.be.task_set_call_budget("t1", 10)  # tier='trivial'
        svc.be.meta_set("tool_calls:t1", "100")  # 100 ≫ 1.5×10
        result = svc.task_done("t1", ac_verified=True, no_knowledge=True)
        assert "WARNING" in result
        assert "call_actual" in result
        assert "call_budget" in result

    def test_no_warning_within_budget(self, svc):
        _seed_active_task(svc)
        svc.be.task_set_call_budget("t1", 100)
        svc.be.meta_set("tool_calls:t1", "5")
        result = svc.task_done("t1", ac_verified=True, no_knowledge=True)
        assert "WARNING: call_actual" not in result

    def test_no_warning_without_budget(self, svc):
        _seed_active_task(svc)
        svc.be.meta_set("tool_calls:t1", "9999")
        result = svc.task_done("t1", ac_verified=True, no_knowledge=True)
        # Without a budget, recording happens but no overrun warning.
        assert "WARNING: call_actual" not in result


# === PostToolUse hook ===


def _run_hook(cwd: str, payload: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, HOOK_PATH],
        input=json.dumps(payload or {}),
        capture_output=True,
        text=True,
        cwd=cwd,
        env={**os.environ, "CLAUDE_PROJECT_DIR": cwd},
        timeout=10,
    )


class TestCallCounterHook:
    def test_noop_without_db(self, tmp_path):
        # Project dir has no .tausik/tausik.db
        result = _run_hook(str(tmp_path))
        assert result.returncode == 0

    def test_noop_when_no_active_task(self, tmp_path, svc):
        # svc has its own DB inside tmp_path/rec.db, but at <tmp>/.tausik/tausik.db
        # we need the canonical layout. Create separate isolated project:
        proj = tmp_path / "proj"
        os.makedirs(proj / ".tausik")
        s = _make_service(str(proj / ".tausik" / "tausik.db"))
        s.be.close()
        result = _run_hook(str(proj))
        assert result.returncode == 0
        # No active task → meta should not have any tool_calls keys
        s2 = _make_service(str(proj / ".tausik" / "tausik.db"))
        try:
            assert s2.be.meta_get("tool_calls:none") is None
        finally:
            s2.be.close()

    def test_increments_for_single_active(self, tmp_path):
        proj = tmp_path / "proj2"
        os.makedirs(proj / ".tausik")
        db_path = str(proj / ".tausik" / "tausik.db")
        s = _make_service(db_path)
        try:
            s.epic_add("e", "Epic")
            s.story_add("e", "st", "Story")
            s.task_add("st", "t1", "Task", role="developer", goal="g")
            s.be.task_update("t1", acceptance_criteria="Done. Fails on invalid input.")
            s.task_start("t1")
        finally:
            s.be.close()

        result = _run_hook(str(proj))
        assert result.returncode == 0
        s2 = _make_service(db_path)
        try:
            assert s2.be.meta_get("tool_calls:t1") == "1"
        finally:
            s2.be.close()

        # Second invocation increments to 2
        _run_hook(str(proj))
        s3 = _make_service(db_path)
        try:
            assert s3.be.meta_get("tool_calls:t1") == "2"
        finally:
            s3.be.close()

    def test_skipped_when_env_set(self, tmp_path):
        proj = tmp_path / "proj3"
        os.makedirs(proj / ".tausik")
        s = _make_service(str(proj / ".tausik" / "tausik.db"))
        try:
            s.epic_add("e", "Epic")
            s.story_add("e", "st", "Story")
            s.task_add("st", "t1", "Task", role="developer", goal="g")
            s.be.task_update("t1", acceptance_criteria="Done. Fails on invalid input.")
            s.task_start("t1")
        finally:
            s.be.close()

        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(proj), "TAUSIK_SKIP_HOOKS": "1"}
        subprocess.run(
            [sys.executable, HOOK_PATH],
            input="{}",
            capture_output=True,
            text=True,
            cwd=str(proj),
            env=env,
            timeout=5,
        )
        s2 = _make_service(str(proj / ".tausik" / "tausik.db"))
        try:
            assert s2.be.meta_get("tool_calls:t1") is None
        finally:
            s2.be.close()
