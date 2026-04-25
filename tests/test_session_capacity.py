"""Tests for agent-native session capacity gate."""

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
    s = _make_service(str(tmp_path / "cap.db"))
    s.epic_add("e", "Epic")
    s.story_add("e", "s", "Story")
    yield s
    s.be.close()


def _ready_task(svc, slug: str, *, budget: int | None = None) -> None:
    svc.task_add("s", slug, "T", role="developer", goal="g", call_budget=budget)
    svc.be.task_update(slug, acceptance_criteria="Returns 400 on invalid input.")


# === Backend session_capacity_summary ===


class TestSummary:
    def test_no_active_session(self, svc):
        out = svc.be.session_capacity_summary(200)
        assert out["session"] is None
        assert out["used"] == 0
        assert out["remaining"] == 200

    def test_with_session_no_tasks(self, svc):
        svc.session_start()
        out = svc.be.session_capacity_summary(200)
        assert out["session"] is not None
        assert out["used"] == 0
        assert out["planned_active"] == 0
        assert out["remaining"] == 200

    def test_planned_active_counted(self, svc):
        svc.session_start()
        _ready_task(svc, "t1", budget=80)
        svc.task_start("t1")
        out = svc.be.session_capacity_summary(200)
        assert out["planned_active"] == 80
        assert out["remaining"] == 120


# === task_start enforcement ===


class TestEnforcement:
    def test_blocks_when_overshoot(self, svc):
        svc.session_start()
        _ready_task(svc, "big", budget=300)
        with pytest.raises(ServiceError, match="capacity"):
            svc.task_start("big")

    def test_passes_under_budget(self, svc):
        svc.session_start()
        _ready_task(svc, "small", budget=50)
        svc.task_start("small")
        assert svc.be.task_get("small")["status"] == "active"

    def test_no_block_without_session(self, svc):
        # No session_start → capacity check is no-op
        _ready_task(svc, "t", budget=300)
        svc.task_start("t")
        assert svc.be.task_get("t")["status"] == "active"

    def test_no_block_without_budget(self, svc):
        svc.session_start()
        _ready_task(svc, "no-budget")
        svc.task_start("no-budget")
        assert svc.be.task_get("no-budget")["status"] == "active"

    def test_zero_budget_no_block(self, svc):
        svc.session_start()
        _ready_task(svc, "zero", budget=0)
        svc.task_start("zero")
        assert svc.be.task_get("zero")["status"] == "active"
