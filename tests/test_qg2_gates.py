"""Tests for QG-2 quality gates: _run_quality_gates, _check_verification_checklist, _verify_ac."""

from __future__ import annotations

import json
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


# verify-cache-empty-scope-hit: the task declares a scope. Leaving it empty
# used to be harmless here; it now blocks on its own (an undeclared scope
# cannot be certified by any verify run), which would mask what these tests
# are actually about.
_SCOPE = ["scripts/x.py"]


@pytest.fixture
def active_task(svc):
    """Service with an active task (with declared scope) for task_done tests."""
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", "t1", "Task 1", goal="Implement feature", role="developer")
    svc.task_update(
        "t1",
        acceptance_criteria="1. Feature works correctly\n2. Returns error on invalid input",
        relevant_files=json.dumps(_SCOPE),
    )
    svc.task_start("t1")
    svc.task_log(
        "t1",
        "AC verified: 1. Feature works correctly ✓ 2. Returns error on invalid input ✓",
    )
    return svc


@pytest.mark.verify_first
class TestRunQualityGates:
    """Test _run_quality_gates: gate_runner integration.

    v1.4 Verify-First Contract: heavy gates (pytest, tsc, ...) moved from
    `task-done` to `verify` trigger. `task_done` now refuses to close unless
    a fresh `tausik verify` run exists in `verification_runs` for the task.
    Opt-out: config.task_done.auto_verify = true (legacy CI inline path).

    These tests cover three flows:
      1. task_done WITHOUT a verify run → blocks with verify-first message.
      2. task_done WITH a fresh green verify run → closes (cache hit).
      3. task_done with auto_verify=True (legacy) → runs verify gates inline,
         pass → closes; fail → blocks.
    """

    def _stub_verify_gate(self, monkeypatch, *, auto_verify: bool = False):
        """Pretend the project has at least one verify-trigger gate.

        Uses monkeypatch on project_config.load_config + .get_gates_for_trigger
        so we never write to the real .tausik/config.json (which would leak
        between tests and into the developer's working tree).
        """
        from project_config import get_gates_for_trigger as real_for_trigger

        def fake_get_for_trigger(trigger, cfg=None):
            if trigger == "verify":
                return [
                    {
                        "name": "pytest",
                        "enabled": True,
                        "trigger": ["verify"],
                        "command": "pytest",
                        "severity": "block",
                    }
                ]
            return real_for_trigger(trigger, cfg)

        fake_cfg = {"task_done": {"auto_verify": auto_verify}}
        monkeypatch.setattr("project_config.load_config", lambda: fake_cfg)
        monkeypatch.setattr("project_config.get_gates_for_trigger", fake_get_for_trigger)
        import service_verification

        return service_verification

    def test_task_done_without_verify_blocks(self, active_task, monkeypatch):
        """v1.4 default: no fresh verify run → task_done refuses to close."""
        # Cheap gates (filesize) all green — that path must not be the issue.
        mock_run = MagicMock(return_value=(True, []))
        self._stub_verify_gate(monkeypatch)
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=mock_run)}):
            with pytest.raises(ServiceError, match="no fresh `tausik verify`"):
                active_task.task_done("t1", ac_verified=True)

    def test_task_done_with_fresh_verify_run_closes(self, active_task, monkeypatch):
        """v1.4: a green `tausik verify` cache row satisfies task_done QG-2."""
        sv = self._stub_verify_gate(monkeypatch)
        # Pre-record a fresh green verify run against the task's declared
        # scope. It used to be files=[], which no longer certifies anything.
        cache_command = sv._build_cache_command("verify", _SCOPE)
        files_hash = sv.compute_files_hash(_SCOPE)
        sv.record_run(
            active_task.be._conn,
            task_slug="t1",
            scope="standard",
            command=cache_command,
            exit_code=0,
            summary="pytest=PASS",
            files_hash=files_hash,
            duration_ms=42,
        )
        mock_run = MagicMock(return_value=(True, []))
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=mock_run)}):
            msg = active_task.task_done("t1", ac_verified=True)
        assert "completed" in msg

    def test_task_done_auto_verify_legacy_inline_pass(self, active_task, monkeypatch):
        """v1.4 opt-out: auto_verify=true runs verify gates inline. Pass → close."""
        self._stub_verify_gate(monkeypatch, auto_verify=True)
        # When _enforce_verify_first runs the verify gates inline it goes
        # through run_gates_with_cache → run_gates. Mock to PASS.
        mock_run = MagicMock(
            return_value=(
                True,
                [
                    {
                        "name": "pytest",
                        "passed": True,
                        "skipped": False,
                        "severity": "block",
                        "output": "ok",
                    }
                ],
            )
        )
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=mock_run)}):
            msg = active_task.task_done("t1", ac_verified=True)
        assert "completed" in msg

    def test_task_done_auto_verify_legacy_inline_fail(self, active_task, monkeypatch):
        """v1.4 opt-out: auto_verify=true + failing verify gate → blocks."""
        self._stub_verify_gate(monkeypatch, auto_verify=True)
        mock_run = MagicMock(
            return_value=(
                False,
                [
                    {
                        "name": "pytest",
                        "passed": False,
                        "skipped": False,
                        "severity": "block",
                        "output": "1 failed",
                    }
                ],
            )
        )
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=mock_run)}):
            with pytest.raises(ServiceError):
                active_task.task_done("t1", ac_verified=True)

    def test_gates_not_bypassable_via_env(self, active_task, monkeypatch):
        """TAUSIK_SKIP_GATES env var has never bypassed QG-2 — still doesn't.

        Verify-First flavor of the regression check: with the var set and
        no verify run, task_done still blocks (no env-based escape hatch).
        """
        monkeypatch.setenv("TAUSIK_SKIP_GATES", "1")
        self._stub_verify_gate(monkeypatch)
        mock_run = MagicMock(return_value=(True, []))
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=mock_run)}):
            with pytest.raises(ServiceError, match="QG-2"):
                active_task.task_done("t1", ac_verified=True)


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
        # v1.4: AC evidence parser also requires per-AC evidence lines; the
        # legacy "scope" keyword alone passes the lightweight checklist but
        # leaves AC coverage at 0/2 — which is now a NOTE warning. To keep
        # this test focused on the legacy keyword path, also add explicit
        # AC evidence so the new parser doesn't fire.
        svc.task_log(
            "t1",
            "Checked scope — only README changed. "
            "AC-1: ✓ verified manually. AC-2: ✓ verified manually. "
            "Domain: the corrected text reads correctly to real users.",
        )
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
            rollback_plan="git revert",
        )
        result = svc.task_start("t1")
        assert "WARNING" in result
        assert "scope_exclude" in result
