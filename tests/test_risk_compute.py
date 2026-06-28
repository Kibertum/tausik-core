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
        conn.execute(
            "CREATE TABLE verification_runs (id INTEGER PRIMARY KEY, task_slug TEXT, "
            "ran_at TEXT, receipt_json TEXT)"
        )
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
        conn.execute(
            "CREATE TABLE verification_runs (id INTEGER PRIMARY KEY, task_slug TEXT, "
            "ran_at TEXT, receipt_json TEXT)"
        )
        monkeypatch.setattr(rc, "_git_numstat_lines", lambda *_a: (_ for _ in ()).throw(OSError))
        risk = rc.compute_task_risk(conn, self._task(), ["scripts/a.py"], project_dir=str(tmp_path))
        assert risk is not None
        assert "code_churn" in risk["defaulted"]


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
        assert "Risk:" in result
        task = svc.be.task_get("t-risk")
        assert task["risk_score"] is not None
        assert 0.0 <= task["risk_score"] <= 1.0
        risk = json.loads(task["risk_json"])
        assert risk["level"] in ("low", "medium", "high")
        assert risk["score"] == task["risk_score"]
        assert "Risk:" in (task["notes"] or "")

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
