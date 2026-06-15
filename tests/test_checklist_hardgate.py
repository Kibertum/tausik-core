"""Tests for the SENAR Rule 5 checklist hard gate (v15s-rule5-checklist-hardgate).

Pure checklist_hard_block decisions by planning tier + the task_done integration
(hard block for substantial/deep, escalating nudge for lower tiers, config
opt-out downgrades to a warning).
"""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from gate_ac_check import checklist_hard_block, checklist_missing  # noqa: E402


def _task(tier=None, notes=""):
    return {"tier": tier, "notes": notes, "relevant_files": "[]", "acceptance_criteria": ""}


class TestChecklistHardBlock:
    def test_substantial_without_checklist_blocks(self):
        block, msg = checklist_hard_block(_task("substantial", notes="just did stuff"))
        assert block is True
        assert "Rule 5" in msg and "substantial" in msg
        assert "checklist_hard=false" in msg  # opt-out documented

    def test_deep_without_checklist_blocks(self):
        block, _ = checklist_hard_block(_task("deep", notes=""))
        assert block is True

    def test_substantial_with_checklist_passes(self):
        # A checklist keyword present in notes -> not missing -> no block.
        block, msg = checklist_hard_block(_task("substantial", notes="scope clean, no secret leak"))
        assert block is False and msg == ""

    def test_lower_tier_never_hard_blocks(self):
        for tier in ("trivial", "light", "moderate", None):
            block, msg = checklist_hard_block(_task(tier, notes=""))
            assert block is False and msg == ""

    def test_checklist_missing_detects_keyword(self):
        assert checklist_missing(_task(notes="nothing relevant here")) is True
        assert checklist_missing(_task(notes="verified scope and secret scan")) is False


class TestTaskDoneIntegration:
    def _make(self, tmp_path, monkeypatch, tier):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TAUSIK_QUIET", "1")
        svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
        svc.task_add(None, "t-cl", "Checklist task")
        svc.task_update(
            "t-cl",
            goal="g",
            acceptance_criteria="1. ok\n2. errors on bad input",
            scope="x.py",
            tier=tier,
        )
        svc.task_start("t-cl")
        return svc

    def test_substantial_blocked_without_checklist(self, tmp_path, monkeypatch):
        from tausik_utils import ServiceError

        svc = self._make(tmp_path, monkeypatch, "substantial")
        try:
            with pytest.raises(ServiceError, match="Rule 5"):
                svc.task_done("t-cl", None, True, True, evidence="AC verified: 1. OK 2. OK")
            assert svc.be.task_get("t-cl")["status"] == "active"  # not closed
        finally:
            svc.be.close()

    def test_substantial_passes_with_checklist(self, tmp_path, monkeypatch):
        svc = self._make(tmp_path, monkeypatch, "substantial")
        try:
            result = svc.task_done(
                "t-cl",
                None,
                True,
                True,
                evidence="AC verified: 1. OK 2. OK. Checklist: scope clean, no secret, tests pass.",
            )
            assert "completed" in result
            assert svc.be.task_get("t-cl")["status"] == "done"
        finally:
            svc.be.close()

    def test_lower_tier_not_blocked(self, tmp_path, monkeypatch):
        svc = self._make(tmp_path, monkeypatch, "light")
        try:
            # No checklist, but light tier -> nudge, not a block.
            result = svc.task_done("t-cl", None, True, True, evidence="AC verified: 1. OK 2. OK")
            assert "completed" in result
            assert svc.be.task_get("t-cl")["status"] == "done"
        finally:
            svc.be.close()

    def test_opt_out_downgrades_to_warning(self, tmp_path, monkeypatch):
        import service_task_done

        monkeypatch.setattr(service_task_done, "_checklist_hard_enabled", lambda: False)
        svc = self._make(tmp_path, monkeypatch, "deep")
        try:
            result = svc.task_done("t-cl", None, True, True, evidence="AC verified: 1. OK 2. OK")
            assert "completed" in result  # not blocked
            assert "checklist_hard=false" in result
        finally:
            svc.be.close()
