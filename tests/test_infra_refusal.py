"""An infrastructure failure refuses loudly, with its own code (github#109).

fail-closed-covers-policy-but-not-infrastructure. Each point verification
depends on is made unavailable here, and the verdict must be red and say
INFRASTRUCTURE plus the code — a reader must see "fix the environment", not
"fix the code". Before 1.10 a signing failure with a key configured printed a
WARNING and left the run green and closable.
"""

from __future__ import annotations

import sqlite3

import pytest

import gate_runner
import infra_refusal
import service_verification as sv
import verify_receipt_emit
from conftest import VERIFICATION_RUNS_DDL

GREEN = [
    {"name": "pytest", "severity": "block", "outcome": "PASSED", "passed": True, "skipped": False}
]


@pytest.fixture
def conn(tmp_path, monkeypatch):
    from backend_schema_gate_runs import GATE_RUNS_SQL

    monkeypatch.setattr(
        "project_config.load_config", lambda: {"verify_pipeline_timeout_seconds": 0}
    )
    monkeypatch.setattr(gate_runner, "run_gates", lambda *_a, **_k: (True, GREEN))
    c = sqlite3.connect(str(tmp_path / "t.db"))
    c.row_factory = sqlite3.Row
    c.executescript(VERIFICATION_RUNS_DDL)
    c.executescript(GATE_RUNS_SQL)
    yield c
    c.close()


def _verify(conn):
    return sv.run_gates_with_cache(conn, "t", ["scripts/x.py"], scope="manual", trigger="verify")


def test_signer_unavailable_turns_the_run_red(conn, monkeypatch):
    """NEGATIVE — red before the fix: a key exists and signing fails."""
    monkeypatch.setattr(
        verify_receipt_emit,
        "emit_signed_receipt",
        lambda *a, **k: (verify_receipt_emit.STATUS_ERROR, "fp"),
    )
    passed, results, status = _verify(conn)
    assert (passed, status) == (False, "signer-unavailable")
    assert results[-1]["output"].startswith("INFRASTRUCTURE: SIGNER_UNAVAILABLE")


def test_receipt_persistence_unavailable_is_named(conn, monkeypatch):
    import verify_run_record

    def _boom(*a, **k):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(verify_run_record, "record_run", _boom)
    passed, results, status = _verify(conn)
    assert passed is False and status == verify_run_record.RECORD_FAILED_STATUS
    assert infra_refusal.RECEIPT_PERSISTENCE_UNAVAILABLE in results[-1]["output"]


@pytest.mark.verify_first
def test_policy_profile_unavailable_is_named(monkeypatch):
    from service_gates import GatesMixin

    def _boom(*a, **k):
        raise RuntimeError("config exploded")

    monkeypatch.setattr("project_config.load_config", _boom)
    report = {"passed": True, "blocking_failures": []}
    GatesMixin._enforce_verify_first(GatesMixin.__new__(GatesMixin), report, "s", ["a.py"])
    assert report["passed"] is False
    assert "INFRASTRUCTURE: POLICY_PROFILE_UNAVAILABLE" in str(report["blocking_failures"])


def test_a_keyless_project_is_not_an_infrastructure_failure(conn, monkeypatch):
    """NEGATIVE: no key at all is a choice, not a fault — the run stays green."""
    monkeypatch.setattr(
        verify_receipt_emit,
        "emit_signed_receipt",
        lambda *a, **k: (verify_receipt_emit.STATUS_NO_KEY, None),
    )
    passed, _results, status = _verify(conn)
    assert passed is True and status != "signer-unavailable"
