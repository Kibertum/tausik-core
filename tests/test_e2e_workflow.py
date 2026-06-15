"""E2E test of full TAUSIK workflow.

Simulates a real development session: init → epic → story → tasks →
session → work → handoff → decisions → completion → cascade close.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path, monkeypatch):
    """Force brain disabled so decide() doesn't hit the real project's enabled
    brain config (which would route writes to Notion instead of local)."""
    import brain_config

    monkeypatch.setattr(brain_config, "load_brain", lambda: {"enabled": False})
    be = SQLiteBackend(str(tmp_path / "e2e.db"))
    s = ProjectService(be)
    yield s
    be.close()


class TestFullWorkflow:
    """End-to-end simulation of a complete development cycle."""

    def test_complete_session_workflow(self, svc):
        # 1. Create project structure
        svc.epic_add("auth", "Authentication System")
        svc.story_add("auth", "login", "User Login")
        svc.story_add("auth", "register", "User Registration")

        # 2. Add tasks with different complexities
        svc.task_add(
            "login",
            "login-api",
            "Login API endpoint",
            stack="python",
            complexity="medium",
            role="developer",
            goal="Implement JWT-based login",
        )
        svc.task_add(
            "login",
            "login-ui",
            "Login UI form",
            stack="react",
            complexity="simple",
            role="developer",
        )
        svc.task_add(
            "register",
            "register-api",
            "Registration endpoint",
            stack="python",
            complexity="medium",
            role="developer",
        )

        # 3. Start a session
        msg = svc.session_start()
        assert "started" in msg

        # 4. Start first task — should auto-activate story and epic
        svc.task_start("login-api", _internal_force=True)
        assert svc.be.story_get("login")["status"] == "active"
        assert svc.be.epic_get("auth")["status"] == "active"

        # 5. Set plan for the task
        svc.task_plan(
            "login-api",
            [
                "Design JWT payload structure",
                "Implement /auth/login endpoint",
                "Add rate limiting",
            ],
        )

        # 6. Work through plan steps
        svc.task_step("login-api", 1)
        svc.task_step("login-api", 2)

        # 7. Record a decision
        svc.decide(
            "Use RS256 for JWT signing",
            task_slug="login-api",
            rationale="Asymmetric keys allow token verification without secret",
        )

        # 8. Save a memory
        svc.memory_add(
            "convention",
            "JWT Standard",
            "Use RS256 algorithm, 15min access token TTL",
            tags=["jwt", "auth"],
        )

        # 9. Block task with reason
        svc.task_block("login-api", "Waiting for key management service")
        assert svc.be.task_get("login-api")["status"] == "blocked"

        # 10. Start second task while first is blocked
        svc.task_start("login-ui", _internal_force=True)
        svc.task_done("login-ui")

        # 11. Unblock and complete first task
        svc.task_unblock("login-api")
        svc.task_step("login-api", 3)  # complete last step
        svc.task_done("login-api")

        # Login story should auto-close (both tasks done)
        assert svc.be.story_get("login")["status"] == "done"
        # Epic should NOT auto-close (register story still open)
        assert svc.be.epic_get("auth")["status"] == "active"

        # 12. Complete remaining task
        svc.task_start("register-api", _internal_force=True)
        svc.task_done("register-api")

        # Now register story AND auth epic should auto-close
        assert svc.be.story_get("register")["status"] == "done"
        assert svc.be.epic_get("auth")["status"] == "done"

        # 13. Save session handoff
        svc.session_handoff(
            {
                "completed": ["login-api", "login-ui", "register-api"],
                "decisions": ["Use RS256 for JWT"],
                "next_steps": ["Implement password reset"],
            }
        )

        # 14. End session
        svc.session_end("Auth system complete")

        # 15. Verify final state
        status = svc.get_status()
        assert status["task_counts"]["done"] == 3
        assert svc.session_current() is None

        metrics = svc.get_metrics()
        assert metrics["tasks_done"] == 3
        assert metrics["completion_pct"] == 100.0

        # 16. Verify handoff retrieval
        handoff = svc.session_last_handoff()
        assert handoff is not None
        assert "login-api" in handoff["completed"]

        # 17. Verify search works across entities
        results = svc.search("JWT")
        assert len(results.get("tasks", [])) >= 1 or len(results.get("memory", [])) >= 1
        assert len(results.get("decisions", [])) >= 1

    def test_multi_epic_workflow(self, svc):
        """Multiple epics with cross-story task movement."""
        svc.epic_add("backend", "Backend Services")
        svc.epic_add("frontend", "Frontend App")
        svc.story_add("backend", "api", "REST API")
        svc.story_add("frontend", "dashboard", "Dashboard")

        svc.task_add("api", "api-task", "API Task")
        svc.task_add("dashboard", "dash-task", "Dashboard Task")

        # Move task between stories
        svc.task_move("api-task", "dashboard")
        task = svc.be.task_get_full("api-task")
        assert task["story_slug"] == "dashboard"

        # Complete all tasks in dashboard
        svc.task_start("api-task", _internal_force=True)
        svc.task_done("api-task")
        svc.task_start("dash-task", _internal_force=True)
        svc.task_done("dash-task")

        # Dashboard story auto-closes, frontend epic auto-closes
        assert svc.be.story_get("dashboard")["status"] == "done"
        assert svc.be.epic_get("frontend")["status"] == "done"
        # Backend epic's api story has no tasks left
        assert svc.be.story_get("api")["status"] != "done"  # no tasks = not auto-closed

    def test_plan_gate_enforcement(self, svc):
        """Plan completion gate blocks premature task closure."""
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "planned-task", "Planned Task")
        svc.task_start("planned-task", _internal_force=True)
        svc.task_plan("planned-task", ["Step A", "Step B", "Step C"])

        # Cannot close with incomplete plan
        with pytest.raises(Exception, match="Plan incomplete"):
            svc.task_done("planned-task")

        # Complete 2 of 3 — still blocked
        svc.task_step("planned-task", 1)
        svc.task_step("planned-task", 2)
        with pytest.raises(Exception, match="Plan incomplete"):
            svc.task_done("planned-task")

        # Complete all — allowed
        svc.task_step("planned-task", 3)
        msg = svc.task_done("planned-task")
        assert "completed" in msg

    def test_multi_agent_workflow(self, svc):
        """Multi-agent: claim, work, unclaim."""
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "Task 1")
        svc.task_add("s1", "t2", "Task 2")

        # Agent 1 claims t1
        svc.task_claim("t1", "agent-alpha")
        assert svc.be.task_get("t1")["claimed_by"] == "agent-alpha"

        # Agent 2 claims t2
        svc.task_claim("t2", "agent-beta")

        # Team status shows both
        team = svc.team_status()
        agents = {a["agent"] for a in team}
        assert "agent-alpha" in agents
        assert "agent-beta" in agents

        # Agent 1 can't claim t2
        with pytest.raises(Exception, match="already claimed"):
            svc.task_claim("t2", "agent-alpha")

        # Unclaim and reclaim
        svc.task_unclaim("t2")
        svc.task_claim("t2", "agent-alpha")
        assert svc.be.task_get("t2")["claimed_by"] == "agent-alpha"

    def test_knowledge_integration(self, svc):
        """Memory, decisions — knowledge cycle."""
        # Memory
        svc.memory_add(
            "pattern",
            "Repository Pattern",
            "Use repository pattern for data access",
            tags=["architecture", "patterns"],
        )

        # Decisions
        svc.decide(
            "Adopt Repository Pattern",
            rationale="Decouples business logic from data access",
        )

        # Search finds everything
        results = svc.search("repository")
        total = sum(len(v) for v in results.values())
        assert total >= 2  # memory + decisions

    def test_review_workflow(self, svc):
        """Task goes through review before completion."""
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "review-task", "Review Task")
        svc.task_start("review-task", _internal_force=True)
        svc.task_review("review-task")
        assert svc.be.task_get("review-task")["status"] == "review"
        svc.task_done("review-task")
        assert svc.be.task_get("review-task")["status"] == "done"
