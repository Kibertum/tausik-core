"""Tests for QG-2 quality gates: _run_quality_gates, _check_verification_checklist, _verify_ac."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from tausik_utils import ServiceError
from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path):
    db = str(tmp_path / "test.db")
    be = SQLiteBackend(db)
    return ProjectService(be)


@pytest.fixture
def active_task(svc):
    """Service with an active task ready for task_done tests."""
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", "t1", "Task 1", goal="Implement feature", role="developer")
    svc.task_update(
        "t1",
        acceptance_criteria="1. Feature works correctly\n2. Returns error on invalid input",
    )
    svc.task_start("t1")
    svc.task_log(
        "t1",
        "AC verified: 1. Feature works correctly ✓ 2. Returns error on invalid input ✓",
    )
    return svc


class TestRunQualityGates:
    """Test _run_quality_gates: gate_runner integration."""

    def test_gates_pass_allows_task_done(self, active_task, monkeypatch):
        mock_run = MagicMock(
            return_value=(
                True,
                [
                    {
                        "name": "pytest",
                        "passed": True,
                        "severity": "block",
                        "output": "ok",
                    }
                ],
            )
        )
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=mock_run)}):
            msg = active_task.task_done("t1", ac_verified=True)
        assert "completed" in msg

    def test_gates_fail_blocks_task_done(self, active_task, monkeypatch):
        mock_run = MagicMock(
            return_value=(
                False,
                [
                    {
                        "name": "pytest",
                        "passed": False,
                        "severity": "block",
                        "output": "1 failed",
                    }
                ],
            )
        )
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=mock_run)}):
            with pytest.raises(ServiceError, match="blocking gates failed"):
                active_task.task_done("t1", ac_verified=True)

    def test_gates_not_bypassable_via_env(self, active_task, monkeypatch):
        """TAUSIK_SKIP_GATES env var no longer bypasses gates."""
        monkeypatch.setenv("TAUSIK_SKIP_GATES", "1")
        mock_run = MagicMock(
            return_value=(
                False,
                [
                    {
                        "name": "pytest",
                        "passed": False,
                        "severity": "block",
                        "output": "1 failed",
                    }
                ],
            )
        )
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=mock_run)}):
            with pytest.raises(ServiceError, match="blocking gates failed"):
                active_task.task_done("t1", ac_verified=True)
        mock_run.assert_called_once()


class TestCheckVerificationChecklist:
    """Test _check_verification_checklist: tier-based checklist warnings."""

    def test_simple_task_no_checklist_items_returns_note(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "Fix typo", goal="Fix a typo", role="developer")
        svc.task_update(
            "t1",
            acceptance_criteria="1. Typo fixed\n2. No error on display",
            complexity="simple",
        )
        task = svc.task_show("t1")
        result = svc._check_verification_checklist("t1", task)
        assert result != ""
        assert "NOTE" in result
        assert "lightweight" in result

    def test_simple_task_with_scope_in_notes_returns_empty(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "Fix typo", goal="Fix a typo", role="developer")
        svc.task_update(
            "t1",
            acceptance_criteria="1. Typo fixed\n2. No error on display",
            complexity="simple",
        )
        svc.task_start("t1", _internal_force=True)
        svc.task_log("t1", "Checked scope — only README changed")
        task = svc.task_show("t1")
        result = svc._check_verification_checklist("t1", task)
        assert result == ""

    def test_medium_task_no_items_returns_standard_note(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "Feature", goal="Add export", role="developer")
        svc.task_update(
            "t1",
            acceptance_criteria="1. Export works\n2. Error on empty data",
            complexity="medium",
        )
        task = svc.task_show("t1")
        result = svc._check_verification_checklist("t1", task)
        assert "standard" in result


class TestVerifyACPerCriterion:
    """Test _verify_ac: per-criterion evidence warning."""

    def test_ac_verified_without_markers_returns_warning(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "Task", goal="Do stuff", role="developer")
        svc.task_update(
            "t1",
            acceptance_criteria="1. Test passes.\n2. Error handled.",
        )
        svc.task_start("t1")
        # Add "AC verified" text but WITHOUT per-criterion markers (✓)
        svc.task_log("t1", "AC verified — all good")
        task = svc.task_show("t1")
        # Should not raise but should return warning in list
        warnings = svc._verify_ac("t1", task, ac_verified=True)
        assert any("WARNING" in w for w in warnings)
        assert any("evidence markers" in w for w in warnings)

    def test_ac_verified_with_all_markers_no_warning(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "Task", goal="Do stuff", role="developer")
        svc.task_update(
            "t1",
            acceptance_criteria="1. Test passes.\n2. Error handled.",
        )
        svc.task_start("t1")
        svc.task_log("t1", "AC verified:\n1. Test passes ✓\n2. Error handled ✓")
        task = svc.task_show("t1")
        warnings = svc._verify_ac("t1", task, ac_verified=True)
        assert not any("evidence markers" in w for w in warnings)

    def test_ac_not_verified_raises_error(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "Task", goal="Do stuff", role="developer")
        svc.task_update(
            "t1",
            acceptance_criteria="1. Test passes.\n2. Error handled.",
        )
        svc.task_start("t1")
        task = svc.task_show("t1")
        with pytest.raises(ServiceError, match="QG-2"):
            svc._verify_ac("t1", task, ac_verified=False)

    def test_no_ac_skips_verify(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "Task", goal="Do stuff", role="developer")
        svc.task_start("t1", _internal_force=True)
        task = svc.task_show("t1")
        # Should not raise — no AC means no verification needed
        svc._verify_ac("t1", task, ac_verified=False)


class TestQG0SecuritySurface:
    """Test QG-0 security surface warning (SENAR Core Start Gate #5)."""

    def test_qg0_security_surface_warning(self, svc):
        """Task with security keyword in title but no security AC → warning."""
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add(
            "s1",
            "t1",
            "Implement auth flow",
            goal="Add authentication",
            role="developer",
        )
        svc.task_update(
            "t1",
            acceptance_criteria="1. User can log in\n2. Returns error on invalid credentials",
        )
        result = svc.task_start("t1")
        assert "WARNING" in result
        assert "security-relevant" in result

    def test_qg0_security_surface_no_warning_when_ac_has_security(self, svc):
        """Task with security keyword + security AC keyword → no warning."""
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add(
            "s1",
            "t1",
            "Implement auth flow",
            goal="Add authentication",
            role="developer",
        )
        svc.task_update(
            "t1",
            acceptance_criteria="1. User can log in\n2. Returns error on invalid credentials\n3. XSS protection verified",
        )
        result = svc.task_start("t1")
        assert "security-relevant" not in result


class TestQG0ScopeWarnings:
    """Test QG-0 scope and scope_exclude warnings (SENAR Core Rule 2)."""

    def test_qg0_scope_warning(self, svc):
        """Task without scope → warning."""
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add(
            "s1",
            "t1",
            "Add feature",
            goal="Implement export",
            role="developer",
        )
        svc.task_update(
            "t1",
            acceptance_criteria="1. Export works\n2. Returns error on empty data",
        )
        result = svc.task_start("t1")
        assert "WARNING" in result
        assert "no scope defined" in result

    def test_qg0_scope_exclude_warning_medium(self, svc):
        """Medium task without scope_exclude → warning."""
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add(
            "s1",
            "t1",
            "Add feature",
            goal="Implement export",
            role="developer",
        )
        svc.task_update(
            "t1",
            acceptance_criteria="1. Export works\n2. Returns error on empty data",
            complexity="medium",
            scope="scripts/export.py",
        )
        result = svc.task_start("t1")
        assert "WARNING" in result
        assert "scope_exclude" in result
