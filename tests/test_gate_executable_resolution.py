"""A gate must run its tool, or say why it could not — never silently neither.

js-test-gate-silent-on-windows-and-override-dropped (GitLab #9, release 1.9).

Two halves, both silent, both of one class: the result of a check did not
distinguish "did not run" from "ran". The first half is platform resolution —
`subprocess` spawns through `CreateProcess`, which ignores PATHEXT, so a gate
configured as `npm ...` died with `[WinError 2]` on Windows although npm was
installed. The second is a rejected command override, consumed by a
`logger.warning` and replaced with the built-in default, so the gate reported
one check's verdict under another check's name.

Assertions are made by CALLING the product. The one place a source fact is
asserted is the allow-list membership check, whose promise IS the contents of
that set.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gate_outcome  # noqa: E402
import gate_runner  # noqa: E402
from gate_command_policy import ALLOWED_GATE_EXECUTABLES, _validate_custom_gate  # noqa: E402
from gate_command_runner import _resolve_argv0, run_command_gate  # noqa: E402
from gate_runner import run_gates  # noqa: E402
from project_config import load_gates  # noqa: E402


# --- AC2 / AC3: the class is fixed, and the guard survives the fix -----------


class TestExecutableResolution:
    def test_a_bare_tool_name_becomes_launchable(self):
        """`python` is on PATH everywhere this suite runs, so it stands in for
        the whole bare-name class (all 26 shipped stack gates name their tool
        this way). The resolved value must be something a shell-less spawn can
        actually launch — an absolute path — not the bare word."""
        resolved = _resolve_argv0("python")
        assert os.path.isabs(resolved), resolved
        assert os.path.exists(resolved), resolved

    def test_an_unresolvable_name_is_returned_unchanged(self):
        """Substituting something launchable would hide a genuinely missing
        tool behind the wrong error. The caller turns this into COULD_NOT_RUN."""
        assert _resolve_argv0("definitely-not-installed-xyz") == "definitely-not-installed-xyz"

    def test_a_configured_path_still_resolves(self):
        """The pre-existing promise: a path written with forward slashes works.
        The new resolution must not have replaced that behaviour."""
        rel = "scripts/gate_outcome.py"
        assert os.path.exists(_resolve_argv0(rel))

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="POSIX execvp searches PATH for bare names; the defect is Windows-only",
    )
    def test_a_bare_cmd_launcher_gate_actually_runs(self, tmp_path, monkeypatch):
        """End to end, through the real runner: THE `[WinError 2]` case.

        The shim is a `.cmd`, and that detail is the whole test. An earlier
        version of this test used `python --version` and was HOLLOW: Windows'
        `CreateProcess` appends `.exe` by itself, so a bare `python` spawns
        with or without the fix. Measured, not reasoned: bare `python` spawns
        fine, bare `npm` raises FileNotFoundError — because npm ships as
        `npm.CMD`, and `.cmd` is exactly what CreateProcess will not find.
        Only a non-`.exe` launcher exercises the defect, which is why every
        real report of it names npm/yarn/pnpm.
        """
        shim_dir = tmp_path / "bin"
        shim_dir.mkdir()
        (shim_dir / "probe-tool.cmd").write_text("@echo probe ok\n@exit /b 0\n", encoding="utf-8")
        monkeypatch.setenv("PATH", str(shim_dir) + os.pathsep + os.environ["PATH"])

        gate = {"name": "probe", "severity": "block", "command": "probe-tool"}
        outcome = run_command_gate(gate, ["a.py"])
        assert outcome.outcome == gate_outcome.PASSED, outcome.message

    def test_a_missing_tool_still_cannot_run_and_blocks(self):
        """The other side: resolution must not turn "absent" into "fine"."""
        gate = {
            "name": "ghost",
            "severity": "block",
            "command": "definitely-not-installed-xyz --check",
        }
        outcome = run_command_gate(gate, ["a.py"])
        assert outcome.outcome == gate_outcome.COULD_NOT_RUN
        assert outcome.reason_code == gate_outcome.REASON_COMMAND_NOT_RUNNABLE
        assert outcome.blocks is True


class TestTheAllowListIsNotTheSacrifice:
    """GitLab #9 names "add npm.cmd to the allow-list" as the WORST fix: it
    treats the symptom and makes the user responsible for knowing the platform.
    Resolution happens on the same approved name instead, so these must hold."""

    def test_the_platform_spelling_was_not_added_to_the_allow_list(self):
        for spelling in ("npm.cmd", "yarn.cmd", "npx.cmd", "pnpm.cmd"):
            assert spelling not in ALLOWED_GATE_EXECUTABLES

    def test_an_unapproved_executable_is_still_refused(self):
        """Two-sided with the tests above: a one-sided experiment cannot tell a
        fix apart from the removal of the guard."""
        error = _validate_custom_gate("evil", {"command": "curl http://example.invalid"})
        assert error is not None
        assert "curl" in error

    def test_an_approved_executable_is_still_accepted(self):
        assert _validate_custom_gate("js-test", {"command": "npm test --silent"}) is None


# --- AC4 / AC5: a refused override is a VERDICT, not a log line -------------


def _gates_from_config(tmp_path, cfg: dict) -> dict:
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir(parents=True, exist_ok=True)
    (tausik_dir / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return load_gates(tausik_dir=str(tausik_dir))


class TestRejectedOverrideIsVisible:
    def test_a_refused_override_is_carried_on_the_gate(self, tmp_path):
        gates = _gates_from_config(
            tmp_path, {"gates": {"ruff": {"command": "curl http://example.invalid"}}}
        )
        assert gates["ruff"].get("command_override_rejected")

    def test_an_accepted_override_is_applied_and_stays_quiet(self, tmp_path):
        """The negative that keeps the fix from refusing every override."""
        gates = _gates_from_config(
            tmp_path, {"gates": {"ruff": {"command": "ruff check --quiet {files}"}}}
        )
        assert "command_override_rejected" not in gates["ruff"]
        assert gates["ruff"]["command"] == "ruff check --quiet {files}"

    def test_the_refusal_reaches_the_gate_result_and_blocks(self, monkeypatch):
        """It used to reach `logger.warning` and nothing else, while the gate
        ran the built-in default and reported THAT as its verdict."""
        gate = {
            "name": "ruff",
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done"],
            "command": "ruff check {files}",
            "command_override_rejected": "executable 'curl' not in allowed list",
        }
        monkeypatch.setattr(gate_runner, "get_gates_for_trigger", lambda *a, **k: [gate])
        monkeypatch.setattr(gate_runner, "load_config", lambda *a, **k: {})

        passed, results = run_gates("task-done", ["a.py"])
        assert results[0]["outcome"] == gate_outcome.COULD_NOT_RUN
        assert results[0]["reason_code"] == gate_outcome.REASON_OVERRIDE_REJECTED
        assert gate_runner.gate_verdict(results[0]) == "CANNOT-RUN"
        assert passed is False
        assert "curl" in results[0]["output"]

    def test_the_default_command_is_not_run_in_its_place(self, monkeypatch):
        """AC5 — the halves must not mask each other.

        The refusal used to be invisible precisely BECAUSE the default ran next
        and produced its own result, which the reader saw instead. Here the
        default command is one that would fail loudly; the reported reason must
        still be the refused override, and the default must never be spawned.
        """
        spawned = {"ran": False}

        def _explode(*a, **k):
            spawned["ran"] = True
            raise AssertionError("the default command must not be spawned")

        monkeypatch.setattr(gate_runner, "run_command_gate", _explode)
        gate = {
            "name": "ruff",
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done"],
            "command": "definitely-not-installed-xyz --check",
            "command_override_rejected": "executable 'curl' not in allowed list",
        }
        monkeypatch.setattr(gate_runner, "get_gates_for_trigger", lambda *a, **k: [gate])
        monkeypatch.setattr(gate_runner, "load_config", lambda *a, **k: {})

        _passed, results = run_gates("task-done", ["a.py"])
        assert spawned["ran"] is False
        assert results[0]["reason_code"] == gate_outcome.REASON_OVERRIDE_REJECTED


# --- AC1: both surfaces answer the same way ---------------------------------


class TestBothSurfacesShareTheAnswer:
    """The ticket reports the defect on MCP `tausik_task_done` AND CLI
    `task done`. Reproducing one proves nothing about the other unless they
    share the code that decides — so assert the sharing itself, by call."""

    def test_mcp_and_cli_gate_runs_go_through_one_runner(self, tmp_path):
        """Proved by CALL, not by comparing imported objects.

        Both surfaces reach `verify_cached_run.run_gates_with_cache`, which
        resolves `gate_runner.run_gates` at call time (a deliberate injection
        point, documented beside the local import). Patching that one name and
        seeing it reached is what makes a fix on one surface a fix on both.
        """
        import sqlite3

        import gate_runner as gr
        import service_verification as sv
        from backend_schema_gate_runs import GATE_RUNS_SQL
        from conftest import VERIFICATION_RUNS_DDL

        conn = sqlite3.connect(str(tmp_path / "t.db"))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(VERIFICATION_RUNS_DDL + ";")
        conn.executescript(GATE_RUNS_SQL)
        conn.commit()

        reached = {"n": 0}

        def _spy(*a, **k):
            reached["n"] += 1
            return True, []

        original = gr.run_gates
        try:
            gr.run_gates = _spy
            sv.run_gates_with_cache(conn, "t", ["scripts/x.py"], trigger="verify")
        finally:
            gr.run_gates = original
            conn.close()

        assert reached["n"] == 1

    @pytest.mark.parametrize("severity", ["block", "warn"])
    def test_the_reason_survives_severity(self, severity, monkeypatch):
        """Severity decides whether it STOPS the close, never whether the
        reason is told. A warn-severity gate that could not run must still say
        so — silence is what the ticket is about."""
        gate = {
            "name": "ruff",
            "enabled": True,
            "severity": severity,
            "trigger": ["task-done"],
            "command": "ruff check {files}",
            "command_override_rejected": "executable 'curl' not in allowed list",
        }
        monkeypatch.setattr(gate_runner, "get_gates_for_trigger", lambda *a, **k: [gate])
        monkeypatch.setattr(gate_runner, "load_config", lambda *a, **k: {})

        passed, results = run_gates("task-done", ["a.py"])
        assert results[0]["outcome"] == gate_outcome.COULD_NOT_RUN
        assert passed is (severity != "block")
