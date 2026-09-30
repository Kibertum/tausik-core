"""Cheap gates run first, and the expensive one is not paid for a run already lost.

THE MEASUREMENT. Static gates read files and answer in seconds; a test gate compiles or runs
the project and answers in minutes. On this project, session #278: ruff plus the duplicate-test
audit plus the prose audit together take 3.5 seconds, against about four minutes for the full
lane. Fifteen times that shift a static gate failed AFTER the lane had already run — each
costing the lane again plus two or three calls, which is where the median task went from 6
calls in April to 32 in September.

TWO RULES, AND THE SECOND IS WHY THIS IS NOT PLAIN FAIL-FAST:

* BETWEEN phases the run stops. Nothing the expensive half could say survives the fix the
  cheap half just demanded.
* WITHIN a phase nothing stops. Three defects have to come back in one report; stopping at the
  first would turn one round into three, which is the cost this change exists to remove.

A SKIPPED SLOW GATE IS `COULD_NOT_RUN`, NOT A PASS. The gate applies and produced no evidence,
and SENAR §8.6(e) is explicit that an absent verdict cannot certify. Recording it as a pass
would let a green report mean "the tests never ran".
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import gate_outcome  # noqa: E402
import gate_runner  # noqa: E402
from gate_spec import COST_FAST, COST_SLOW, SLOW_GATES, gate_cost  # noqa: E402

#: The REAL runner, captured at import. `tests/conftest.py` replaces
#: `gate_runner.run_gates` for the whole suite to stop pytest running inside pytest, and its
#: own docstring says a test of gate behaviour has to reach past it. Binding the function
#: here — before any fixture runs — is the smallest way to do that, and it leaves the guard
#: in place for every other test.
_RUN_GATES = gate_runner.run_gates


def _gate(name, severity="block"):
    return {"name": name, "severity": severity, "enabled": True, "trigger": ["verify"]}


@pytest.fixture
def runner(monkeypatch):
    """Drive `run_gates` over declared gates with declared verdicts.

    The seam is `impl_for`: the runner resolves a gate's implementation by name and calls it,
    so handing back a stub per gate exercises the real loop — the phase boundary, the result
    shapes and the ordering — without running anything that takes minutes.
    """
    ran: list[str] = []

    def build(gates, failing=()):
        monkeypatch.setattr(gate_runner, "load_config", lambda *_a, **_k: {})
        monkeypatch.setattr(gate_runner, "get_gates_for_trigger", lambda *_a, **_k: list(gates))
        monkeypatch.setattr(gate_runner, "gate_applies_to", lambda *_a, **_k: True)

        def impl_for(name):
            def run(gate, _files):
                ran.append(name)
                return (name not in failing, "boom" if name in failing else "")

            return run

        monkeypatch.setattr(gate_runner, "impl_for", impl_for)
        return ran

    return build


class TestTheCostIsDeclaredAndComplete:
    def test_a_test_runner_is_slow_and_static_analysis_is_fast(self):
        assert gate_cost("pytest") == COST_SLOW
        assert gate_cost("ruff") == COST_FAST
        assert gate_cost("test_dedupe") == COST_FAST

    def test_an_unknown_gate_defaults_to_fast(self):
        """A new gate is cheap until somebody says otherwise: the wrong default would put a
        four-minute gate in the phase that is supposed to answer in seconds."""
        assert gate_cost("some-gate-nobody-declared") == COST_FAST

    def test_every_gate_that_runs_the_project_is_declared_slow(self):
        """THE LIST CANNOT SILENTLY MISS ONE. A registry entry whose command runs tests or
        builds and is not in `SLOW_GATES` would be sorted into the cheap phase and paid for
        before the phase boundary could protect anything."""
        from default_gates import DEFAULT_GATES

        missed = []
        for name, gate in DEFAULT_GATES.items():
            command = str(gate.get("command") or "")
            runs_project = any(
                token in command for token in (" test", "test ", "pytest", "swift build", "javac")
            )
            if runs_project and name not in SLOW_GATES:
                missed.append((name, command))
        assert not missed, f"declare these in gate_spec.SLOW_GATES: {missed}"


class TestThePhaseBoundary:
    def test_the_slow_gate_does_not_run_when_a_fast_one_failed(self, runner):
        ran = runner([_gate("pytest"), _gate("ruff")], failing={"ruff"})
        passed, results = _RUN_GATES("verify", ["a.py"])
        assert "ruff" in ran and "pytest" not in ran
        assert passed is False

    def test_the_skipped_slow_gate_is_could_not_run_and_not_a_pass(self, runner):
        runner([_gate("pytest"), _gate("ruff")], failing={"ruff"})
        _passed, results = _RUN_GATES("verify", ["a.py"])
        slow = next(r for r in results if r["name"] == "pytest")
        assert slow["outcome"] == gate_outcome.COULD_NOT_RUN
        assert slow["reason_code"] == gate_outcome.REASON_FAST_PHASE_FAILED
        assert slow["passed"] is False
        assert "takes minutes" in slow["output"]

    def test_the_slow_gate_runs_when_the_fast_ones_pass(self, runner):
        ran = runner([_gate("pytest"), _gate("ruff"), _gate("test_dedupe")])
        passed, _ = _RUN_GATES("verify", ["a.py"])
        assert ran.index("pytest") == len(ran) - 1, "cheap first, expensive last"
        assert passed is True

    def test_a_warning_level_fast_failure_does_not_stop_the_slow_phase(self, runner):
        """Only a BLOCKING failure closes the boundary. A warn-level gate has not refused
        anything, and skipping the tests over it would be a gate raising its own severity."""
        ran = runner([_gate("pytest"), _gate("ruff", severity="warn")], failing={"ruff"})
        _RUN_GATES("verify", ["a.py"])
        assert "pytest" in ran


class TestNothingStopsInsideAPhase:
    def test_three_failing_fast_gates_all_report(self, runner):
        """AC-3, and the reason this is not plain fail-fast: three defects have to come back
        in ONE report. Stopping at the first would turn one round into three — the very cost
        this change removes."""
        gates = [_gate("ruff"), _gate("test_dedupe"), _gate("filesize"), _gate("pytest")]
        ran = runner(gates, failing={"ruff", "test_dedupe", "filesize"})
        _passed, results = _RUN_GATES("verify", ["a.py"])
        assert {"ruff", "test_dedupe", "filesize"} <= set(ran)
        failed = {r["name"] for r in results if r.get("passed") is False}
        assert {"ruff", "test_dedupe", "filesize"} <= failed

    def test_the_order_within_a_phase_is_not_disturbed(self, runner):
        """The sort is stable on cost alone: gates of the same cost keep registry order, so
        this change cannot reshuffle a report somebody reads by position."""
        gates = [_gate("ruff"), _gate("test_dedupe"), _gate("filesize")]
        ran = runner(gates)
        _RUN_GATES("verify", ["a.py"])
        assert ran == ["ruff", "test_dedupe", "filesize"]


class TestNothingWasWeakened:
    def test_the_static_gates_now_answer_at_verify_too(self):
        """AC-4: they used to fire only at task-done, which is AFTER the lane and after the
        scoped verify — the last possible moment, at the highest possible price."""
        from default_gates import DEFAULT_GATES

        for name in ("test_dedupe", "filesize", "class_surface", "bootstrap_drift", "doc_coverage"):
            triggers = DEFAULT_GATES[name].get("trigger") or []
            assert "verify" in triggers, name
            assert "task-done" in triggers, f"{name}: the later gate must stay as well"

    def test_no_gate_lost_its_severity(self):
        """AC-5: reordering is not relaxing. Every blocking gate is still blocking."""
        from default_gates import DEFAULT_GATES

        blocking = {n for n, g in DEFAULT_GATES.items() if g.get("severity") == "block"}
        for name in ("ruff", "pytest", "test_dedupe", "filesize", "bootstrap_drift"):
            assert name in blocking, name

    def test_the_registry_still_holds_every_gate(self):
        from default_gates import DEFAULT_GATES

        assert len(DEFAULT_GATES) >= 48
