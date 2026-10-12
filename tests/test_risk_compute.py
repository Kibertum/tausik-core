"""Tests for scripts/risk_compute.py + task_done risk recording.

AC coverage (v15-risk-compute-on-done): factor collection, task_done
persists risk_score/risk_json + notes line, collection failures never
block the close.
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from conftest import canonical_ddl

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import risk_compute as rc  # noqa: E402


class TestIsTestFile:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("tests/test_x.py", True),
            ("pkg/tests/helper.py", True),
            ("scripts/test_util.py", True),
            ("scripts/util.py", False),
            ("tests\\test_win.py", True),
        ],
    )
    def test_detection(self, path, expected):
        assert rc._is_test_file(path) is expected


class TestCollector:
    def _task(self, **kw):
        base = {
            "slug": "t-risk",
            "acceptance_criteria": "1. works\n2. errors on bad input",
            "notes": "AC-1: ✓ tested via tests/test_a.py::test_ok\nAC-2: ✓ negative covered",
            "started_at": "2026-06-12T00:00:00Z",
        }
        base.update(kw)
        return base

    def test_collects_without_db_receipt_or_git(self, tmp_path, monkeypatch):
        import sqlite3

        conn = sqlite3.connect(":memory:")
        conn.execute(canonical_ddl("verification_runs"))
        monkeypatch.chdir(tmp_path)  # no git repo, no config
        risk = rc.compute_task_risk(
            conn,
            self._task(),
            ["scripts/a.py", "tests/test_a.py"],
            project_dir=str(tmp_path),
        )
        assert risk is not None
        assert 0.0 <= risk["score"] <= 1.0
        # measured: test_delta (1:1 -> 0.0), security (0.0), ac_evidence (covered)
        assert risk["factors"]["test_delta"] == 0.0
        assert risk["factors"]["security_hits"] == 0.0
        assert risk["factors"]["ac_evidence"] == 0.0
        # unmeasured factors are conservatively defaulted, not dropped
        assert "gate_coverage" in risk["defaulted"]

    def test_total_failure_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            rc, "_factor_gate_coverage", lambda *_a: (_ for _ in ()).throw(RuntimeError)
        )

        class _BoomDict(dict):
            def get(self, *_a, **_k):  # task.get explodes -> total failure path
                raise RuntimeError("boom")

        assert rc.compute_task_risk(None, _BoomDict(), []) is None  # type: ignore[arg-type]

    def test_broken_git_drops_churn_only(self, tmp_path, monkeypatch):
        import sqlite3

        conn = sqlite3.connect(":memory:")
        conn.execute(canonical_ddl("verification_runs"))
        monkeypatch.setattr(rc, "_git_numstat_lines", lambda *_a: (_ for _ in ()).throw(OSError))
        risk = rc.compute_task_risk(conn, self._task(), ["scripts/a.py"], project_dir=str(tmp_path))
        assert risk is not None
        assert "code_churn" in risk["defaulted"]


class TestGateCoverageReadsVerifyTimeCount:
    """risk-gate-coverage-configured-count-in-check: _factor_gate_coverage used to
    compare the receipt's ran-gate count (verify time) against a denominator
    recomputed from load_config() at task-done. A trust-tier flip between the two
    moments changed the denominator, making the factor machine-dependent — a
    comparison of two DIFFERENT gate sets. The count is now captured IN the signed
    receipt, so numerator and denominator come from the same verify-time source."""

    def _conn(self):
        import sqlite3

        conn = sqlite3.connect(":memory:")
        conn.execute(canonical_ddl("verification_runs"))
        return conn

    def _insert_receipt(self, conn, slug, *, ran_gate_names, configured=None):
        """Fabricate a stored envelope. The factor reads the receipt dict via
        load_receipt — it never verifies the signature — so an unsigned envelope
        with just the fields the factor reads is a faithful stand-in."""
        gates = [{"name": n, "passed": True, "severity": "block"} for n in ran_gate_names]
        receipt: dict = {"task_slug": slug, "gates": gates}
        if configured is not None:
            receipt["configured_gates_count"] = configured
        envelope = {"envelope": "tausik-signed/v1", "receipt": receipt}
        conn.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at, receipt_json) "
            "VALUES (?, 'standard', 'c', 0, 'ok', 'h', '2026-01-01T00:00:00Z', ?)",
            (slug, json.dumps(envelope)),
        )
        conn.commit()

    def test_uses_receipt_count_not_current_config(self, monkeypatch):
        """The load-bearing test: 5 gates configured at verify, 2 ran -> 0.6, and
        it stays 0.6 even though the CURRENT config would report 10. The trust-tier
        flip can no longer move the factor."""
        from project_config import get_gates_for_trigger  # noqa: F401

        conn = self._conn()
        self._insert_receipt(conn, "t", ran_gate_names=["a", "b"], configured=5)
        # If the recompute path were taken, this would drive the denominator to 10.
        monkeypatch.setattr("project_config.get_gates_for_trigger", lambda *_a, **_k: [{}] * 10)
        assert rc._factor_gate_coverage(conn, "t") == round(1.0 - 2 / 5, 4)  # 0.6

    def test_legacy_receipt_without_count_falls_back_to_recompute(self, monkeypatch):
        """NEGATIVE SCENARIO / back-compat: a pre-fix receipt has no
        configured_gates_count, so the old behavior (recompute from current
        config) is preserved rather than crashing on a missing field."""
        conn = self._conn()
        self._insert_receipt(conn, "t", ran_gate_names=["a", "b"], configured=None)
        monkeypatch.setattr("project_config.get_gates_for_trigger", lambda *_a, **_k: [{}] * 4)
        assert rc._factor_gate_coverage(conn, "t") == round(1.0 - 2 / 4, 4)  # 0.5

    def test_legacy_receipt_no_config_returns_none(self, monkeypatch):
        """Legacy receipt AND no gates configured -> None (nothing to cover), the
        exact pre-fix outcome — never a ZeroDivisionError or a None-deref."""
        conn = self._conn()
        self._insert_receipt(conn, "t", ran_gate_names=["a"], configured=None)
        monkeypatch.setattr("project_config.get_gates_for_trigger", lambda *_a, **_k: [])
        assert rc._factor_gate_coverage(conn, "t") is None

    def test_zero_or_bad_count_falls_back(self, monkeypatch):
        """A non-positive / non-int count is unusable as a denominator, so it drops
        to the recompute fallback instead of dividing by zero."""
        conn = self._conn()
        self._insert_receipt(conn, "t", ran_gate_names=["a"], configured=0)
        monkeypatch.setattr("project_config.get_gates_for_trigger", lambda *_a, **_k: [{}] * 4)
        assert rc._factor_gate_coverage(conn, "t") == round(1.0 - 1 / 4, 4)  # 0.75

    def test_no_receipt_returns_none(self):
        conn = self._conn()
        assert rc._factor_gate_coverage(conn, "ghost") is None


@pytest.fixture
def svc(tmp_path, monkeypatch):
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    monkeypatch.chdir(tmp_path)  # keep git/config lookups inside tmp
    monkeypatch.setenv("TAUSIK_QUIET", "1")
    service = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    service.task_add(None, "t-risk", "Risk task")
    service.task_update(
        "t-risk",
        goal="g",
        acceptance_criteria="1. ok\n2. errors on bad input",
        scope="x.py",
    )
    service.task_start("t-risk")
    return service


class TestTaskDoneIntegration:
    def test_done_persists_risk_and_note(self, svc):
        result = svc.task_done(
            "t-risk",
            ["scripts/a.py", "tests/test_a.py"],
            True,
            True,
            evidence="AC-1: ✓ tests/test_a.py::test_ok AC-2: ✓ negative",
        )
        # "Risk profile", not "Risk:" — the wording was demoted deliberately
        # (decision #206). The composite scores AUC 0.4820 against this project's
        # own escapes, so presenting it as a verdict at closure was a reassurance
        # nothing had earned. The caveat is asserted too: dropping it would
        # restore exactly the reading that was removed.
        assert "Risk profile:" in result
        assert "descriptive, not predictive" in result
        task = svc.be.task_get("t-risk")
        assert task["risk_score"] is not None
        assert 0.0 <= task["risk_score"] <= 1.0
        risk = json.loads(task["risk_json"])
        assert risk["level"] in ("low", "medium", "high")
        assert risk["score"] == task["risk_score"]
        assert "Risk profile:" in (task["notes"] or "")

    def test_done_survives_risk_crash(self, svc, monkeypatch):
        import risk_compute

        def _boom(*_a, **_k):
            raise RuntimeError("collector exploded")

        monkeypatch.setattr(risk_compute, "compute_task_risk", _boom)
        result = svc.task_done("t-risk", None, True, True, evidence="AC verified: 1. OK 2. OK")
        assert "completed" in result
        task = svc.be.task_get("t-risk")
        assert task["status"] == "done"
        assert task["risk_score"] is None
