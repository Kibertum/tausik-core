"""Tests for project MCP server — _handle_tool dispatch."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"),
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
    def test_status_empty(self, svc):
        result = _handle_tool(svc, "tausik_status", {})
        assert "Tasks: 0/0 done" in result

    def test_status_with_tasks(self, seeded):
        result = _handle_tool(seeded, "tausik_status", {})
        assert "Tasks: 0/1 done" in result
        assert "1 planning" in result


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

    def test_task_list(self, seeded):
        result = _handle_tool(seeded, "tausik_task_list", {})
        assert "t1" in result
        assert "Task 1" in result

    def test_task_list_filter_status(self, seeded):
        result = _handle_tool(seeded, "tausik_task_list", {"status": "active"})
        assert "No tasks found" in result

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

    def test_task_done(self, seeded):
        seeded.task_start("t1", _internal_force=True)
        result = _handle_tool(seeded, "tausik_task_done", {"slug": "t1"})
        assert "completed" in result

    def test_task_block_unblock(self, seeded):
        seeded.task_start("t1", _internal_force=True)
        result = _handle_tool(
            seeded, "tausik_task_block", {"slug": "t1", "reason": "blocked"}
        )
        assert "blocked" in result
        result = _handle_tool(seeded, "tausik_task_unblock", {"slug": "t1"})
        assert "unblocked" in result

    def test_task_update(self, seeded):
        result = _handle_tool(
            seeded, "tausik_task_update", {"slug": "t1", "goal": "New goal"}
        )
        assert "updated" in result

    def test_task_update_no_fields(self, seeded):
        result = _handle_tool(seeded, "tausik_task_update", {"slug": "t1"})
        assert "No fields" in result

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
    def test_session_start(self, svc):
        result = _handle_tool(svc, "tausik_session_start", {})
        assert "started" in result

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

    def test_last_handoff_empty(self, svc):
        result = _handle_tool(svc, "tausik_session_last_handoff", {})
        assert "No handoff" in result

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

    def test_roadmap_empty(self, svc):
        result = _handle_tool(svc, "tausik_roadmap", {})
        assert "No epics" in result


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

    def test_memory_search_empty(self, svc):
        result = _handle_tool(svc, "tausik_memory_search", {"query": "nothing"})
        assert "No memories" in result

    def test_decide(self, svc):
        result = _handle_tool(
            svc,
            "tausik_decide",
            {
                "decision": "Use SQLite",
                "rationale": "Zero deps",
            },
        )
        assert "recorded" in result

    def test_search(self, seeded):
        result = _handle_tool(seeded, "tausik_search", {"query": "Task"})
        assert "tasks" in result

    def test_search_empty(self, svc):
        result = _handle_tool(svc, "tausik_search", {"query": "nothing"})
        assert "No results" in result


class TestMetricsAndEvents:
    def test_metrics(self, seeded):
        result = _handle_tool(seeded, "tausik_metrics", {})
        assert "Tasks:" in result
        assert "Sessions:" in result

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

    def test_unknown_tool(self, svc):
        result = _handle_tool(svc, "tausik_nonexistent", {})
        assert "Unknown tool" in result
