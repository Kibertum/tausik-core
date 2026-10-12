"""r14-task-done-v1-msg: task_done v1 must aggregate ALL blocking failures
into the ServiceError message, not just the first one.

Pre-1.4 the agent saw only failure #1, fixed it, retried, then saw failure
#2, etc. Wasted round-trips. Now every blocker is surfaced at once.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from service_task import _format_task_done_failures
from tausik_utils import ServiceError


class TestFormatTaskDoneFailures:
    def test_no_failures_falls_back_to_default(self):
        report = {"ok": False, "blocking_failures": []}
        assert _format_task_done_failures(report) == "task_done failed"

    def test_single_failure_returns_unwrapped_message(self):
        """Backward compat: one failure → same wording as v1.3."""
        report = {
            "ok": False,
            "blocking_failures": [{"stage": "ac", "message": "QG-2: AC unverified"}],
        }
        assert _format_task_done_failures(report) == "QG-2: AC unverified"

    def test_multiple_failures_aggregate(self):
        report = {
            "ok": False,
            "blocking_failures": [
                {"stage": "ac", "message": "QG-2: AC unverified"},
                {
                    "stage": "gates",
                    "gate": "filesize",
                    "message": "QG-2 Implementation Gate failed: filesize — too big",
                },
                {
                    "stage": "gates",
                    "gate": "verify-first",
                    "message": "QG-2 Implementation Gate failed: verify-first — no run",
                },
            ],
        }
        msg = _format_task_done_failures(report)
        assert "multiple failures" in msg
        assert "AC unverified" in msg
        assert "filesize" in msg
        assert "verify-first" in msg
        # Each failure should be on its own line, numbered.
        assert "[1]" in msg and "[2]" in msg and "[3]" in msg

    def test_per_failure_message_cap(self):
        long = "x" * 500
        report = {
            "ok": False,
            "blocking_failures": [
                {"stage": "ac", "message": long},
                {"stage": "gates", "gate": "g", "message": long},
            ],
        }
        msg = _format_task_done_failures(report)
        # Each per-failure body capped at 180 chars; not the whole message.
        for line in msg.splitlines()[1:]:  # skip the header
            # Strip the "  [N] stage=... gate=... : " prefix
            after_colon = line.split(":", 2)[-1]
            assert len(after_colon.strip()) <= 180

    def test_missing_message_handled_gracefully(self):
        report = {
            "ok": False,
            "blocking_failures": [
                {"stage": "ac"},  # no 'message' key
                {"stage": "gates", "message": "real one"},
            ],
        }
        msg = _format_task_done_failures(report)
        # Should not crash, both entries appear (empty body for #1).
        assert "[1]" in msg and "[2]" in msg
        assert "real one" in msg


class TestTaskDoneIntegration:
    """Integration: ServiceError raised by task_done v1 carries the new format."""

    @pytest.fixture
    def svc(self, tmp_path):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        be = SQLiteBackend(str(tmp_path / "t.db"))
        return ProjectService(be)

    def test_v1_error_contains_aggregated_message(self, svc, monkeypatch):
        # Build a task that will produce two blocking failures from
        # _task_done_report: ac_verified=False (fails AC stage) plus a
        # synthetic second one we inject by patching _task_done_report.
        svc.epic_add("e", "E")
        svc.story_add("e", "s", "S")
        svc.task_add("s", "t", "Task", goal="g", role="developer")
        svc.task_update(
            "t",
            acceptance_criteria="1. Works\n2. Returns error on bad input",
        )
        svc.task_start("t")

        def fake_report(self, slug, **_kw):
            return {
                "ok": False,
                "blocking_failures": [
                    {"stage": "ac", "message": "QG-2 first"},
                    {"stage": "gates", "gate": "filesize", "message": "QG-2 second"},
                ],
            }

        monkeypatch.setattr(
            "project_service.ProjectService._task_done_report", fake_report
        )
        with pytest.raises(ServiceError) as exc:
            svc.task_done("t")
        s = str(exc.value)
        assert "QG-2 first" in s
        assert "QG-2 second" in s
        assert "multiple failures" in s
