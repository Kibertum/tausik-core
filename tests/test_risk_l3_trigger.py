"""Tests for scripts/risk_l3_trigger.py (v15-l3-risk-trigger).

AC coverage: measured-high blocks without L3 review, recorded L3 review
satisfies, defaulted-only high does NOT block, config opt-out downgrades
to warning, low/medium pass silently.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest
from conftest import canonical_ddl

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import risk_l3_trigger as t  # noqa: E402
from risk_model import compute_risk  # noqa: E402


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute(canonical_ddl("reviews"))
    yield c
    c.close()


def _risk_all_measured(value):
    return compute_risk({n: value for n in t.WEIGHTS})


class TestMeasuredScore:
    def test_all_measured(self):
        assert t.measured_score(_risk_all_measured(0.8)) == pytest.approx(0.8)

    def test_renormalized_over_measured_subset(self):
        # only gate_coverage measured (0.9): renormalized = 0.9, stored score higher
        risk = compute_risk({"gate_coverage": 0.9})
        assert t.measured_score(risk) == pytest.approx(0.9)

    def test_nothing_measured_returns_none(self):
        assert t.measured_score(compute_risk({})) is None


class TestCheckL3Required:
    def test_measured_high_without_review_blocks(self, conn):
        blocking, note = t.check_l3_required(conn, "t1", _risk_all_measured(0.9))
        assert blocking is True
        assert "review record" in note and "--type L3" in note

    def test_high_risk_note_delegates_to_external_reviewer(self, conn):
        # AC3: the remediation names the Rule 4 external reviewer subagent and
        # recommends running it on a different model.
        _, note = t.check_l3_required(conn, "t1", _risk_all_measured(0.9))
        assert "@tausik-external-reviewer" in note
        assert "separation of" in note

    def test_recorded_l3_satisfies(self, conn):
        conn.execute(
            "INSERT INTO reviews (task_slug, run_type, critical_findings, warnings, run_at) "
            "VALUES ('t1', 'L3', 0, 1, '2026-01-01')"
        )
        blocking, note = t.check_l3_required(conn, "t1", _risk_all_measured(0.9))
        assert blocking is False
        assert "satisfied" in note

    def test_lowercase_run_type_cannot_be_stored_at_all(self, conn):
        """Прежний тест здесь утверждал, что 'l3' засчитывается наравне с 'L3'.

        Он был зелёным только потому, что фикстура объявляла reviews своей
        копией БЕЗ CHECK(run_type IN ('L1','L2','L3')). На канонной схеме
        такая строка не вставляется вовсе, а argparse не пропускает lowercase
        ещё раньше (--type choices). То есть тест покрывал ветку, недостижимую
        в проде, — ровно класс «фикстура беднее прода».

        UPPER() в has_l3_review остаётся как страховка от рукописных строк, но
        поддерживаемой формой ввода lowercase не является, и тест теперь
        фиксирует ИМЕННО ЭТО.
        """
        with pytest.raises(sqlite3.IntegrityError, match="run_type"):
            conn.execute(
                "INSERT INTO reviews (task_slug, run_type, critical_findings, warnings, run_at) "
                "VALUES ('t1', 'l3', 0, 0, '2026-01-01')"
            )

    def test_canonical_l3_satisfies_via_upper(self, conn):
        """Единственная форма, которая может оказаться в БД, гейт снимает."""
        conn.execute(
            "INSERT INTO reviews (task_slug, run_type, critical_findings, warnings, run_at) "
            "VALUES ('t1', 'L3', 0, 0, '2026-01-01')"
        )
        blocking, _ = t.check_l3_required(conn, "t1", _risk_all_measured(0.9))
        assert blocking is False

    def test_defaulted_only_high_does_not_block(self, conn):
        # nothing measured -> stored score 1.0 (high) but no evidence -> pass
        risk = compute_risk({})
        assert risk["level"] == "high"
        blocking, note = t.check_l3_required(conn, "t1", risk)
        assert blocking is False and note == ""

    def test_measured_subset_with_enough_coverage_blocks(self, conn):
        # 4 of 5 measured = 0.85 weight coverage >= 0.75 -> escalate
        risk = compute_risk(
            {
                "gate_coverage": 0.9,
                "test_delta": 0.9,
                "ac_evidence": 0.9,
                "security_hits": 0.9,
            }
        )
        blocking, _ = t.check_l3_required(conn, "t1", risk)
        assert blocking is True

    def test_thin_measurement_coverage_does_not_block(self, conn):
        # ac+churn = 0.35 coverage: two weak signals, not the critical 1%
        risk = compute_risk({"ac_evidence": 1.0, "code_churn": 0.9})
        assert t.measured_score(risk) >= t.LEVEL_HIGH
        blocking, note = t.check_l3_required(conn, "t1", risk)
        assert blocking is False and note == ""

    def test_casual_close_pattern_does_not_block(self, conn):
        # source-only files + no evidence markers = {test_delta, ac_evidence,
        # security} at 0.60 coverage, measured 0.6667 — the live full-suite
        # boundary flake. Routine work must not require an L3 review.
        risk = compute_risk({"test_delta": 1.0, "ac_evidence": 1.0, "security_hits": 0.0})
        assert t.measured_score(risk) >= t.LEVEL_HIGH
        blocking, note = t.check_l3_required(conn, "t1", risk)
        assert blocking is False and note == ""

    def test_low_and_medium_pass(self, conn):
        for v in (0.1, 0.5):
            blocking, note = t.check_l3_required(conn, "t1", _risk_all_measured(v))
            assert blocking is False and note == ""

    def test_opt_out_downgrades_to_warning(self, conn, monkeypatch):
        monkeypatch.setattr(t, "_block_enabled", lambda: False)
        blocking, note = t.check_l3_required(conn, "t1", _risk_all_measured(0.9))
        assert blocking is False
        assert note.startswith("WARNING")

    def test_none_risk_passes(self, conn):
        assert t.check_l3_required(conn, "t1", None) == (False, "")

    def test_broken_db_never_raises(self):
        bad = sqlite3.connect(":memory:")  # no reviews table
        blocking, note = t.check_l3_required(bad, "t1", _risk_all_measured(0.9))
        assert blocking is False and note == ""


class TestTaskDoneIntegration:
    def test_high_risk_close_blocked_then_passes_after_review(self, tmp_path, monkeypatch):
        from project_backend import SQLiteBackend
        from project_service import ProjectService
        from tausik_utils import ServiceError

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TAUSIK_QUIET", "1")
        svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
        svc.task_add(None, "t-hot", "Hot task")
        svc.task_update(
            "t-hot",
            goal="g",
            acceptance_criteria="1. ok\n2. errors on bad input",
            scope="x.py",
        )
        svc.task_start("t-hot")

        import risk_compute

        hot = {
            "score": 0.9,
            "level": "high",
            "factors": {n: 0.9 for n in t.WEIGHTS},
            "weights": dict(t.WEIGHTS),
            "defaulted": [],
        }
        monkeypatch.setattr(risk_compute, "compute_task_risk", lambda *_a, **_k: hot)
        with pytest.raises(ServiceError, match="Under-evidenced closure"):
            svc.task_done("t-hot", None, True, True, evidence="AC verified: 1. OK 2. OK")
        assert svc.be.task_get("t-hot")["status"] == "active"  # not closed

        svc.be.review_record(task_slug="t-hot", run_type="L3", critical_findings=0)
        result = svc.task_done("t-hot", None, True, True, evidence="AC verified: 1. OK 2. OK")
        assert "completed" in result and "satisfied" in result
        assert svc.be.task_get("t-hot")["status"] == "done"


class TestTheRefusalStatesItsOwnBasis:
    """Decision #212: the block stays, but it may not claim to predict anything.

    `task done` REFUSES on this signal — it appends a blocking failure and
    returns. A refusal has to say what justifies it, and the honest answer is a
    description of the evidence, not a forecast: the backtest measured AUC
    0.4820 for the composite over 374 closures. These pin the wording so the
    older framing ("High-risk closure") cannot come back without a decision.
    """

    def test_the_message_does_not_call_the_closure_high_risk(self, conn):
        _, note = t.check_l3_required(conn, "t1", _risk_all_measured(0.9))
        assert "High-risk closure" not in note
        assert "Under-evidenced closure" in note

    def test_the_message_disclaims_prediction_and_cites_the_measurement(self, conn):
        _, note = t.check_l3_required(conn, "t1", _risk_all_measured(0.9))
        assert "NOT a prediction" in note
        assert "0.4820" in note
        assert "risk-model-backtest-2026-07" in note

    def test_the_block_is_still_on_by_default(self, conn):
        """The chosen outcome of the three, pinned.

        Lifting it would be a defensible call and this test is where that call
        would land: it fails the moment `l3_block_on_high` stops defaulting to
        blocking, so the change cannot happen by drift.
        """
        blocking, _ = t.check_l3_required(conn, "t1", _risk_all_measured(0.9))
        assert blocking is True
        assert t._block_enabled() is True

    def test_the_status_line_carries_the_same_caveat_as_task_done(self):
        """AC-6: one composite, one stated confidence, in both places it appears."""
        from risk_metrics import format_risk_status_line

        line = format_risk_status_line(
            {"avg": 0.31, "count": 374, "distribution": {"low": 300, "medium": 70, "high": 4}}
        )
        assert "descriptive, not predictive" in line

    def test_the_weight_comment_no_longer_calls_gate_coverage_the_strongest(self):
        """AC-3: the claim must not sit in the source beside the measurement refuting it."""
        import inspect

        import risk_model

        src = inspect.getsource(risk_model)
        assert "strongest closure-risk signal" not in src
        assert "0.409" in src and "0.0098" in src
