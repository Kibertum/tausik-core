"""Tests for in-session delegated-task recognition at task_start (v15-ow-hook-recognize)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from service_delegate import worker_mode_notice  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "t.db"))
    s = ProjectService(be)
    s.epic_add("v1", "V1")
    s.story_add("v1", "setup", "Setup")
    yield s
    be.close()


def _ready_task(svc, slug):
    svc.task_add("setup", slug, slug, complexity="medium", role="developer")
    svc.task_update(
        slug,
        goal="do it",
        acceptance_criteria="AC1: works. Negative: errors on bad input.",
        scope="scripts/x.py",
        scope_exclude="tests/",
        rollback_plan="git revert",
    )


class TestWorkerModeNotice:
    def test_notice_names_task_model_and_contract(self):
        msg = worker_mode_notice("feat-x", {"display": "Sonnet 4.6"})
        assert "Worker mode" in msg and "feat-x" in msg
        assert "Sonnet 4.6" in msg
        assert "summary-back" in msg and "hard-gated" in msg

    def test_notice_falls_back_when_no_model(self):
        assert "recommended" in worker_mode_notice("x", {})


class TestTaskStartRecognition:
    def test_delegated_start_shows_worker_mode_and_suppresses_banner(self, svc):
        _ready_task(svc, "feat-d")
        svc.task_delegate("feat-d")
        out = svc.task_start("feat-d")
        assert "Worker mode" in out
        assert "Model recommendation:" not in out  # orchestrator banner suppressed

    def test_non_delegated_start_unchanged(self, svc):
        _ready_task(svc, "feat-n")
        out = svc.task_start("feat-n")
        assert "Worker mode" not in out
        # Normal banner present (model banner is on by default).
        assert "Model recommendation:" in out
