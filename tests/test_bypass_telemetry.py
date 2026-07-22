"""l26-bypass-telemetry: every way to weaken supervision leaves a countable trace.

The release-1.8 thesis is that the framework must be able to say how many times
it was switched off — a silent bypass makes any claim of enforcement
unfalsifiable. These tests pin, per vector, that the bypass emits exactly one
`events` row (entity_type='supervision', action='bypass_*'), that the metric
aggregates them, that the audit hash-chain survives raw inserts, and that the
telemetry itself is fail-open (a broken sink never blocks the supervisor).
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
_HOOKS = os.path.join(_SCRIPTS, "hooks")
for _p in (_SCRIPTS, _HOOKS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


def _make_project(tmp_path) -> tuple[str, str, SQLiteBackend]:
    """A throwaway project: `.tausik/tausik.db` on a real schema."""
    tdir = tmp_path / ".tausik"
    tdir.mkdir()
    db = str(tdir / "tausik.db")
    be = SQLiteBackend(db)  # constructs schema
    return str(tmp_path), str(tdir), be


def _supervision_rows(db: str) -> list[tuple[str, str, str]]:
    conn = sqlite3.connect(db)
    try:
        return conn.execute(
            "SELECT entity_id, action, details FROM events "
            "WHERE entity_type='supervision' ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


# --- The shared hook emitter -------------------------------------------------


class TestEmitHelper:
    def test_writes_one_supervision_row(self, tmp_path):
        project_dir, _tdir, be = _make_project(tmp_path)
        from _common import emit_supervision_bypass

        emit_supervision_bypass(project_dir, "skip_hooks", "task_gate", "detail")
        rows = _supervision_rows(_db_of(be))
        assert rows == [("task_gate", "bypass_skip_hooks", "detail")]

    def test_no_db_is_silent(self, tmp_path):
        from _common import emit_supervision_bypass

        # No .tausik/tausik.db under this dir — must be a no-op, not a crash.
        emit_supervision_bypass(str(tmp_path), "skip_hooks", "task_gate")

    def test_broken_db_never_raises(self, tmp_path):
        from _common import emit_supervision_bypass

        tdir = tmp_path / ".tausik"
        tdir.mkdir()
        (tdir / "tausik.db").write_bytes(b"this is not a sqlite database")
        # Best-effort: a corrupt sink must not propagate an error to the caller.
        emit_supervision_bypass(str(tmp_path), "skip_hooks", "task_gate")

    def test_does_not_read_skip_hooks_env(self, tmp_path, monkeypatch):
        """The auditor must not be silenced by the very flag it audits."""
        project_dir, _tdir, be = _make_project(tmp_path)
        monkeypatch.setenv("TAUSIK_SKIP_HOOKS", "1")
        from _common import emit_supervision_bypass

        emit_supervision_bypass(project_dir, "skip_hooks", "bash_firewall")
        assert len(_supervision_rows(_db_of(be))) == 1


def _db_of(be: SQLiteBackend) -> str:
    """Resolve the on-disk path of a backend's connection."""
    row = be._conn.execute("PRAGMA database_list").fetchone()
    return row[2]  # (seq, name, file)


# --- Audit hash-chain survives raw inserts -----------------------------------


class TestChainStaysValid:
    def test_verify_ok_after_bypass_events(self, tmp_path):
        project_dir, _tdir, be = _make_project(tmp_path)
        from _common import emit_supervision_bypass

        for v in ("skip_hooks", "auto_verify", "gates_disable"):
            emit_supervision_bypass(project_dir, v, "src")
        # A raw INSERT leaves entry_hash NULL; events_verify seals then checks.
        result = be.events_verify(seal=True)
        assert result["status"] == "ok", result


# --- Metric aggregation ------------------------------------------------------


class TestMetric:
    def test_summary_groups_by_action(self, tmp_path):
        project_dir, _tdir, be = _make_project(tmp_path)
        from _common import emit_supervision_bypass

        emit_supervision_bypass(project_dir, "skip_hooks", "task_gate")
        emit_supervision_bypass(project_dir, "skip_hooks", "bash_firewall")
        emit_supervision_bypass(project_dir, "gates_disable", "filesize")

        s = be.supervision_bypasses_summary()
        assert s["total"] == 3
        assert s["by_action"]["bypass_skip_hooks"] == 2
        assert s["by_action"]["bypass_gates_disable"] == 1

    def test_metric_key_present_and_zero_on_clean_project(self, tmp_path):
        _project_dir, _tdir, be = _make_project(tmp_path)
        svc = ProjectService(be)
        m = svc.get_metrics()
        assert m["supervision_bypasses"] == {"total": 0, "by_action": {}}


# --- gates_disable (the CLI/MCP/brain chokepoint) ----------------------------


class TestGatesDisable:
    def test_effective_disable_emits(self, tmp_path):
        _project_dir, tdir, be = _make_project(tmp_path)
        import project_config as pc

        # A custom, unguarded gate: the disable actually takes effect.
        pc.set_gate_enabled("my-own-gate", True, tausik_dir=tdir)
        msg = pc.set_gate_enabled("my-own-gate", False, tausik_dir=tdir)
        assert msg == "Gate 'my-own-gate' disabled."
        rows = _supervision_rows(_db_of(be))
        assert [r[1] for r in rows] == ["bypass_gates_disable"]
        assert rows[0][0] == "my-own-gate"

    def test_enable_does_not_emit(self, tmp_path):
        _project_dir, tdir, be = _make_project(tmp_path)
        import project_config as pc

        pc.set_gate_enabled("my-own-gate", True, tausik_dir=tdir)
        assert _supervision_rows(_db_of(be)) == []

    def test_rejected_disable_does_not_emit(self, tmp_path):
        """A guarded gate whose disable is REFUSED is the guard working, not a
        bypass — it must not be recorded as one."""
        _project_dir, tdir, be = _make_project(tmp_path)
        import project_config as pc

        msg = pc.set_gate_enabled("filesize", False, tausik_dir=tdir)
        assert "NOT disabled" in msg
        assert _supervision_rows(_db_of(be)) == []


# --- l3_block_on_high=false downgrade ----------------------------------------


class TestL3Downgrade:
    _HIGH_RISK = {
        "factors": {
            "gate_coverage": 1.0,
            "test_delta": 1.0,
            "ac_evidence": 1.0,
            "security_hits": 1.0,
            "code_churn": 1.0,
        },
        "defaulted": [],
    }

    def test_downgrade_emits_and_warns(self, tmp_path, monkeypatch):
        _project_dir, _tdir, be = _make_project(tmp_path)
        import risk_l3_trigger

        monkeypatch.setattr(risk_l3_trigger, "_block_enabled", lambda: False)
        blocking, note = risk_l3_trigger.check_l3_required(be._conn, "some-task", self._HIGH_RISK)
        be._conn.commit()
        assert blocking is False
        assert "l3_block_on_high=false" in note
        rows = _supervision_rows(_db_of(be))
        assert [r[1] for r in rows] == ["bypass_l3_block_downgrade"]

    def test_block_enabled_does_not_emit(self, tmp_path, monkeypatch):
        _project_dir, _tdir, be = _make_project(tmp_path)
        import risk_l3_trigger

        monkeypatch.setattr(risk_l3_trigger, "_block_enabled", lambda: True)
        blocking, _note = risk_l3_trigger.check_l3_required(be._conn, "some-task", self._HIGH_RISK)
        be._conn.commit()
        assert blocking is True
        assert _supervision_rows(_db_of(be)) == []

    def test_downgrade_leaves_no_open_transaction(self, tmp_path, monkeypatch):
        """Regression (adversarial review, CRITICAL): the emit must NOT write
        through the caller's connection. task_done calls check_l3_required and
        then `BEGIN IMMEDIATE` — a bare INSERT on `conn` would leave an implicit
        transaction open and make that BEGIN raise 'cannot start a transaction
        within a transaction', crashing the very close this downgrade allows."""
        _project_dir, _tdir, be = _make_project(tmp_path)
        import risk_l3_trigger

        monkeypatch.setattr(risk_l3_trigger, "_block_enabled", lambda: False)
        risk_l3_trigger.check_l3_required(be._conn, "some-task", self._HIGH_RISK)
        # This is exactly what service_task_done does next; it must not raise.
        be._conn.execute("BEGIN IMMEDIATE")
        be._conn.execute("ROLLBACK")
        # And the downgrade was still recorded (on its own connection).
        assert [r[1] for r in _supervision_rows(_db_of(be))] == ["bypass_l3_block_downgrade"]


# --- scope_hard_gate=false start-time bypass ---------------------------------


class TestScopeHardGate:
    def test_bypass_invokes_callback(self, monkeypatch):
        import gate_qg0_check

        monkeypatch.setattr(gate_qg0_check, "_scope_hard_gate_enabled", lambda: False)
        fired: list[bool] = []
        # Everything else valid (rollback + a negative scenario in AC) so ONLY
        # the missing scope is in play and the disabled gate lets it through.
        task = {
            "goal": "g",
            "acceptance_criteria": "does X; returns error on invalid input",
            "complexity": "medium",
            "rollback_plan": "git revert",
        }
        gate_qg0_check.check_qg0_start(
            "s", task, on_scope_hard_gate_bypass=lambda: fired.append(True)
        )
        assert fired == [True]

    def test_enabled_gate_raises_not_calls_back(self, monkeypatch):
        import gate_qg0_check
        from tausik_utils import ServiceError

        monkeypatch.setattr(gate_qg0_check, "_scope_hard_gate_enabled", lambda: True)
        fired: list[bool] = []
        task = {"goal": "g", "acceptance_criteria": "a", "complexity": "medium"}
        with pytest.raises(ServiceError):
            gate_qg0_check.check_qg0_start(
                "s", task, on_scope_hard_gate_bypass=lambda: fired.append(True)
            )
        assert fired == []

    def test_simple_task_neither_raises_nor_records(self, monkeypatch):
        import gate_qg0_check

        monkeypatch.setattr(gate_qg0_check, "_scope_hard_gate_enabled", lambda: False)
        fired: list[bool] = []
        task = {
            "goal": "g",
            "acceptance_criteria": "does X; error on empty input",
            "complexity": "simple",
        }
        gate_qg0_check.check_qg0_start(
            "s", task, on_scope_hard_gate_bypass=lambda: fired.append(True)
        )
        assert fired == []  # simple tasks were never gated; nothing was bypassed

    def test_callback_failure_does_not_crash(self, monkeypatch):
        """Regression (adversarial review, HIGH): a telemetry write failure in
        the scope_hard_gate callback must not crash task_start (AC5 fail-open),
        matching the guard the sibling qg0 callbacks already have."""
        import gate_qg0_check

        monkeypatch.setattr(gate_qg0_check, "_scope_hard_gate_enabled", lambda: False)

        def _boom():
            raise RuntimeError("db is on fire")

        task = {
            "goal": "g",
            "acceptance_criteria": "does X; returns error on invalid input",
            "complexity": "medium",
            "rollback_plan": "git revert",
        }
        # Must not raise despite the callback blowing up.
        gate_qg0_check.check_qg0_start("s", task, on_scope_hard_gate_bypass=_boom)


# --- auto_verify=true weakens Verify-First ------------------------------------


class TestAutoVerify:
    def test_auto_verify_branch_emits(self, tmp_path, monkeypatch):
        _project_dir, _tdir, be = _make_project(tmp_path)
        svc = ProjectService(be)
        # Isolate the emit: the note append and the inline gate run are not
        # what we assert, only that taking the auto_verify opt-out records it.
        monkeypatch.setattr(be, "task_append_notes", lambda *a, **k: None)

        import project_config
        import service_verification

        monkeypatch.setattr(
            project_config, "load_config", lambda: {"task_done": {"auto_verify": True}}
        )
        monkeypatch.setattr(
            project_config, "get_gates_for_trigger", lambda *a, **k: [{"name": "pytest"}]
        )
        monkeypatch.setattr(
            service_verification, "has_fresh_verify_run", lambda *a, **k: (False, None)
        )
        monkeypatch.setattr(
            service_verification, "run_gates_with_cache", lambda *a, **k: (True, [], "passed")
        )

        from gate_verify_first import enforce_verify_first

        enforce_verify_first(svc, {}, "av-task", ["scripts/x.py"])
        rows = _supervision_rows(_db_of(be))
        assert [r[1] for r in rows] == ["bypass_auto_verify"]

    def test_emit_failure_does_not_crash(self, tmp_path, monkeypatch):
        """Regression (adversarial review, HIGH): a telemetry write failure on
        the auto_verify path must not crash task_done (AC5 fail-open)."""
        _project_dir, _tdir, be = _make_project(tmp_path)
        svc = ProjectService(be)
        monkeypatch.setattr(be, "task_append_notes", lambda *a, **k: None)

        def _boom(*a, **k):
            raise RuntimeError("db is on fire")

        monkeypatch.setattr(be, "event_add", _boom)

        import project_config
        import service_verification

        monkeypatch.setattr(
            project_config, "load_config", lambda: {"task_done": {"auto_verify": True}}
        )
        monkeypatch.setattr(
            project_config, "get_gates_for_trigger", lambda *a, **k: [{"name": "pytest"}]
        )
        monkeypatch.setattr(
            service_verification, "has_fresh_verify_run", lambda *a, **k: (False, None)
        )
        monkeypatch.setattr(
            service_verification, "run_gates_with_cache", lambda *a, **k: (True, [], "passed")
        )

        from gate_verify_first import enforce_verify_first

        # Must not raise despite event_add blowing up.
        enforce_verify_first(svc, {}, "av-task", ["scripts/x.py"])


# --- Hook subprocess end-to-end (proves the hook -> helper wiring) -----------


class TestHookSubprocessWiring:
    def _run_hook(self, hook_name: str, project_dir: str, env_extra: dict) -> int:
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = project_dir
        env.update(env_extra)
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", os.path.join(_HOOKS, hook_name)],
            input="{}",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        return proc.returncode

    def test_bash_firewall_emits_on_skip(self, tmp_path):
        project_dir, _tdir, be = _make_project(tmp_path)
        rc = self._run_hook("bash_firewall.py", project_dir, {"TAUSIK_SKIP_HOOKS": "1"})
        assert rc == 0
        rows = _supervision_rows(_db_of(be))
        assert [r[1] for r in rows] == ["bypass_skip_hooks"]
        assert rows[0][0] == "bash_firewall"

    def test_git_push_gate_emits_on_skip(self, tmp_path):
        project_dir, _tdir, be = _make_project(tmp_path)
        rc = self._run_hook("git_push_gate.py", project_dir, {"TAUSIK_SKIP_PUSH_HOOK": "1"})
        assert rc == 0
        rows = _supervision_rows(_db_of(be))
        assert [r[1] for r in rows] == ["bypass_skip_push_hook"]
        assert rows[0][0] == "git_push_gate"

    def test_no_skip_emits_nothing(self, tmp_path):
        """The event fires only on the bypass, never in normal operation."""
        project_dir, _tdir, be = _make_project(tmp_path)
        # No skip env: bash_firewall runs its normal path over an empty command.
        rc = self._run_hook("bash_firewall.py", project_dir, {})
        assert rc == 0
        assert _supervision_rows(_db_of(be)) == []
