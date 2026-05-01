"""v1.4 Verify-First Contract — end-to-end tests.

Covers the architectural fix that decouples task closure from heavy
verification gates so MCP hosts (VS Code Claude Extension) don't hang
during `task done`. Heavy gates (pytest, tsc, cargo, phpstan, ...) live
on the new "verify" trigger; `task done` enforces a fresh `tausik verify`
green via the verify cache.

Each test class is marked @pytest.mark.verify_first so the conftest opt-out
shim (auto_verify noop) is bypassed and real enforcement runs.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError


@pytest.fixture
def svc(tmp_path):
    db = str(tmp_path / "test.db")
    be = SQLiteBackend(db)
    return ProjectService(be)


@pytest.fixture
def task_ready(svc):
    """Task with goal + AC + started, ready for `task done`."""
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "t", "Implement X", goal="Implement X", role="developer")
    svc.task_update(
        "t",
        acceptance_criteria="1. X works\n2. Returns error on invalid input",
    )
    svc.task_start("t")
    svc.task_log("t", "AC verified: 1. X works ✓ 2. Returns error on invalid input ✓")
    return svc


def _stub_verify_only(monkeypatch, *, auto_verify: bool):
    """Pretend the project has a single verify-trigger gate (pytest) and
    no other gates. Returns the service_verification module for cache helpers.
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
    monkeypatch.setattr(
        "project_config.get_gates_for_trigger", fake_get_for_trigger
    )
    import service_verification

    return service_verification


@pytest.mark.verify_first
class TestVerifyFirstEnforcement:
    """task_done refuses to close until a fresh verify run exists."""

    def test_no_verify_run_blocks(self, task_ready, monkeypatch):
        _stub_verify_only(monkeypatch, auto_verify=False)
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            with pytest.raises(ServiceError, match="no fresh `tausik verify`"):
                task_ready.task_done("t", ac_verified=True)

    def test_block_message_points_to_remediation(self, task_ready, monkeypatch):
        # Use task_done_v2 — it returns the structured report including the
        # full remediation/output without the 180-char truncation that the
        # legacy v1 ServiceError applies to the user-facing message.
        _stub_verify_only(monkeypatch, auto_verify=False)
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            report = task_ready.task_done_v2("t", ac_verified=True)
        assert not report["ok"]
        failures = report["blocking_failures"]
        assert any(
            f.get("gate") == "verify-first" and "tausik verify" in f.get("output", "")
            for f in failures
        )
        # Remediation must include the explicit two-step command.
        assert any(
            "tausik verify --task" in f.get("remediation", "") for f in failures
        )

    def test_fresh_verify_run_unblocks(self, task_ready, monkeypatch):
        sv = _stub_verify_only(monkeypatch, auto_verify=False)
        cache_command = sv._build_cache_command("verify", [])
        files_hash = sv.compute_files_hash([])
        sv.record_run(
            task_ready.be._conn,
            task_slug="t",
            scope="standard",
            command=cache_command,
            exit_code=0,
            summary="pytest=PASS",
            files_hash=files_hash,
            duration_ms=42,
        )
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            msg = task_ready.task_done("t", ac_verified=True)
        assert "completed" in msg


@pytest.mark.verify_first
class TestAutoVerifyOptOut:
    """auto_verify=true preserves the legacy "run gates inline" behavior."""

    def test_auto_verify_inline_pass(self, task_ready, monkeypatch):
        _stub_verify_only(monkeypatch, auto_verify=True)
        # When _enforce_verify_first runs verify gates inline → run_gates → PASS.
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
            msg = task_ready.task_done("t", ac_verified=True)
        assert "completed" in msg

    def test_auto_verify_inline_fail_blocks(self, task_ready, monkeypatch):
        _stub_verify_only(monkeypatch, auto_verify=True)
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
                task_ready.task_done("t", ac_verified=True)


@pytest.mark.verify_first
class TestCacheBucketSeparation:
    """Verify-First cache key includes trigger; task-done bucket and verify
    bucket must NOT cross-satisfy each other."""

    def test_task_done_bucket_does_not_satisfy_verify_first(
        self, task_ready, monkeypatch
    ):
        sv = _stub_verify_only(monkeypatch, auto_verify=False)
        # Pre-record a green run with the OLD trigger="task-done" key
        files_hash = sv.compute_files_hash([])
        sv.record_run(
            task_ready.be._conn,
            task_slug="t",
            scope="standard",
            command=sv._build_cache_command("task-done", []),
            exit_code=0,
            summary="x=PASS",
            files_hash=files_hash,
            duration_ms=10,
        )
        # _enforce_verify_first looks up by trigger="verify" cache key — the
        # task-done row above must NOT satisfy it.
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            with pytest.raises(ServiceError, match="no fresh `tausik verify`"):
                task_ready.task_done("t", ac_verified=True)


@pytest.mark.verify_first
class TestNoVerifyGatesProjectIsExempt:
    """Small projects without any verify-trigger gates must not be blocked.

    We don't want the contract to require a verify run for a project where
    there's nothing to verify (e.g. docs-only repo, plain config-as-code).
    """

    def test_empty_verify_trigger_skips_enforcement(self, task_ready, monkeypatch):
        # Patch get_gates_for_trigger to return [] for "verify" specifically.
        from project_config import get_gates_for_trigger as real

        def fake(trigger, cfg=None):
            if trigger == "verify":
                return []
            return real(trigger, cfg)

        monkeypatch.setattr(
            "project_config.load_config", lambda: {"task_done": {"auto_verify": False}}
        )
        monkeypatch.setattr("project_config.get_gates_for_trigger", fake)
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            msg = task_ready.task_done("t", ac_verified=True)
        assert "completed" in msg


@pytest.mark.verify_first
class TestStackGatesMovedToVerify:
    """Sanity: confirm the v1.4 migration in default_gates / stack JSONs."""

    @pytest.mark.parametrize(
        "gate_name",
        ["pytest", "tsc", "cargo-test", "go-test", "phpunit", "phpstan"],
    )
    def test_heavy_gate_is_on_verify_trigger(self, gate_name):
        from project_config import DEFAULT_GATES

        gate = DEFAULT_GATES.get(gate_name)
        if gate is None:
            pytest.skip(f"{gate_name} not registered (stack JSON missing in suite)")
        assert "verify" in gate.get("trigger", []), (
            f"{gate_name} must be on verify trigger after v1.4"
        )
        assert "task-done" not in gate.get("trigger", []), (
            f"{gate_name} must NOT be on task-done trigger after v1.4"
        )

    def test_filesize_stays_universal_on_task_done(self):
        from project_config import DEFAULT_GATES

        gate = DEFAULT_GATES["filesize"]
        # filesize is cheap (line counting only) — stays on task-done.
        assert "task-done" in gate["trigger"]
