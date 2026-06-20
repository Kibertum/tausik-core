"""Tests for `tausik task delegate` — orchestrator-worker delegation (v15-ow-delegate-cli)."""

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
    yield s
    be.close()


def _task(svc, slug, complexity):
    svc.task_add("setup", slug, slug, complexity=complexity, role="developer")


class TestTaskDelegate:
    def test_medium_records_delegation(self, svc):
        _task(svc, "feat-x", "medium")
        msg = svc.task_delegate("feat-x")
        assert "delegated" in msg.lower()
        rec = svc.task_delegation("feat-x")
        assert rec is not None
        assert rec["model"]  # a recommended model id was recorded
        assert "delegated_at" in rec

    def test_simple_is_delegable(self, svc):
        _task(svc, "feat-s", "simple")
        assert svc.task_delegation("feat-s") is None
        svc.task_delegate("feat-s")
        assert svc.task_delegation("feat-s") is not None

    def test_complex_refused(self, svc):
        _task(svc, "feat-c", "complex")
        with pytest.raises(ServiceError, match="complex"):
            svc.task_delegate("feat-c")
        assert svc.task_delegation("feat-c") is None  # nothing recorded

    def test_unknown_task_refused(self, svc):
        with pytest.raises(ServiceError, match="not found"):
            svc.task_delegate("nope")

    def test_done_task_refused(self, svc):
        _task(svc, "feat-d", "simple")
        svc.be.task_update("feat-d", status="done")
        with pytest.raises(ServiceError, match="done"):
            svc.task_delegate("feat-d")

    def test_idempotent_redelegate(self, svc):
        _task(svc, "feat-i", "medium")
        svc.task_delegate("feat-i")
        msg2 = svc.task_delegate("feat-i")
        assert "already delegated" in msg2.lower() and "no-op" in msg2.lower()

    def test_undelegate_clears(self, svc):
        _task(svc, "feat-u", "medium")
        svc.task_delegate("feat-u")
        assert svc.task_delegation("feat-u") is not None
        svc.task_undelegate("feat-u")
        assert svc.task_delegation("feat-u") is None

    def test_undelegate_noop_when_not_delegated(self, svc):
        _task(svc, "feat-n", "medium")
        assert "not delegated" in svc.task_undelegate("feat-n").lower()

    def test_undelegate_removes_meta_row(self, svc):
        _task(svc, "feat-r", "medium")
        svc.task_delegate("feat-r")
        svc.task_undelegate("feat-r")
        # No tombstone: the meta key is gone, not left as an empty string.
        assert svc.be.meta_get("delegation:feat-r") is None

    def test_task_delete_clears_delegation_meta(self, svc):
        _task(svc, "feat-del", "medium")
        svc.task_delegate("feat-del")
        svc.task_summary_back("feat-del", "done")
        svc.task_delete("feat-del")
        # No stale state a reused slug could inherit.
        assert svc.be.meta_get("delegation:feat-del") is None
        assert svc.be.meta_get("worker_summary:feat-del") is None

    def test_idempotent_message_no_session_shows_unknown(self, svc):
        # Fixture has no active session → parent_session is None; the no-op
        # message must read '#unknown', not the literal '#None'.
        _task(svc, "feat-q", "medium")
        svc.task_delegate("feat-q")
        msg = svc.task_delegate("feat-q")
        assert "#unknown" in msg and "#None" not in msg
