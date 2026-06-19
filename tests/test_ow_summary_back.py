"""Tests for worker→orchestrator summary-back (v15-ow-summary-back)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService, ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "t.db"))
    s = ProjectService(be)
    s.epic_add("v1", "V1")
    s.story_add("v1", "setup", "Setup")
    s.task_add("setup", "feat-x", "X", complexity="medium", role="developer")
    yield s
    be.close()


class TestSummaryBack:
    def test_records_structured_summary(self, svc):
        svc.task_summary_back(
            "feat-x",
            "did the thing",
            changed="a.py,b.py",
            gates="green",
            ac_evidence="AC1 pass",
            follow_ups="none",
        )
        rec = svc.task_worker_summary("feat-x")
        assert rec is not None
        assert rec["summary"] == "did the thing"
        assert rec["gates"] == "green"
        assert rec["changed"] == "a.py,b.py"
        assert "at" in rec

    def test_summary_appended_to_task_log(self, svc):
        svc.task_summary_back("feat-x", "done", gates="green")
        task = svc.be.task_get("feat-x")
        assert "[worker-summary] done" in (task.get("notes") or "")

    def test_no_summary_returns_none(self, svc):
        assert svc.task_worker_summary("feat-x") is None

    def test_optional_fields_default_empty(self, svc):
        svc.task_summary_back("feat-x", "minimal")
        rec = svc.task_worker_summary("feat-x")
        assert rec["changed"] == "" and rec["follow_ups"] == "" and rec["gates"] == ""

    def test_unknown_task_raises(self, svc):
        with pytest.raises(ServiceError, match="not found"):
            svc.task_summary_back("nope", "x")

    def test_corrupt_summary_meta_returns_none(self, svc):
        svc.be.meta_set("worker_summary:feat-x", "not-json")
        assert svc.task_worker_summary("feat-x") is None
