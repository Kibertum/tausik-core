"""A project-wide PASS is not evidence about the files a task declared.

a-passing-irrelevant-gate-unblocks-an-empty-verify. Observed in session #158
(run #1643: hadolint PASS, pytest SKIP on a python-only change, receipt signed)
and re-measured before this fix on a temp project: a custom gate with no file
scope passed, pytest skipped for want of a mapped test, and `task done
--ac-verified --verify-handle` closed the task — no cutoff downstream.

Both ends are pinned: the refusal, and the runs that must stay green — a
scoped gate that ran, a config made only of project-wide gates, and the
declared `--no-tests-expected` exemption.
"""

from __future__ import annotations

import sqlite3

import pytest

import gate_runner
import service_verification as sv
from conftest import VERIFICATION_RUNS_DDL
from verify_zero_gate import (
    EXECUTED,
    NONE_APPLICABLE,
    declares_file_scope,
    run_state,
    unscoped_only,
)

DECLARED = ["mod.py"]

# Bound at import, before conftest's autouse `_mock_run_gates` replaces it.
_REAL_RUN_GATES = gate_runner.run_gates


def _res(name, outcome, scoped):
    skipped = outcome == "NOT_APPLICABLE"
    return {
        "name": name,
        "severity": "block",
        "outcome": outcome,
        "passed": outcome != "FAILED",
        "skipped": skipped,
        "file_scoped": scoped,
    }


PYTEST_SKIP = _res("pytest", "NOT_APPLICABLE", True)
WIDE_PASS = _res("irrelevant", "PASSED", False)
RUFF_PASS = _res("ruff", "PASSED", True)


@pytest.mark.parametrize(
    "gate, scoped",
    [
        pytest.param({"command": "ruff check {files}"}, True, id="files-placeholder"),
        pytest.param({"command": "pytest -q {test_files_for_files}"}, True, id="test-mapping"),
        pytest.param({"command": "go test ./...", "file_extensions": [".go"]}, True, id="ext"),
        pytest.param(
            {"command": "hadolint x", "file_patterns": ["Dockerfile"]}, True, id="pattern"
        ),
        pytest.param({"command": "go test ./..."}, False, id="project-wide"),
        pytest.param({}, False, id="no-command"),
    ],
)
def test_a_gate_is_scoped_only_when_it_says_which_files(gate, scoped):
    assert declares_file_scope(gate) is scoped


def test_the_observed_run_is_not_an_execution():
    """NEGATIVE — run #1643 in shape: python change, pytest SKIP, unscoped PASS."""
    assert unscoped_only([PYTEST_SKIP, WIDE_PASS]) == ["irrelevant"]
    assert run_state([PYTEST_SKIP, WIDE_PASS]) == NONE_APPLICABLE


@pytest.mark.parametrize(
    "results",
    [
        pytest.param([PYTEST_SKIP, WIDE_PASS, RUFF_PASS], id="a-scoped-gate-ran"),
        pytest.param([WIDE_PASS, _res("npm-test", "PASSED", False)], id="only-project-wide"),
        pytest.param(
            [{"name": "pytest", "outcome": "PASSED", "passed": True, "skipped": False}],
            id="legacy-row-without-the-flag",
        ),
    ],
)
def test_legitimate_runs_stay_executions(results):
    assert unscoped_only(results) == []
    assert run_state(results) == EXECUTED


@pytest.fixture
def conn(tmp_path, monkeypatch):
    from backend_schema_gate_runs import GATE_RUNS_SQL

    monkeypatch.setattr(
        "project_config.load_config", lambda: {"verify_pipeline_timeout_seconds": 0}
    )
    c = sqlite3.connect(str(tmp_path / "t.db"))
    c.row_factory = sqlite3.Row
    c.executescript(VERIFICATION_RUNS_DDL)
    c.executescript(GATE_RUNS_SQL)
    yield c
    c.close()


def _verify(conn, monkeypatch, results, **kw):
    monkeypatch.setattr(gate_runner, "run_gates", lambda *_a, **_k: (True, results))
    passed, out, status = sv.run_gates_with_cache(
        conn, "t", DECLARED, scope="manual", trigger="verify", **kw
    )
    return passed, out, status


def test_verify_blocks_the_observed_run_and_names_the_wide_gate(conn, monkeypatch):
    passed, out, status = _verify(conn, monkeypatch, [PYTEST_SKIP, WIDE_PASS])
    assert (passed, status) == (False, "no-test-mapped")
    assert "Only project-wide gate(s) ran (irrelevant)" in out[0]["output"]


def test_the_declared_exemption_still_records_and_asks_for_the_ack(conn, monkeypatch):
    passed, _out, status = _verify(
        conn, monkeypatch, [PYTEST_SKIP, WIDE_PASS], no_tests_expected=True
    )
    assert (passed, status) == (True, "no-tests-declared")
    row = conn.execute("SELECT no_tests_declared FROM verification_runs").fetchone()
    assert row[0] == 1


def test_a_run_where_a_scoped_gate_ran_is_still_green(conn, monkeypatch):
    passed, _out, status = _verify(conn, monkeypatch, [PYTEST_SKIP, WIDE_PASS, RUFF_PASS])
    assert passed is True
    assert status not in ("no-test-mapped", "no-tests-declared")


def test_run_gates_stamps_every_result_with_its_scope(monkeypatch):
    gates = [
        {"name": "wide", "severity": "block", "command": "python -c pass"},
        {"name": "scoped", "severity": "block", "command": "x {files}", "file_extensions": [".md"]},
    ]
    monkeypatch.setattr(gate_runner, "load_config", lambda: {})
    monkeypatch.setattr(gate_runner, "get_gates_for_trigger", lambda *_a: gates)
    monkeypatch.setattr(gate_runner, "gate_applies_to", lambda *_a: True)
    monkeypatch.setattr(gate_runner, "impl_for", lambda _n: None)
    _passed, results = _REAL_RUN_GATES("verify", DECLARED)
    assert {r["name"]: r["file_scoped"] for r in results} == {"wide": False, "scoped": True}
