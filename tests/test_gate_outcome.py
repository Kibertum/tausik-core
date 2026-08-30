"""The outcome of a check is a TYPE, and "could not run" is one of its values.

check-result-conflates-could-not-run-with-passed (release 1.9, wave 2).

Every assertion here is made by CALLING the product and reading what it
returned. Nothing asserts a source literal: a test that pins the text of an
implementation breaks on every refactor and proves nothing about the promise
(convention #417). The one exception is the DB round-trip, whose promise IS the
stored shape, and it reads that shape back out of SQLite rather than out of DDL.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import gate_outcome  # noqa: E402
import gate_runner  # noqa: E402
from gate_command_runner import run_command_gate  # noqa: E402
from gate_runner import gate_verdict, run_gates, summarize_results  # noqa: E402


# --- AC1: four named outcomes, reached by construction ----------------------


class TestTheTypeExists:
    def test_all_four_outcomes_are_constructible_and_named(self):
        built = [
            gate_outcome.passed("ok"),
            gate_outcome.failed("boom"),
            gate_outcome.not_applicable(gate_outcome.REASON_STACK_MISMATCH),
            gate_outcome.could_not_run(gate_outcome.REASON_TIMED_OUT),
        ]
        assert [o.outcome for o in built] == [
            gate_outcome.PASSED,
            gate_outcome.FAILED,
            gate_outcome.NOT_APPLICABLE,
            gate_outcome.COULD_NOT_RUN,
        ]

    def test_executed_and_blocking_are_separate_questions(self):
        """The two axes the old booleans fused. `ran` is not `blocks`."""
        ran_blocks = {
            (o.ran, o.blocks)
            for o in (
                gate_outcome.passed(),
                gate_outcome.failed(),
                gate_outcome.not_applicable(gate_outcome.REASON_STACK_MISMATCH),
                gate_outcome.could_not_run(gate_outcome.REASON_TIMED_OUT),
            )
        }
        # All four combinations are distinct; COULD_NOT_RUN is the one the
        # legacy pair could not express: did not run, and still blocks.
        assert ran_blocks == {(True, False), (True, True), (False, False), (False, True)}

    def test_an_unknown_outcome_is_refused(self):
        with pytest.raises(ValueError):
            gate_outcome.GateOutcome("PROBABLY_FINE")


# --- AC2: a non-execution cannot be spelled without its reason --------------


class TestReasonIsMandatory:
    @pytest.mark.parametrize("outcome", [gate_outcome.COULD_NOT_RUN, gate_outcome.NOT_APPLICABLE])
    def test_refused_at_construction_without_a_reason(self, outcome):
        with pytest.raises(ValueError):
            gate_outcome.GateOutcome(outcome, detail="something happened")

    @pytest.mark.parametrize("outcome", [gate_outcome.COULD_NOT_RUN, gate_outcome.NOT_APPLICABLE])
    def test_but_constructs_with_one(self, outcome):
        """The other half of the two-sided proof: the guard is not just 'always no'."""
        built = gate_outcome.GateOutcome(outcome, reason_code="some_reason")
        assert built.reason_code == "some_reason"

    def test_a_verdict_earned_by_running_needs_no_reason(self):
        assert gate_outcome.passed().reason_code == ""
        assert gate_outcome.failed().reason_code == ""


# --- AC3 / AC4: what blocks, and what deliberately does not -----------------


def _one_gate_run(monkeypatch, impl_outcome, severity="block"):
    """Drive run_gates with a single gate whose implementation we control."""
    gate = {"name": "probe", "enabled": True, "severity": severity, "trigger": ["task-done"]}
    monkeypatch.setattr(gate_runner, "get_gates_for_trigger", lambda *a, **k: [gate])
    monkeypatch.setattr(gate_runner, "load_config", lambda *a, **k: {})
    monkeypatch.setattr(gate_runner, "impl_for", lambda name: lambda g, f: impl_outcome)
    return run_gates("task-done", ["a.py"])


class TestBlockingIsDecidedByOutcome:
    def test_could_not_run_blocks(self, monkeypatch):
        """SENAR 1.4 §8.6(e): no evidence produced, so nothing is certified."""
        passed, results = _one_gate_run(
            monkeypatch,
            gate_outcome.could_not_run(gate_outcome.REASON_NO_TESTS_COLLECTED, "nothing collected"),
        )
        assert results[0]["outcome"] == gate_outcome.COULD_NOT_RUN
        assert passed is False

    def test_not_applicable_does_not_block(self, monkeypatch):
        """The negative constraint. Same gate, same severity — opposite answer.

        A change that honestly matches no test is a NORMAL case. Collapsing it
        into the blocking state would replace one indistinguishability with
        another, which is the failure mode this task exists to avoid.
        """
        passed, results = _one_gate_run(
            monkeypatch,
            gate_outcome.not_applicable(gate_outcome.REASON_NO_TEST_MAPPING, "no map"),
        )
        assert results[0]["outcome"] == gate_outcome.NOT_APPLICABLE
        assert passed is True

    def test_the_two_are_distinguishable_in_the_result(self, monkeypatch):
        """Both "did not run" — and the record says which, and why."""
        _, cannot = _one_gate_run(
            monkeypatch, gate_outcome.could_not_run(gate_outcome.REASON_TIMED_OUT)
        )
        _, legit = _one_gate_run(
            monkeypatch, gate_outcome.not_applicable(gate_outcome.REASON_STACK_MISMATCH)
        )
        assert cannot[0]["outcome"] != legit[0]["outcome"]
        assert cannot[0]["reason_code"] != legit[0]["reason_code"]


# --- AC7: pytest already distinguishes these; stop throwing it away ---------


class TestExitCodeIsNotCollapsed:
    def _pytest_gate(self, body, tmp_path):
        """A real subprocess: the promise is about an exit code, so run one."""
        script = tmp_path / "probe.py"
        script.write_text(body, encoding="utf-8")
        return {
            "name": "pytest",
            "severity": "block",
            "command": f'python "{script}" pytest',
            "timeout": 60,
        }

    def test_exit_5_means_nothing_ran(self, tmp_path):
        gate = self._pytest_gate("import sys; print('5 deselected'); sys.exit(5)", tmp_path)
        outcome = run_command_gate(gate, ["a.py"])
        assert outcome.outcome == gate_outcome.COULD_NOT_RUN
        assert outcome.reason_code == gate_outcome.REASON_NO_TESTS_COLLECTED
        assert outcome.ran is False

    def test_exit_1_still_means_a_real_failure(self, tmp_path):
        """The other side. A fix that turned every red suite into 'could not
        run' would be worse than the defect it replaced."""
        gate = self._pytest_gate("import sys; print('1 failed'); sys.exit(1)", tmp_path)
        outcome = run_command_gate(gate, ["a.py"])
        assert outcome.outcome == gate_outcome.FAILED
        assert outcome.ran is True
        assert outcome.blocks is True

    def test_exit_0_still_passes(self, tmp_path):
        gate = self._pytest_gate("import sys; print('3 passed'); sys.exit(0)", tmp_path)
        assert run_command_gate(gate, ["a.py"]).outcome == gate_outcome.PASSED

    def test_exit_5_from_a_non_pytest_command_is_a_failure(self, tmp_path):
        """5 is pytest's word for "collected nothing", not a universal one.

        Reading it as "could not run" for an arbitrary tool would invent a
        meaning the tool never assigned, so the mapping is gated on the command
        actually being pytest.
        """
        script = tmp_path / "probe.py"
        script.write_text("import sys; sys.exit(5)", encoding="utf-8")
        gate = {"name": "linter", "severity": "block", "command": f'python "{script}"'}
        assert run_command_gate(gate, ["a.py"]).outcome == gate_outcome.FAILED


# --- AC6: the refusal names the way out -------------------------------------


class TestTheRefusalIsActionable:
    def test_it_names_the_environment_variable_and_not_the_missing_flag(self, tmp_path):
        """#182 measured the cost of a refusal that named neither cause nor cure.

        The expected text is taken FROM THE PRODUCT — the remedy the runner
        actually emits — rather than re-typed here as a literal.
        """
        script = tmp_path / "probe.py"
        script.write_text("import sys; sys.exit(5)", encoding="utf-8")
        gate = {"name": "pytest", "severity": "block", "command": f'python "{script}" pytest'}
        message = run_command_gate(gate, ["a.py"]).message

        assert "TAUSIK_VERIFY_FULL=1" in message
        # `verify --full` DOES NOT EXIST — `verify --help` lists --task, --scope,
        # --relevant-files and --no-tests-expected, and nothing else. Naming it
        # here would send the reader to a flag the product refuses. pyproject.toml
        # carried the same false promise until it was deleted rather than
        # implemented, so the environment variable is the only name in the tree.
        assert "--full" not in message


# --- AC10: the summary stops signing emptiness ------------------------------


class TestSummaryAndVerdict:
    def test_could_not_run_is_not_reported_as_pass_or_skip(self):
        result = {
            "name": "pytest",
            "outcome": gate_outcome.COULD_NOT_RUN,
            "reason_code": gate_outcome.REASON_NO_TESTS_COLLECTED,
            "passed": False,
            "skipped": False,
        }
        verdict = gate_verdict(result)
        assert verdict not in ("PASS", "SKIP")
        assert verdict == "CANNOT-RUN"
        assert "pytest=CANNOT-RUN" in summarize_results([result])

    def test_legacy_rows_without_an_outcome_still_read(self):
        """Rows written before v47 have no outcome. They fall back, and the
        fallback still cannot say CANNOT-RUN — which is why the column exists."""
        assert gate_verdict({"passed": True, "skipped": False}) == "PASS"
        assert gate_verdict({"passed": False, "skipped": False}) == "FAIL"
        assert gate_verdict({"passed": True, "skipped": True}) == "SKIP"


# --- AC9: the receipt stores the outcome, and it survives the round trip ----


class TestPersistence:
    def _db(self, tmp_path):
        from backend_init import init_schema

        conn = sqlite3.connect(str(tmp_path / "t.db"))
        conn.execute("PRAGMA foreign_keys=ON")
        init_schema(conn)
        return conn

    def test_outcome_and_reason_round_trip_through_sqlite(self, tmp_path):
        """Read back from the DB, not from the DDL: the promise is the stored row."""
        from gate_run_record import record_gate_runs

        conn = self._db(tmp_path)
        conn.execute(
            "INSERT INTO verification_runs (id, task_slug, scope, command, exit_code,"
            " files_hash, ran_at, no_tests_declared)"
            " VALUES (1, 't', 'standard', 'pytest', 1, 'h', 'now', 0)"
        )
        record_gate_runs(
            conn,
            verification_run_id=1,
            task_slug="t",
            trigger="task-done",
            gate_results=[
                {
                    "name": "pytest",
                    "severity": "block",
                    "outcome": gate_outcome.COULD_NOT_RUN,
                    "reason_code": gate_outcome.REASON_NO_TESTS_COLLECTED,
                    "passed": False,
                    "skipped": False,
                    "duration_ms": 3,
                }
            ],
        )
        conn.commit()

        row = conn.execute(
            "SELECT outcome, reason_code FROM gate_runs WHERE gate_name='pytest'"
        ).fetchone()
        assert row == (
            gate_outcome.COULD_NOT_RUN,
            gate_outcome.REASON_NO_TESTS_COLLECTED,
        )
        # And the stored row reconstructs the same reading.
        assert gate_verdict({"outcome": row[0], "reason_code": row[1]}) == "CANNOT-RUN"
        conn.close()

    def test_a_pre_v47_style_result_stores_null_rather_than_a_guess(self, tmp_path):
        """Inventing an outcome for a row that never had one would manufacture
        exactly the evidence this task exists to stop manufacturing."""
        from gate_run_record import record_gate_runs

        conn = self._db(tmp_path)
        conn.execute(
            "INSERT INTO verification_runs (id, task_slug, scope, command, exit_code,"
            " files_hash, ran_at, no_tests_declared)"
            " VALUES (1, 't', 'standard', 'pytest', 1, 'h', 'now', 0)"
        )
        record_gate_runs(
            conn,
            verification_run_id=1,
            task_slug="t",
            trigger="task-done",
            gate_results=[{"name": "old", "severity": "warn", "passed": True, "skipped": True}],
        )
        conn.commit()
        assert conn.execute(
            "SELECT outcome, reason_code FROM gate_runs WHERE gate_name='old'"
        ).fetchone() == (None, None)
        conn.close()
