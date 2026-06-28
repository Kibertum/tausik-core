"""Tests for threshold-gated FTS optimize on session end (v15p-fts-optimize-cron)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402

_KEY = "fts.last_optimize_events"


def _backend(tmp_path) -> SQLiteBackend:
    return SQLiteBackend(str(tmp_path / "t.db"))


def _bump_events(be: SQLiteBackend, n: int) -> None:
    for i in range(n):
        be.event_add("test", str(i), "noise")


class TestFtsMaybeOptimize:
    def test_below_threshold_skips(self, tmp_path):
        be = _backend(tmp_path)
        _bump_events(be, 3)
        res = be.fts_maybe_optimize(threshold=100)
        assert res["optimized"] is False
        assert res["events_delta"] < 100
        assert be.meta_get(_KEY) is None  # baseline untouched

    def test_at_threshold_optimizes_and_records_baseline(self, tmp_path):
        be = _backend(tmp_path)
        _bump_events(be, 12)
        res = be.fts_maybe_optimize(threshold=10)
        assert res["optimized"] is True
        assert res["events_delta"] >= 10
        assert all(v == "ok" for v in res["results"].values())
        # Baseline persisted = current event count.
        baseline = int(be.meta_get(_KEY))
        current = be._q("SELECT count(*) AS c FROM events")[0]["c"]
        assert baseline == current

    def test_optimize_logs_audit_event(self, tmp_path):
        be = _backend(tmp_path)
        _bump_events(be, 12)
        before = be._q("SELECT count(*) AS c FROM events WHERE action='optimize'")[0]["c"]
        be.fts_maybe_optimize(threshold=10)
        after = be._q("SELECT count(*) AS c FROM events WHERE action='optimize'")[0]["c"]
        assert after == before + 1

    def test_second_call_after_optimize_is_below_threshold(self, tmp_path):
        be = _backend(tmp_path)
        _bump_events(be, 12)
        assert be.fts_maybe_optimize(threshold=10)["optimized"] is True
        # No new churn → next call skips (delta resets via baseline).
        res2 = be.fts_maybe_optimize(threshold=10)
        assert res2["optimized"] is False

    def test_corrupt_baseline_does_not_crash(self, tmp_path):
        be = _backend(tmp_path)
        be.meta_set(_KEY, "not-a-number")
        _bump_events(be, 12)
        res = be.fts_maybe_optimize(threshold=10)  # treats baseline as 0, no crash
        assert res["optimized"] is True

    def test_negative_delta_rebaselines_without_firing(self, tmp_path):
        # Baseline ahead of current (events shrank via vacuum/replace) → reset, no fire.
        be = _backend(tmp_path)
        _bump_events(be, 2)
        be.meta_set(_KEY, "9999")  # pretend a much higher prior count
        res = be.fts_maybe_optimize(threshold=10)
        assert res["optimized"] is False
        assert res["events_delta"] < 0
        # Baseline re-anchored to current count → next call computes a sane delta.
        current = be._q("SELECT count(*) AS c FROM events")[0]["c"]
        assert int(be.meta_get(_KEY)) == current
