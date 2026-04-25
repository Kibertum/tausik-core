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


# === CLI output smoke ===


class TestCliMetricsOutput:
    def test_per_tier_in_metrics_output(self, be, tmp_path, capsys, monkeypatch):
        from project_cli_ops import cmd_metrics
        from project_service import ProjectService

        _seed(be, "t1", tier="light", budget=20, actual=18)
        svc = ProjectService(be)
        cmd_metrics(svc, args=None)
        captured = capsys.readouterr().out
        assert "Per-tier" in captured
        assert "light" in captured
