"""Tests for backend_session_metrics — gap-based active time."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from backend_session_metrics import (
    DEFAULT_IDLE_THRESHOLD_MINUTES,
    compute_active_minutes,
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

    def test_gap_above_threshold_excluded(self, be):
        # Active 5 min → 30 min idle (above threshold) → active 5 min
        # Should sum to 10 min, not 40
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T12:00:00Z")
        for ts in (
            "2026-04-25T10:00:00Z",
            "2026-04-25T10:05:00Z",
            "2026-04-25T10:35:00Z",  # 30-min gap → AFK
            "2026-04-25T10:40:00Z",
        ):
            _add_event(be, ts)
        assert compute_active_minutes(be._q, be._q1, sid) == 10

    def test_custom_threshold(self, be):
        # 8-min gap: included with threshold=10, excluded with threshold=5
        sid = _add_session(be, "2026-04-25T10:00:00Z", "2026-04-25T11:00:00Z")
        _add_event(be, "2026-04-25T10:00:00Z")
        _add_event(be, "2026-04-25T10:08:00Z")
        assert (
            compute_active_minutes(be._q, be._q1, sid, idle_threshold_minutes=10) == 8
        )
        assert compute_active_minutes(be._q, be._q1, sid, idle_threshold_minutes=5) == 0

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
        assert (
            compute_active_minutes(be._q, be._q1, sid, idle_threshold_minutes=-1) == 0
        )
        assert compute_active_minutes(be._q, be._q1, sid, idle_threshold_minutes=0) == 0

    def test_unknown_session_returns_zero(self, be):
        assert compute_active_minutes(be._q, be._q1, 999999) == 0

    def test_default_threshold_constant(self):
        assert DEFAULT_IDLE_THRESHOLD_MINUTES == 10


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
