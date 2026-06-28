"""Tests for project MCP server — _handle_tool dispatch."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project"),
)

from project_backend import SQLiteBackend
from project_service import ProjectService
from handlers import handle_tool as _handle_tool


@pytest.fixture
def svc(tmp_path):
    db_path = os.path.join(str(tmp_path), "tausik.db")
    be = SQLiteBackend(db_path)
    return ProjectService(be)


@pytest.fixture
def seeded(svc):
    """Service with epic -> story -> task hierarchy."""
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", "t1", "Task 1", complexity="simple", role="developer")
    return svc


class TestStatus:
    def test_status_compact_returns_json_with_expected_keys(self, seeded):
        result = _handle_tool(seeded, "tausik_status", {"compact": True})
        data = json.loads(result)
        assert data["tasks_total"] == 1
        assert data["tasks_done"] == 0
        assert data["tasks_planning"] == 1
        assert "session_id" in data

    # v14b-status-exploration-audit-signals: ensure /start can drop
    # tausik_explore_current and tausik_audit_check from Phase 1 batch.

    def test_status_compact_omits_signals_when_clean(self, seeded):
        data = json.loads(_handle_tool(seeded, "tausik_status", {"compact": True}))
        assert "exploration_open" not in data
        assert "exploration_id" not in data
        assert "exploration_over_limit" not in data
        assert "audit_overdue_sessions" not in data

    def test_status_compact_surfaces_active_exploration(self, seeded):
        seeded.exploration_start("research auth flow")
        data = json.loads(_handle_tool(seeded, "tausik_status", {"compact": True}))
        assert data["exploration_open"] is True
        assert isinstance(data["exploration_id"], int)

    def test_status_human_warns_on_active_exploration(self, seeded):
        seeded.exploration_start("research auth flow")
        result = _handle_tool(seeded, "tausik_status", {})
        assert "Open exploration" in result
        assert "research auth flow" in result

    def test_status_compact_emits_audit_overdue_when_threshold_met(self, seeded):
        seeded.be.session_start()
        first_id = seeded.be.session_current()["id"]
        seeded.be.meta_set("last_audit_session", str(first_id))
        seeded.be.session_start()
        seeded.be.session_start()
        seeded.be.session_start()
        data = json.loads(_handle_tool(seeded, "tausik_status", {"compact": True}))
        assert data["audit_overdue_sessions"] >= 3

    def test_status_compact_audit_absent_when_under_threshold(self, seeded):
        seeded.be.session_start()
        seeded.be.meta_set("last_audit_session", str(seeded.be.session_current()["id"]))
        data = json.loads(_handle_tool(seeded, "tausik_status", {"compact": True}))
        assert "audit_overdue_sessions" not in data

    def test_status_handles_malformed_audit_meta(self, seeded):
        seeded.be.session_start()
        seeded.be.meta_set("last_audit_session", "not-an-int")
        data = json.loads(_handle_tool(seeded, "tausik_status", {"compact": True}))
        assert "audit_overdue_sessions" not in data
        assert "tasks_total" in data


class TestTaskCRUD:
    def test_task_add(self, svc):
        svc.epic_add("e1", "Epic")
        svc.story_add("e1", "s1", "Story")
        result = _handle_tool(
            svc,
            "tausik_task_add",
            {
                "story_slug": "s1",
                "slug": "new-task",
                "title": "New Task",
            },
        )
        assert "created" in result

    def test_task_show(self, seeded):
        result = _handle_tool(seeded, "tausik_task_show", {"slug": "t1"})
        assert "Task: t1" in result
        assert "Status: planning" in result

    def test_task_start(self, seeded):
        # MCP task_start now respects QG-0 — seed has goal+AC so it passes
        seeded.task_update(
            "t1",
            goal="Test goal",
            acceptance_criteria="1. Test passes. 2. Returns error on invalid input.",
        )
        result = _handle_tool(seeded, "tausik_task_start", {"slug": "t1"})
        assert "started" in result

    def test_task_done_returns_structured_json(self, seeded):
        seeded.task_start("t1", _internal_force=True)
        result = _handle_tool(seeded, "tausik_task_done", {"slug": "t1"})
        payload = json.loads(result)
        assert payload["slug"] == "t1"
        assert payload["ok"] is True
        assert payload["gates_passed"] is True

    def test_task_block_unblock(self, seeded):
        seeded.task_start("t1", _internal_force=True)
        result = _handle_tool(seeded, "tausik_task_block", {"slug": "t1", "reason": "blocked"})
        assert "blocked" in result
        result = _handle_tool(seeded, "tausik_task_unblock", {"slug": "t1"})
        assert "unblocked" in result

    def test_task_update(self, seeded):
        result = _handle_tool(seeded, "tausik_task_update", {"slug": "t1", "goal": "New goal"})
        assert "updated" in result

    def test_task_not_found(self, svc):
        from tausik_utils import ServiceError

        with pytest.raises(ServiceError, match="not found"):
            _handle_tool(svc, "tausik_task_show", {"slug": "nope"})


class TestTaskPlan:
    def test_plan_and_step(self, seeded):
        result = _handle_tool(
            seeded,
            "tausik_task_plan",
            {
                "slug": "t1",
                "steps": ["Step 1", "Step 2"],
            },
        )
        assert "2 steps" in result

        result = _handle_tool(seeded, "tausik_task_step", {"slug": "t1", "step_num": 1})
        assert "Step 1 done" in result

    def test_show_with_plan(self, seeded):
        seeded.task_plan("t1", ["A", "B"])
        result = _handle_tool(seeded, "tausik_task_show", {"slug": "t1"})
        assert "Plan: 0/2" in result


class TestSession:
    def test_session_end(self, svc):
        svc.session_start()
        result = _handle_tool(svc, "tausik_session_end", {"summary": "Done"})
        assert "ended" in result

    def test_session_handoff(self, svc):
        svc.session_start()
        result = _handle_tool(
            svc,
            "tausik_session_handoff",
            {
                "handoff": {"done": ["task1"], "next": ["task2"]},
            },
        )
        assert "Handoff saved" in result

    def test_last_handoff_with_data(self, svc):
        svc.session_start()
        svc.session_handoff({"done": ["t1"]})
        svc.session_end()
        result = _handle_tool(svc, "tausik_session_last_handoff", {})
        assert "t1" in result


class TestHierarchy:
    def test_epic_add_list(self, svc):
        result = _handle_tool(svc, "tausik_epic_add", {"slug": "ep", "title": "Epic"})
        assert "created" in result
        result = _handle_tool(svc, "tausik_epic_list", {})
        assert "ep" in result

    def test_epic_done(self, svc):
        svc.epic_add("ep", "Epic")
        result = _handle_tool(svc, "tausik_epic_done", {"slug": "ep"})
        assert "done" in result

    def test_story_add_list(self, svc):
        svc.epic_add("ep", "Epic")
        result = _handle_tool(
            svc,
            "tausik_story_add",
            {
                "epic_slug": "ep",
                "slug": "st",
                "title": "Story",
            },
        )
        assert "created" in result
        result = _handle_tool(svc, "tausik_story_list", {})
        assert "st" in result

    def test_roadmap(self, seeded):
        result = _handle_tool(seeded, "tausik_roadmap", {})
        assert "e1" in result
        assert "s1" in result
        assert "t1" in result


class TestKnowledge:
    def test_memory_add_search(self, svc):
        result = _handle_tool(
            svc,
            "tausik_memory_add",
            {
                "type": "pattern",
                "title": "Auth pattern",
                "content": "Use JWT tokens",
            },
        )
        assert "saved" in result
        result = _handle_tool(svc, "tausik_memory_search", {"query": "auth"})
        assert "Auth pattern" in result

    def test_decide(self, svc, monkeypatch):
        # Stub brain disabled so decide() doesn't read the real project's
        # half-configured brain (would surface the v14b BLOCKED warning
        # instead of the "recorded" path this dispatch test asserts).
        import brain_config

        monkeypatch.setattr(brain_config, "load_brain", lambda cfg=None: {"enabled": False})
        result = _handle_tool(
            svc,
            "tausik_decide",
            {
                "decision": "Use SQLite",
                "rationale": "Zero deps",
            },
        )
        assert "recorded" in result


class TestMetricsAndEvents:
    def test_events(self, seeded):
        result = _handle_tool(seeded, "tausik_events", {})
        # Should have audit events from task creation
        assert "task" in result or "No events" in result

    def test_events_filter(self, seeded):
        result = _handle_tool(
            seeded,
            "tausik_events",
            {
                "entity_type": "task",
                "entity_id": "t1",
            },
        )
        assert "t1" in result or "No events" in result


# Cross-class merge of G19 + G20 (2026-05-07 audit) — empty/initial-state and
# list/search no-result responses share an identical shape and are exercised
# here as parametrized cases. Fixtures are looked up dynamically via
# request.getfixturevalue so both `svc` and `seeded` participate.
@pytest.mark.parametrize(
    "fixture_name,tool_name,args,expected_substring",
    [
        pytest.param("svc", "tausik_status", {}, "Tasks: 0/0 done", id="status_empty"),
        pytest.param("svc", "tausik_session_start", {}, "started", id="session_start"),
        pytest.param(
            "svc", "tausik_session_last_handoff", {}, "No handoff", id="last_handoff_empty"
        ),
        pytest.param("svc", "tausik_roadmap", {}, "No epics", id="roadmap_empty"),
        pytest.param("svc", "tausik_nonexistent", {}, "Unknown tool", id="unknown_tool"),
        pytest.param(
            "seeded",
            "tausik_task_list",
            {"status": "active"},
            "No tasks found",
            id="task_list_filter_status",
        ),
        pytest.param(
            "seeded", "tausik_task_update", {"slug": "t1"}, "No fields", id="task_update_no_fields"
        ),
        pytest.param(
            "svc",
            "tausik_memory_search",
            {"query": "nothing"},
            "No memories",
            id="memory_search_empty",
        ),
        pytest.param("seeded", "tausik_search", {"query": "Task"}, "tasks", id="search"),
        pytest.param("svc", "tausik_search", {"query": "nothing"}, "No results", id="search_empty"),
    ],
)
def test_handle_tool_returns_expected_substring(
    request, fixture_name, tool_name, args, expected_substring
):
    fixture = request.getfixturevalue(fixture_name)
    result = _handle_tool(fixture, tool_name, args)
    assert expected_substring in result


# Module-level: G60 cross-class merge — multi-substring assertions on seeded svc
@pytest.mark.parametrize(
    "tool_name,args,expected_substrings",
    [
        pytest.param(
            "tausik_status", {}, ("Tasks: 0/1 done", "1 planning"), id="status_with_tasks"
        ),
        pytest.param("tausik_task_list", {}, ("t1", "Task 1"), id="task_list"),
        pytest.param("tausik_metrics", {}, ("Tasks:", "Sessions:"), id="metrics"),
    ],
)
def test_handle_tool_returns_expected_substrings_seeded(
    seeded, tool_name, args, expected_substrings
):
    result = _handle_tool(seeded, tool_name, args)
    for substr in expected_substrings:
        assert substr in result
