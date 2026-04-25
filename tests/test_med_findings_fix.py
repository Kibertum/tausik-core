"""Tests for v1.4.1 MED review findings 6, 7, 9, 11."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError


def _make_service(db_path: str) -> ProjectService:
    return ProjectService(SQLiteBackend(db_path))


@pytest.fixture
def svc(tmp_path):
    s = _make_service(str(tmp_path / "med.db"))
    s.epic_add("e", "Epic")
    s.story_add("e", "s", "Story")
    yield s
    s.be.close()


def _ready_task(svc, slug: str, *, budget: int | None = None) -> None:
    svc.task_add("s", slug, "T", role="developer", goal="g", call_budget=budget)
    svc.be.task_update(slug, acceptance_criteria="Returns 400 on invalid input.")


# === MED-6: task_update budget wins over explicit tier ===


class TestUpdateBudgetWins:
    def test_budget_overrides_explicit_tier(self, svc):
        svc.task_add("s", "t1", "Task", role="developer")
        result = svc.task_update("t1", call_budget=200, tier="trivial")
        task = svc.be.task_get("t1")
        assert task["call_budget"] == 200
        # 200 → 'deep' auto; explicit 'trivial' is dropped (MED-6)
        assert task["tier"] == "deep"
        assert "overridden" in result.lower()

    def test_tier_only_still_works(self, svc):
        svc.task_add("s", "t1", "Task", role="developer")
        svc.task_update("t1", tier="moderate")
        assert svc.be.task_get("t1")["tier"] == "moderate"

    def test_budget_only_auto_derives(self, svc):
        svc.task_add("s", "t1", "Task", role="developer")
        svc.task_update("t1", call_budget=15)
        task = svc.be.task_get("t1")
        assert task["call_budget"] == 15
        assert task["tier"] == "light"

    def test_other_fields_still_apply_with_budget(self, svc):
        svc.task_add("s", "t1", "Task", role="developer")
        svc.task_update("t1", call_budget=15, tier="deep", notes="hello")
        task = svc.be.task_get("t1")
        assert task["notes"] == "hello"
        assert task["tier"] == "light"


# === MED-7: --force flag bypasses session capacity gate ===


class TestForceFlag:
    def test_force_bypasses_capacity_overshoot(self, svc):
        svc.session_start()
        _ready_task(svc, "big", budget=300)
        with pytest.raises(ServiceError, match="capacity"):
            svc.task_start("big")
        result = svc.task_start("big", force=True)
        assert "FORCED start" in result
        assert svc.be.task_get("big")["status"] == "active"

    def test_force_logs_audit_event(self, svc):
        svc.session_start()
        _ready_task(svc, "big", budget=300)
        svc.task_start("big", force=True)
        events = svc.be.events_list(entity_type="task", entity_id="big")
        actions = [e["action"] for e in events]
        assert "capacity_force_start" in actions

    def test_force_appends_audit_to_notes(self, svc):
        svc.session_start()
        _ready_task(svc, "big", budget=300)
        svc.task_start("big", force=True)
        notes = svc.be.task_get("big")["notes"] or ""
        assert "FORCED start" in notes

    def test_force_without_overshoot_no_audit(self, svc):
        svc.session_start()
        _ready_task(svc, "ok", budget=10)
        result = svc.task_start("ok", force=True)
        assert "FORCED" not in result
        events = [
            e
            for e in svc.be.events_list(entity_type="task", entity_id="ok")
            if e["action"] == "capacity_force_start"
        ]
        assert events == []

    def test_force_default_is_false(self, svc):
        svc.session_start()
        _ready_task(svc, "big", budget=300)
        with pytest.raises(ServiceError):
            svc.task_start("big")


# === MED-9: julianday compare for event-count window ===


class TestEventCountTimestampSafety:
    def test_microsecond_timestamps_handled(self, svc):
        _ready_task(svc, "t1", budget=10)
        svc.task_start("t1")
        svc.be._ex(
            "INSERT INTO events(entity_type, entity_id, action, created_at) "
            "VALUES('task', 't1', 'note', '2099-01-01T12:00:00.123456+00:00')"
        )
        cnt = svc.be.task_event_count_in_window("t1")
        assert isinstance(cnt, int)
        assert cnt >= 1

    def test_window_excludes_after_completed(self, svc):
        _ready_task(svc, "t1", budget=10)
        svc.task_start("t1")
        svc.be.task_update("t1", completed_at="2020-01-01T00:00:00Z", status="done")
        svc.be._ex(
            "INSERT INTO events(entity_type, entity_id, action, created_at) "
            "VALUES('task', 't1', 'late', '2099-01-01T00:00:00Z')"
        )
        cnt = svc.be.task_event_count_in_window("t1")
        all_count = len(svc.be.events_list(entity_type="task", entity_id="t1"))
        assert cnt < all_count


# === MED-11: docs ===


class TestOverflowDocs:
    def test_claude_md_mentions_overflow_cap(self):
        path = os.path.join(os.path.dirname(__file__), "..", "CLAUDE.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert ">400" in text or "> 400" in text
        assert "deep" in text.lower()

    def test_tools_py_mentions_overflow(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "agents",
            "claude",
            "mcp",
            "project",
            "tools.py",
        )
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert ">400" in text
        assert "deep" in text.lower()

    def test_mcp_mirrors_in_sync(self):
        base = os.path.join(os.path.dirname(__file__), "..")
        with open(
            os.path.join(base, "agents", "claude", "mcp", "project", "tools.py"),
            encoding="utf-8",
        ) as f:
            claude = f.read()
        with open(
            os.path.join(base, "agents", "cursor", "mcp", "project", "tools.py"),
            encoding="utf-8",
        ) as f:
            cursor = f.read()
        with open(
            os.path.join(base, ".claude", "mcp", "project", "tools.py"),
            encoding="utf-8",
        ) as f:
            installed = f.read()
        assert claude == cursor
        assert claude == installed
