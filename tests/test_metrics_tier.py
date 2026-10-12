"""Tests for per-tier metrics + calibration drift."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend


@pytest.fixture
def be(tmp_path):
    b = SQLiteBackend(str(tmp_path / "metrics.db"))
    yield b
    b.close()


def _seed(
    be,
    slug: str,
    *,
    tier: str | None = None,
    budget: int | None = None,
    actual: int | None = None,
    attempts: int = 1,
    completed: bool = True,
) -> None:
    if not be.epic_get("e"):
        be.epic_add("e", "Epic")
        be.story_add("e", "s", "Story")
    be.task_add("s", slug, "T", goal="g", role="developer")
    fields = {"attempts": attempts}
    if completed:
        fields.update(status="done", completed_at="2026-04-25T10:00:00Z")
    if tier is not None:
        fields["tier"] = tier
    if budget is not None:
        fields["call_budget"] = budget
    if actual is not None:
        fields["call_actual"] = actual
    be.task_update(slug, **fields)


# === Per-tier metrics ===


class TestPerTier:
    def test_empty_db_returns_empty_dict(self, be):
        m = be.get_metrics()
        assert m["per_tier"] == {}

    def test_single_tier(self, be):
        _seed(be, "t1", tier="light", budget=20, actual=18)
        out = be.get_metrics()["per_tier"]
        assert "light" in out
        d = out["light"]
        assert d["count"] == 1
        assert d["avg_budget"] == 20.0
        assert d["avg_actual"] == 18.0
        assert d["fpsr_pct"] == 100.0
        assert d["ratio_actual_over_budget"] == 0.9

    def test_legacy_tasks_bucketed_as_unset(self, be):
        # epic + story exist after first _seed; second _seed re-runs epic_add but
        # add ignores duplicates here? Use direct task_add via existing setup.
        _seed(be, "t1", tier="light", budget=10, actual=10)
        be.task_add("s", "t2", "Legacy", goal="g", role="developer")
        be.task_update("t2", status="done", completed_at="2026-04-25T10:01:00Z")
        out = be.get_metrics()["per_tier"]
        assert out["light"]["count"] == 1
        assert "unset" in out
        assert out["unset"]["count"] == 1
        assert out["unset"]["avg_budget"] is None
        assert out["unset"]["avg_actual"] is None

    def test_fpsr_per_tier(self, be):
        # one trivial first-pass, one trivial retry → 50% fpsr
        _seed(be, "t1", tier="trivial", budget=5, actual=4, attempts=1)
        be.task_add("s", "t2", "T2", goal="g", role="developer")
        be.task_update(
            "t2",
            tier="trivial",
            call_budget=5,
            call_actual=8,
            attempts=3,
            status="done",
            completed_at="2026-04-25T10:00:00Z",
        )
        out = be.get_metrics()["per_tier"]
        assert out["trivial"]["count"] == 2
        assert out["trivial"]["fpsr_pct"] == 50.0


# === Calibration drift ===


class TestCalibrationDrift:
    def test_none_when_too_few_measured(self, be):
        for i in range(3):
            _seed(be, f"t{i}", tier="light", budget=10, actual=10)
        m = be.get_metrics()
        assert m["calibration_drift"] is None

    def test_calibrated_label(self, be):
        for i in range(6):
            _seed(be, f"t{i}", tier="light", budget=10, actual=10)
        d = be.get_metrics()["calibration_drift"]
        assert d is not None
        assert d["label"] == "calibrated"
        assert d["avg_ratio"] == 1.0
        assert d["samples"] == 6

    def test_underestimating(self, be):
        # actual >> budget for 5+ tasks
        for i in range(5):
            _seed(be, f"t{i}", tier="moderate", budget=10, actual=20)
        d = be.get_metrics()["calibration_drift"]
        assert d["label"] == "underestimating"
        assert d["avg_ratio"] >= 1.5

    def test_overestimating(self, be):
        for i in range(5):
            _seed(be, f"t{i}", tier="deep", budget=200, actual=80)
        d = be.get_metrics()["calibration_drift"]
        assert d["label"] == "overestimating"
        assert d["avg_ratio"] <= 0.5

    def test_skips_tasks_without_actual(self, be):
        # 4 tasks with budget+actual + 5 budget-only tasks → only 4 measured
        for i in range(4):
            _seed(be, f"t{i}", tier="light", budget=10, actual=10)
        for i in range(5):
            _seed(be, f"u{i}", tier="light", budget=10)
        m = be.get_metrics()
        assert m["calibration_drift"] is None  # only 4 measured < 5 threshold


# === Budget calibration (tier thresholds vs measured p50 actuals) ===


class TestBudgetCalibration:
    @pytest.mark.parametrize(
        ("upper", "actuals", "expected_verdict"),
        [
            (9, [10] * 5, "starved"),  # bound below p50 blocks half of real work
            (10, [10] * 5, "ok"),  # upper == p50 is not starved
            (20, [10] * 5, "ok"),  # 2x cushion still constrains
            (30, [10] * 5, "ok"),  # exactly factor x p50 stays ok
            (31, [10] * 5, "decorated"),  # beyond factor x p50 only labels
        ],
    )
    def test_verdict_against_p50(self, upper, actuals, expected_verdict):
        from backend_tier_metrics import budget_calibration_check

        rows = [{"tier": "light", "b": None, "a": a, "attempts": 1} for a in actuals]
        out = budget_calibration_check(lambda sql, params=(): rows, thresholds=((upper, "light"),))
        assert out["tiers"]["light"]["verdict"] == expected_verdict

    def test_starved_wins_the_status_over_decorated(self):
        from backend_tier_metrics import budget_calibration_check

        rows = [{"tier": "light", "b": None, "a": 10, "attempts": 1}] * 5 + [
            {"tier": "deep", "b": None, "a": 5, "attempts": 1}
        ] * 5
        out = budget_calibration_check(
            lambda sql, params=(): rows,
            thresholds=((9, "light"), (200, "deep")),
        )
        assert out["status"] == "starved"  # blocking real work outranks decoration
        assert out["tiers"]["deep"]["verdict"] == "decorated"

    @pytest.mark.parametrize(
        ("rows", "why"),
        [
            ([{"tier": "light", "b": 20, "a": None, "attempts": 1}] * 5, "no actuals"),
            ([{"tier": "light", "b": 20, "a": 10, "attempts": 1}] * 4, "n below 5"),
        ],
    )
    def test_unmeasured_corpuses_return_none(self, rows, why):
        from backend_tier_metrics import budget_calibration_check

        out = budget_calibration_check(lambda sql, params=(): rows, thresholds=((24, "light"),))
        assert out is None  # a corpus with no measured tier earns no verdict


# === CLI output smoke ===


class TestCliMetricsOutput:
    def test_per_tier_in_metrics_output(self, be, tmp_path, capsys, monkeypatch):
        from project_cli_metrics import cmd_metrics
        from project_service import ProjectService

        _seed(be, "t1", tier="light", budget=20, actual=18)
        svc = ProjectService(be)
        cmd_metrics(svc, args=None)
        captured = capsys.readouterr().out
        assert "Per-tier" in captured
        assert "light" in captured

    def test_budget_calibration_section_in_metrics_output(self, be, capsys):
        from project_cli_metrics import cmd_metrics
        from project_service import ProjectService

        # 5 light tasks → p50 actual 12; light upper 33 sits under the 3.0x
        # ceiling (36) and above p50 → the only measured tier is "ok".
        for i in range(5):
            _seed(be, f"t{i}", tier="light", budget=33, actual=12)
        svc = ProjectService(be)
        cmd_metrics(svc, args=None)
        captured = capsys.readouterr().out
        assert "Budget calibration: ok" in captured
        assert "light" in captured


def test_calibration_is_the_median_of_the_last_30_with_its_spread():
    """calibration-window-too-small-to-forecast: the backtest winner, not the mean of 10."""
    from backend_tier_metrics import calibration_drift

    # 40 closures, oldest first: 10 wild ones (ratio 5.0) older than the last 30.
    ratios = [5.0] * 10 + [0.5] * 15 + [1.0] * 15
    rows = [{"b": 10, "a": r * 10} for r in reversed(ratios)]  # newest first, as the SQL returns

    def q(sql, params=()):
        assert "LIMIT 30" in sql
        return rows[:30]

    drift = calibration_drift(q)
    assert drift["samples"] == 30
    assert drift["avg_ratio"] == 0.75  # median of fifteen 0.5 and fifteen 1.0
    assert (drift["p25"], drift["p75"]) == (0.5, 1.0)


def test_fewer_than_five_samples_still_give_no_coefficient():
    from backend_tier_metrics import calibration_drift

    assert calibration_drift(lambda sql, params=(): [{"b": 1, "a": 1}] * 4) is None
