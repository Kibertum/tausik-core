"""Tests for TAUSIK ProjectService — business logic, lifecycle, cascades."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService, ServiceError


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "test.db"))
    s = ProjectService(be)
    yield s
    be.close()


def _setup_hierarchy(svc):
    """Create epic → story for task tests."""
    svc.epic_add("v1", "Version 1")
    svc.story_add("v1", "setup", "Setup")


# === Hierarchy ===


class TestHierarchy:
    def test_epic_crud(self, svc):
        msg = svc.epic_add("v1", "Version 1")
        assert "created" in msg
        epics = svc.epic_list()
        assert len(epics) == 1
        svc.epic_done("v1")
        assert svc.epic_list()[0]["status"] == "done"
        svc.epic_delete("v1")
        assert len(svc.epic_list()) == 0

    def test_epic_invalid_slug(self, svc):
        with pytest.raises(ValueError, match="Invalid slug"):
            svc.epic_add("Bad Slug!", "Title")

    def test_epic_not_found(self, svc):
        with pytest.raises(ServiceError, match="not found"):
            svc.epic_done("nope")

    def test_story_crud(self, svc):
        svc.epic_add("v1", "V1")
        msg = svc.story_add("v1", "setup", "Setup")
        assert "created" in msg
        stories = svc.story_list("v1")
        assert len(stories) == 1
        svc.story_done("setup")
        assert svc.story_list()[0]["status"] == "done"
        svc.story_delete("setup")
        assert len(svc.story_list()) == 0

    def test_story_invalid_epic(self, svc):
        with pytest.raises(ServiceError, match="not found"):
            svc.story_add("nope", "s1", "Story")


# === Task Lifecycle ===


class TestTaskLifecycle:
    def test_add_task(self, svc):
        _setup_hierarchy(svc)
        msg = svc.task_add(
            "setup", "t1", "Task 1", complexity="simple", role="developer"
        )
        assert "created" in msg
        tasks = svc.task_list()
        assert len(tasks) == 1
        assert tasks[0]["status"] == "planning"
        assert tasks[0]["score"] == 1

    def test_add_invalid_complexity(self, svc):
        _setup_hierarchy(svc)
        with pytest.raises(ServiceError, match="Invalid complexity"):
            svc.task_add("setup", "t1", "T1", complexity="huge")

    def test_add_free_text_role(self, svc):
        _setup_hierarchy(svc)
        msg = svc.task_add("setup", "t1", "T1", role="ceo")
        assert "created" in msg
        task = svc.be.task_get("t1")
        assert task["role"] == "ceo"

    def test_start_task(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        msg = svc.task_start("t1", _internal_force=True)
        assert "started" in msg
        assert "attempt #1" in msg
        task = svc.be.task_get("t1")
        assert task["status"] == "active"
        assert task["attempts"] == 1
        assert task["started_at"] is not None

    def test_start_already_active(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        msg = svc.task_start("t1", _internal_force=True)  # idempotent
        assert "already active" in msg

    def test_start_done_task(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        svc.task_done("t1")
        with pytest.raises(ServiceError, match="already done"):
            svc.task_start("t1", _internal_force=True)

    def test_done_task(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        msg = svc.task_done("t1")
        assert "completed" in msg
        task = svc.be.task_get("t1")
        assert task["status"] == "done"
        assert task["completed_at"] is not None

    def test_done_with_relevant_files(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        svc.task_done("t1", relevant_files=["src/main.py", "tests/test.py"])
        task = svc.be.task_get("t1")
        assert json.loads(task["relevant_files"]) == ["src/main.py", "tests/test.py"]

    def test_block_and_unblock(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        msg = svc.task_block("t1", "Waiting for API")
        assert "blocked" in msg
        task = svc.be.task_get("t1")
        assert task["status"] == "blocked"
        assert "Waiting for API" in task["notes"]
        msg = svc.task_unblock("t1")
        assert "unblocked" in msg
        assert svc.be.task_get("t1")["status"] == "active"

    def test_unblock_non_blocked(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        with pytest.raises(ServiceError, match="not blocked"):
            svc.task_unblock("t1")

    def test_review(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_review("t1")
        assert svc.be.task_get("t1")["status"] == "review"

    def test_update(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_update("t1", goal="New goal")
        assert svc.be.task_get("t1")["goal"] == "New goal"

    def test_delete(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_delete("t1")
        assert svc.be.task_get("t1") is None

    def test_show(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.decide("Use REST", task_slug="t1")
        detail = svc.task_show("t1")
        assert detail["slug"] == "t1"
        assert detail["story_slug"] == "setup"
        assert len(detail["decisions"]) == 1

    def test_show_not_found(self, svc):
        with pytest.raises(ServiceError, match="not found"):
            svc.task_show("nope")

    def test_task_not_found(self, svc):
        with pytest.raises(ServiceError, match="not found"):
            svc.task_start("nope", _internal_force=True)

    def test_list_filter(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1", role="developer")
        svc.task_add("setup", "t2", "T2", role="qa")
        devs = svc.task_list(role="developer")
        assert len(devs) == 1

    def test_multiple_attempts(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        svc.task_block("t1")
        svc.task_unblock("t1")
        # Re-block and simulate re-start by setting to planning
        svc.be.task_update("t1", status="planning")
        svc.task_start("t1", _internal_force=True)
        task = svc.be.task_get("t1")
        assert task["attempts"] == 2

    # --- v2.0: task_quick ---

    def test_task_quick_creates_task(self, svc):
        """task_quick creates a task with auto-generated slug, no story required."""
        msg = svc.task_quick("Fix auth bug")
        assert "created" in msg
        tasks = svc.task_list()
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Fix auth bug"
        assert tasks[0]["status"] == "planning"
        # slug should be auto-derived from title
        assert "fix-auth-bug" in tasks[0]["slug"]

    def test_task_quick_with_goal_role(self, svc):
        """task_quick accepts optional goal and role fields."""
        msg = svc.task_quick("Fix bug", goal="Fix it", role="developer")
        assert "created" in msg
        tasks = svc.task_list()
        assert len(tasks) == 1
        task = svc.be.task_get(tasks[0]["slug"])
        assert task["goal"] == "Fix it"
        assert task["role"] == "developer"

    def test_task_quick_duplicate_slug(self, svc):
        """Two task_quick calls with same title produce different slugs."""
        msg1 = svc.task_quick("Fix auth bug")
        msg2 = svc.task_quick("Fix auth bug")
        assert "created" in msg1
        assert "created" in msg2
        tasks = svc.task_list()
        assert len(tasks) == 2
        slugs = [t["slug"] for t in tasks]
        assert slugs[0] != slugs[1]

    # --- v2.0: task_next ---

    def test_task_next_returns_planning(self, svc):
        """task_next returns the highest-score planning task."""
        _setup_hierarchy(svc)
        svc.task_add("setup", "t-low", "Low", complexity="simple")  # score=1
        svc.task_add("setup", "t-high", "High", complexity="complex")  # score=8
        svc.task_add("setup", "t-mid", "Mid", complexity="medium")  # score=3
        picked = svc.task_next()
        assert picked is not None
        assert picked["slug"] == "t-high"

    def test_task_next_empty(self, svc):
        """task_next returns None when no planning tasks exist."""
        result = svc.task_next()
        assert result is None

    def test_task_next_with_agent_no_ac(self, svc):
        """task_next with agent_id claims but does NOT start if QG-0 fails."""
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "Task 1")
        picked = svc.task_next(agent_id="agent-1")
        assert picked is not None
        assert picked["slug"] == "t1"
        assert picked["claimed_by"] == "agent-1"
        assert picked["status"] == "planning"  # QG-0 blocked

    def test_task_next_with_agent_and_ac(self, svc):
        """task_next with goal+AC claims AND starts."""
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "Task 1", goal="Implement")
        svc.task_update(
            "t1", acceptance_criteria="1. Works. 2. Returns error on invalid input."
        )
        picked = svc.task_next(agent_id="agent-1")
        assert picked is not None
        assert picked["status"] == "active"
        assert picked["claimed_by"] == "agent-1"

    # --- v2.0: flat task lifecycle ---

    def test_flat_task_lifecycle(self, svc):
        """Task without story (story_slug=None) can go through full lifecycle."""
        msg = svc.task_add(None, "flat-1", "Flat task", role="developer")
        assert "created" in msg
        task = svc.be.task_get("flat-1")
        assert task is not None
        assert task["status"] == "planning"

        msg = svc.task_start("flat-1", _internal_force=True)
        assert "started" in msg
        assert svc.be.task_get("flat-1")["status"] == "active"

        msg = svc.task_done("flat-1")
        assert "completed" in msg
        assert svc.be.task_get("flat-1")["status"] == "done"


# === Plan Completion Gate ===


class TestPlanGate:
    def test_incomplete_plan_blocks_done(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        svc.task_plan("t1", ["Step 1", "Step 2", "Step 3"])
        with pytest.raises(ServiceError, match="Plan incomplete"):
            svc.task_done("t1")

    def test_complete_plan_allows_done(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        svc.task_plan("t1", ["Step 1", "Step 2"])
        svc.task_step("t1", 1)
        svc.task_step("t1", 2)
        msg = svc.task_done("t1")
        assert "completed" in msg

    def test_done_without_force(self, svc):
        """task_done no longer accepts force parameter — gates always run."""
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1", goal="Test goal")
        svc.task_update(
            "t1", acceptance_criteria="1. Works. 2. Returns error on bad input."
        )
        svc.task_start("t1")
        svc.task_plan("t1", ["Step 1", "Step 2"])
        svc.task_step("t1", 1)
        svc.task_step("t1", 2)
        svc.task_log("t1", "AC verified: 1. Works ✓ 2. Returns error on bad input ✓")
        msg = svc.task_done("t1", ac_verified=True)
        assert "completed" in msg

    def test_plan_set(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        msg = svc.task_plan("t1", ["A", "B", "C"])
        assert "3 steps" in msg
        task = svc.be.task_get("t1")
        steps = json.loads(task["plan"])
        assert len(steps) == 3
        assert not steps[0]["done"]

    def test_step_marks_done(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_plan("t1", ["A", "B"])
        msg = svc.task_step("t1", 1)
        assert "1/2" in msg
        steps = json.loads(svc.be.task_get("t1")["plan"])
        assert steps[0]["done"] is True
        assert steps[1]["done"] is False

    def test_step_out_of_range(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_plan("t1", ["A"])
        with pytest.raises(ServiceError, match="out of range"):
            svc.task_step("t1", 5)

    def test_step_no_plan(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        with pytest.raises(ServiceError, match="no plan"):
            svc.task_step("t1", 1)


# === Cascade ===


class TestCascade:
    def test_cascade_start_activates_story(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        assert svc.be.story_get("setup")["status"] == "open"
        svc.task_start("t1", _internal_force=True)
        assert svc.be.story_get("setup")["status"] == "active"

    def test_cascade_done_closes_story(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        msg = svc.task_done("t1")
        assert "auto-closed" in msg
        assert svc.be.story_get("setup")["status"] == "done"

    def test_cascade_done_closes_epic(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        msg = svc.task_done("t1")
        assert "Epic" in msg and "auto-closed" in msg
        assert svc.be.epic_get("v1")["status"] == "done"

    def test_cascade_partial_not_closed(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        svc.task_add("setup", "t2", "T2")
        svc.task_start("t1", _internal_force=True)
        msg = svc.task_done("t1")
        assert "auto-closed" not in msg
        assert svc.be.story_get("setup")["status"] != "done"

    def test_task_move(self, svc):
        _setup_hierarchy(svc)
        svc.story_add("v1", "other", "Other Story")
        svc.task_add("setup", "t1", "T1")
        msg = svc.task_move("t1", "other")
        assert "moved" in msg
        task = svc.be.task_get_full("t1")
        assert task["story_slug"] == "other"


# === Sessions ===


class TestSessions:
    def test_start_and_end(self, svc):
        msg = svc.session_start()
        assert "started" in msg
        current = svc.session_current()
        assert current is not None
        msg = svc.session_end("All done")
        assert "ended" in msg
        assert svc.session_current() is None

    def test_double_start(self, svc):
        svc.session_start()
        msg = svc.session_start()
        assert "already active" in msg

    def test_end_no_session(self, svc):
        with pytest.raises(ServiceError, match="No active session"):
            svc.session_end()

    def test_handoff(self, svc):
        svc.session_start()
        handoff = {"completed": ["t1"], "next_steps": ["t2"]}
        msg = svc.session_handoff(handoff)
        assert "saved" in msg
        result = svc.session_last_handoff()
        assert result["completed"] == ["t1"]

    def test_handoff_no_session(self, svc):
        with pytest.raises(ServiceError, match="No active session"):
            svc.session_handoff({"completed": []})

    def test_list(self, svc):
        svc.session_start()
        svc.session_end("S1")
        svc.session_start()
        svc.session_end("S2")
        sessions = svc.session_list()
        assert len(sessions) == 2


# === Knowledge ===


class TestKnowledge:
    def test_memory_crud(self, svc):
        msg = svc.memory_add("pattern", "Singleton", "Use singleton for config")
        assert "saved" in msg
        mems = svc.memory_list()
        assert len(mems) == 1
        detail = svc.memory_show(mems[0]["id"])
        assert detail["title"] == "Singleton"
        msg = svc.memory_delete(mems[0]["id"])
        assert "deleted" in msg

    def test_memory_invalid_type(self, svc):
        with pytest.raises(ServiceError, match="Invalid memory type"):
            svc.memory_add("invalid", "Title", "Content")

    def test_memory_search(self, svc):
        svc.memory_add("pattern", "Database pooling", "Always pool connections")
        results = svc.memory_search("database")
        assert len(results) >= 1

    def test_memory_not_found(self, svc):
        with pytest.raises(ServiceError, match="not found"):
            svc.memory_show(9999)

    def test_decisions(self, svc):
        msg = svc.decide("Use REST API", rationale="Simpler than GraphQL")
        assert "recorded" in msg
        decs = svc.decisions()
        assert len(decs) == 1
        assert decs[0]["rationale"] == "Simpler than GraphQL"

    def test_task_plan_empty_step_rejected(self, svc):
        """Empty plan steps should be rejected."""
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "Task")
        with pytest.raises(ServiceError, match="step .* is empty"):
            svc.task_plan("t1", ["step 1", "", "step 3"])

    def test_task_plan_whitespace_step_rejected(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "Task")
        with pytest.raises(ServiceError, match="step .* is empty"):
            svc.task_plan("t1", ["step 1", "   "])


# === Top-level Operations ===


class TestTopLevel:
    def test_status(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        status = svc.get_status()
        assert "task_counts" in status

    def test_roadmap(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1")
        roadmap = svc.get_roadmap()
        assert len(roadmap) == 1
        assert len(roadmap[0]["stories"]) == 1

    def test_search(self, svc):
        _setup_hierarchy(svc)
        svc.task_add("setup", "fix-auth", "Fix authentication")
        results = svc.search("authentication")
        assert "tasks" in results
