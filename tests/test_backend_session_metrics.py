"""Tests for backend_session_metrics — bounded inter-tool-call deltas (clip semantics)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from backend_session_metrics import (
    DEFAULT_IDLE_THRESHOLD_MINUTES,
    DEFAULT_IDLE_THRESHOLD_SECONDS,
    compute_active_minutes,
    compute_active_seconds,
    recompute_all_sessions,
)
from project_backend import SQLiteBackend


@pytest.fixture
def be(tmp_path):
    b = SQLiteBackend(str(tmp_path / "metrics.db"))
    yield b
    b.close()


def _add_session(be, started_at, ended_at=None):
    cur = be._conn.execute(
        "INSERT INTO sessions(started_at, ended_at) VALUES (?, ?)",
        (started_at, ended_at),
    )
    be._conn.commit()
    return cur.lastrowid


def _add_event(be, ts):
    be._conn.execute(
        "INSERT INTO events(entity_type, entity_id, action, created_at) "
        "VALUES ('test', 'x', 'tick', ?)",
        (ts,),
    )
    be._conn.commit()


class TestComputeActiveMinutes:
    def test_empty_session_returns_zero(self, be):
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T11:00:00Z")
        assert compute_active_minutes(be._q, be._q1, sid) == 0

    def test_single_event_returns_zero(self, be):
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T11:00:00Z")
        _add_event(be, "2026-04-25T10:30:00Z")
        assert compute_active_minutes(be._q, be._q1, sid) == 0

    def test_all_active_intervals_summed(self, be):
        # 5 events, 5-minute gaps, all under 10-min threshold → 4 gaps × 5 = 20 min
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T11:00:00Z")
        for ts in (
            "2026-04-25T10:00:00Z",
            "2026-04-25T10:05:00Z",
            "2026-04-25T10:10:00Z",
            "2026-04-25T10:15:00Z",
            "2026-04-25T10:20:00Z",
        ):
            _add_event(be, ts)
        assert compute_active_minutes(be._q, be._q1, sid) == 20

    def test_gap_above_threshold_clipped_not_excluded(self, be):
        # v14b-session-active-time: clip semantics — long AFK gap contributes
        # exactly threshold (10 min), not 0. Active 5 min → 30 min AFK (clipped
        # to 10) → active 5 min == 20 min total, not 10.
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T12:00:00Z")
        for ts in (
            "2026-04-25T10:00:00Z",
            "2026-04-25T10:05:00Z",
            "2026-04-25T10:35:00Z",  # 30-min gap → clipped to 10
            "2026-04-25T10:40:00Z",
        ):
            _add_event(be, ts)
        assert compute_active_minutes(be._q, be._q1, sid) == 20

    def test_custom_threshold(self, be):
        # 8-min gap: included with threshold=10, clipped with threshold=5
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T11:00:00Z")
        _add_event(be, "2026-04-25T10:00:00Z")
        _add_event(be, "2026-04-25T10:08:00Z")
        assert compute_active_minutes(be._q, be._q1, sid, idle_threshold_minutes=10) == 8
        # clip: 8-min gap exceeds 5-min threshold → contributes exactly 5 min
        assert compute_active_minutes(be._q, be._q1, sid, idle_threshold_minutes=5) == 5

    def test_open_session_uses_now_as_upper_bound(self, be):
        # Session never ended — should still compute against existing events
        sid = _add_session(be, "2026-04-25T10:00:00Z", None)
        _add_event(be, "2026-04-25T10:00:00Z")
        _add_event(be, "2026-04-25T10:03:00Z")
        # 3-min gap, under default threshold
        assert compute_active_minutes(be._q, be._q1, sid) == 3

    def test_negative_threshold_returns_zero(self, be):
        sid = _add_session(be, "2026-04-25T10:00:00Z", None)
        _add_event(be, "2026-04-25T10:00:00Z")
        _add_event(be, "2026-04-25T10:05:00Z")
        assert compute_active_minutes(be._q, be._q1, sid, idle_threshold_minutes=-1) == 0
        assert compute_active_minutes(be._q, be._q1, sid, idle_threshold_minutes=0) == 0

    def test_unknown_session_returns_zero(self, be):
        assert compute_active_minutes(be._q, be._q1, 999999) == 0

    def test_default_threshold_constant(self):
        assert DEFAULT_IDLE_THRESHOLD_MINUTES == 10
        assert DEFAULT_IDLE_THRESHOLD_SECONDS == 600


class TestComputeActiveSeconds:
    """v14b-session-active-time: AC scenarios + negative scenarios for clip semantics."""

    def test_ac_a_short_session_no_afk(self, be):
        # AC scenario (a): 5 events 5-min apart, all under threshold → 4 × 300s = 1200s
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T11:00:00Z")
        for ts in (
            "2026-04-25T10:00:00Z",
            "2026-04-25T10:05:00Z",
            "2026-04-25T10:10:00Z",
            "2026-04-25T10:15:00Z",
            "2026-04-25T10:20:00Z",
        ):
            _add_event(be, ts)
        assert compute_active_seconds(be._q, be._q1, sid) == 1200

    def test_ac_b_30min_gap_clipped_to_threshold(self, be):
        # AC scenario (b): 5 + 30(clip→10) + 5 = 20 min = 1200s
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T12:00:00Z")
        for ts in (
            "2026-04-25T10:00:00Z",
            "2026-04-25T10:05:00Z",
            "2026-04-25T10:35:00Z",
            "2026-04-25T10:40:00Z",
        ):
            _add_event(be, ts)
        assert compute_active_seconds(be._q, be._q1, sid) == 1200

    def test_ac_c_active_180min_triggers_warning(self, be):
        # AC scenario (c): 36 events 5-min apart → 35 × 300s = 10500s = 175 min
        # Add one more 5-min gap to push to 180 min = 10800s
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T13:30:00Z")
        # Generate 37 events at 5-minute intervals → 36 gaps × 5min = 180min
        from datetime import datetime, timedelta, timezone

        start = datetime(2026, 4, 25, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(37):
            ts = (start + timedelta(minutes=5 * i)).strftime("%Y-%m-%dT%H:%M:%SZ")
            _add_event(be, ts)
        assert compute_active_seconds(be._q, be._q1, sid) == 180 * 60

    def test_negative_a_no_events_returns_zero(self, be):
        # Negative (a): no tool-call events at all → 0 (not None, not NaN)
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T11:00:00Z")
        result = compute_active_seconds(be._q, be._q1, sid)
        assert result == 0
        assert isinstance(result, int)

    def test_negative_b_long_afk_keeps_active_low(self, be):
        # Negative (b): wall ≈ 200 min, only one big AFK gap
        # → 5min work + 195min AFK(clipped to 10min) = 15 min active, well under 180
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T13:20:00Z")
        for ts in (
            "2026-04-25T10:00:00Z",
            "2026-04-25T10:05:00Z",  # 5 min work
            "2026-04-25T13:20:00Z",  # 195-min gap → clipped to 10
        ):
            _add_event(be, ts)
        active = compute_active_seconds(be._q, be._q1, sid)
        # 5 min real + 10 min clipped = 15 min = 900s
        assert active == 900
        assert active < 180 * 60  # Rule 9.2 not triggered

    def test_negative_c_corrupt_timestamps_best_effort(self, be):
        # Negative (c): non-monotonic timestamps shouldn't crash; valid pairs sum.
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T11:00:00Z")
        for ts in (
            "2026-04-25T10:00:00Z",
            "2026-04-25T10:05:00Z",  # +5 min
            "2026-04-25T10:03:00Z",  # NON-MONOTONIC: backward 2 min → ignored
            "2026-04-25T10:10:00Z",  # +7 min from prev (10:03)
        ):
            _add_event(be, ts)
        # Events come back in created_at order via window function: 10:00, 10:03,
        # 10:05, 10:10. Gaps: 3, 2, 5 → all under threshold → 10 min = 600s.
        # Test asserts the function returns a sane non-negative int (no crash).
        result = compute_active_seconds(be._q, be._q1, sid)
        assert isinstance(result, int)
        assert result >= 0
        assert result <= 600  # at most sum of valid gaps under threshold

    def test_returns_seconds_not_minutes(self, be):
        # 90-second gap → 90 seconds, not rounded to 1 or 2 minutes
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T11:00:00Z")
        _add_event(be, "2026-04-25T10:00:00Z")
        _add_event(be, "2026-04-25T10:01:30Z")
        result = compute_active_seconds(be._q, be._q1, sid)
        assert 89 <= result <= 91  # rounding tolerance

    def test_minutes_wrapper_rounds_seconds(self, be):
        # 90 seconds → 1 min (round, not floor)
        # 150 seconds → 2 min (round 2.5 → banker's rounding → 2)
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T11:00:00Z")
        _add_event(be, "2026-04-25T10:00:00Z")
        _add_event(be, "2026-04-25T10:01:30Z")  # 90s
        assert compute_active_minutes(be._q, be._q1, sid) == 2  # 90/60 = 1.5 → 2

    def test_unknown_session_seconds_returns_zero(self, be):
        assert compute_active_seconds(be._q, be._q1, 999999) == 0

    def test_negative_threshold_seconds_returns_zero(self, be):
        sid = _add_session(be, "2026-04-25T10:00:00Z", None)
        _add_event(be, "2026-04-25T10:00:00Z")
        _add_event(be, "2026-04-25T10:05:00Z")
        assert compute_active_seconds(be._q, be._q1, sid, idle_threshold_minutes=0) == 0
        assert compute_active_seconds(be._q, be._q1, sid, idle_threshold_minutes=-1) == 0


class TestRecomputeAllSessions:
    def test_empty_db_returns_empty_list(self, be):
        assert recompute_all_sessions(be._q, be._q1) == []

    def test_returns_one_row_per_session_oldest_first(self, be):
        sid1 = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T10:30:00Z")
        sid2 = _add_session(be, "2026-04-25T11:00:00Z", "2026-04-25T11:30:00Z")
        out = recompute_all_sessions(be._q, be._q1)
        assert [r["id"] for r in out] == [sid1, sid2]

    def test_afk_pct_computed_when_wall_positive(self, be):
        # Session 60 min wall, but events span 10 min active
        _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T11:00:00Z")
        _add_event(be, "2026-04-25T10:00:00Z")
        _add_event(be, "2026-04-25T10:05:00Z")
        _add_event(be, "2026-04-25T10:10:00Z")
        out = recompute_all_sessions(be._q, be._q1)
        assert len(out) == 1
        row = out[0]
        assert row["wall_minutes"] == 60
        assert row["active_minutes"] == 10
        assert row["active_seconds"] == 600
        assert row["afk_pct"] == round(1 - 10 / 60, 3)

    def test_afk_pct_none_when_wall_zero(self, be):
        # started_at == ended_at → wall=0, afk_pct undefined
        _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T10:00:00Z")
        out = recompute_all_sessions(be._q, be._q1)
        assert out[0]["afk_pct"] is None

    def test_open_session_wall_uses_now(self, be):
        # Open session's wall_minutes should be > 0 (from started_at to now)
        _add_session(be, "2026-04-25T10:00:00Z", None)
        out = recompute_all_sessions(be._q, be._q1)
        assert out[0]["wall_minutes"] > 0
