"""CLI + MCP flags for agent-native units (--call-budget, --tier)."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


def _make_service(db_path: str) -> ProjectService:
    return ProjectService(SQLiteBackend(db_path))


@pytest.fixture
def svc(tmp_path):
    s = _make_service(str(tmp_path / "cli.db"))
    s.epic_add("e1", "Epic 1")
    s.story_add("e1", "s1", "Story 1")
    yield s
    s.be.close()


# === service.task_add with budget/tier ===


class TestServiceAdd:
    def test_budget_only_derives_tier(self, svc):
        msg = svc.task_add("s1", "t1", "Task 1", role="developer", call_budget=30)
        task = svc.be.task_get("t1")
        assert task["call_budget"] == 30
        assert task["tier"] == "moderate"
        assert "overridden" not in msg

    def test_tier_only_no_budget(self, svc):
        svc.task_add("s1", "t2", "Task 2", role="developer", tier="light")
        task = svc.be.task_get("t2")
        assert task["call_budget"] is None
        assert task["tier"] == "light"

    def test_both_budget_overrides_tier(self, svc):
        msg = svc.task_add(
            "s1", "t3", "Task 3", role="developer", call_budget=200, tier="trivial"
        )
        task = svc.be.task_get("t3")
        # call_budget=200 → tier='deep' (>150 threshold), tier='trivial' ignored
        assert task["call_budget"] == 200
        assert task["tier"] == "deep"
        assert "overridden" in msg.lower()

    def test_neither_leaves_nulls(self, svc):
        svc.task_add("s1", "t4", "Task 4", role="developer")
        task = svc.be.task_get("t4")
        assert task["call_budget"] is None
        assert task["tier"] is None

    def test_negative_budget_rejected(self, svc):
        from tausik_utils import ServiceError

        with pytest.raises(ServiceError, match="call_budget"):
            svc.task_add("s1", "t5", "Task 5", role="developer", call_budget=-1)

    def test_invalid_tier_rejected(self, svc):
        from tausik_utils import ServiceError

        with pytest.raises(ServiceError, match="tier"):
            svc.task_add("s1", "t6", "Task 6", role="developer", tier="bogus")


# === service.task_update with budget/tier ===


class TestServiceUpdate:
    def test_update_budget_derives_tier(self, svc):
        svc.task_add("s1", "t1", "Task 1", role="developer")
        svc.task_update("t1", call_budget=70)
        task = svc.be.task_get("t1")
        assert task["call_budget"] == 70
        assert task["tier"] == "substantial"

    def test_update_tier_directly(self, svc):
        svc.task_add("s1", "t1", "Task 1", role="developer")
        svc.task_update("t1", tier="deep")
        task = svc.be.task_get("t1")
        assert task["tier"] == "deep"

    def test_update_explicit_tier_overridden_by_budget(self, svc):
        """MED-6 review fix: task_update aligns with task_add — budget wins."""
        svc.task_add("s1", "t1", "Task 1", role="developer")
        result = svc.task_update("t1", call_budget=5, tier="deep")
        task = svc.be.task_get("t1")
        assert task["call_budget"] == 5
        # Explicit 'deep' is dropped; auto-derived 'trivial' wins (budget=5)
        assert task["tier"] == "trivial"
        assert "overridden" in result.lower()

    def test_update_negative_budget_rejected(self, svc):
        from tausik_utils import ServiceError

        svc.task_add("s1", "t1", "Task 1", role="developer")
        with pytest.raises(ServiceError, match="call_budget"):
            svc.task_update("t1", call_budget=-7)

    def test_update_invalid_tier_rejected(self, svc):
        from tausik_utils import ServiceError

        svc.task_add("s1", "t1", "Task 1", role="developer")
        with pytest.raises(ServiceError, match="tier"):
            svc.task_update("t1", tier="huge")


# === MCP handler dispatch ===


class TestMcpHandlers:
    def test_handler_passes_budget_through(self, svc):
        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
            ),
        )
        from handlers import _do_task_add, _do_task_update

        msg = _do_task_add(
            svc,
            {
                "story_slug": "s1",
                "slug": "tm1",
                "title": "MCP add",
                "role": "developer",
                "call_budget": 12,
            },
        )
        assert "tm1" in msg
        task = svc.be.task_get("tm1")
        assert task["call_budget"] == 12
        assert task["tier"] == "light"

        _do_task_update(svc, {"slug": "tm1", "call_budget": 80})
        task = svc.be.task_get("tm1")
        assert task["call_budget"] == 80
        assert task["tier"] == "substantial"

    def test_handler_invalid_tier_rejected(self, svc):
        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
            ),
        )
        from handlers import _do_task_add
        from tausik_utils import ServiceError

        with pytest.raises(ServiceError):
            _do_task_add(
                svc,
                {
                    "story_slug": "s1",
                    "slug": "tm-bad",
                    "title": "Bad tier",
                    "role": "developer",
                    "tier": "ginormous",
                },
            )


# === CLI argparse smoke test ===


CLI = [sys.executable, os.path.join("scripts", "project.py")]
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def cli_env(tmp_path):
    """Return env that points TAUSIK at an isolated DB inside tmp_path."""
    return {
        **os.environ,
        "TAUSIK_DB": str(tmp_path / "cli.db"),
        "TAUSIK_PROJECT_DIR": str(tmp_path),
    }


def _run_cli(*args, env=None):
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=env,
        timeout=15,
    )


class TestCliParser:
    def test_help_lists_call_budget(self):
        result = _run_cli("task", "add", "--help")
        assert result.returncode == 0
        assert "--call-budget" in result.stdout
        assert "--tier" in result.stdout

    def test_help_update_lists_call_budget(self):
        result = _run_cli("task", "update", "--help")
        assert result.returncode == 0
        assert "--call-budget" in result.stdout
        assert "--tier" in result.stdout

    def test_invalid_tier_argparse_rejects(self):
        # No DB needed — argparse fails before any DB call.
        result = _run_cli("task", "add", "Foo", "--tier", "huge")
        assert result.returncode != 0
        assert "tier" in (result.stderr + result.stdout).lower()

    def test_non_integer_budget_argparse_rejects(self):
        result = _run_cli("task", "add", "Foo", "--call-budget", "abc")
        assert result.returncode != 0
