"""Tests for scripts/nudge_escalation.py (v15p-escalating-nudges).

Covers the four escalation levels at their boundaries, per-invariant counter
persistence in the meta table, reset-on-compliance, config threshold overrides,
and the never-raise contract on malformed input.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import nudge_escalation as n  # noqa: E402


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    yield c
    c.close()


class TestLevelForCount:
    @pytest.mark.parametrize(
        "count,expected",
        [
            (0, n.SILENT),
            (1, n.HINT),
            (2, n.HINT),
            (3, n.WARNING),
            (4, n.WARNING),
            (5, n.STRONG),
            (50, n.STRONG),
        ],
    )
    def test_default_threshold_boundaries(self, count, expected):
        assert n.level_for_count(count) == expected

    def test_custom_thresholds(self):
        t = {"hint": 2, "warning": 4, "strong": 6}
        assert n.level_for_count(1, t) == n.SILENT
        assert n.level_for_count(2, t) == n.HINT
        assert n.level_for_count(4, t) == n.WARNING
        assert n.level_for_count(6, t) == n.STRONG


class TestRenderNudge:
    def test_silent_is_empty(self):
        assert n.render_nudge("do the thing", n.SILENT, 0) == ""

    def test_each_level_distinct_text(self):
        hint = n.render_nudge("log your work", n.HINT, 1)
        warn = n.render_nudge("log your work", n.WARNING, 3)
        strong = n.render_nudge("log your work", n.STRONG, 5)
        assert hint != warn != strong
        assert "log your work" in hint and "log your work" in warn and "log your work" in strong
        assert "ⓘ" in hint
        assert "⚠" in warn and "#3" in warn
        assert "‼" in strong and "5×" in strong

    def test_unknown_level_is_empty(self):
        assert n.render_nudge("x", 99, 1) == ""


class TestCounterPersistence:
    def test_peek_unseen_is_zero(self, conn):
        assert n.peek(conn, "journaling") == 0

    def test_bump_increments(self, conn):
        assert n.bump(conn, "journaling") == 1
        assert n.bump(conn, "journaling") == 2
        assert n.peek(conn, "journaling") == 2

    def test_counters_are_per_invariant(self, conn):
        n.bump(conn, "journaling")
        n.bump(conn, "checkpoint")
        n.bump(conn, "checkpoint")
        assert n.peek(conn, "journaling") == 1
        assert n.peek(conn, "checkpoint") == 2

    def test_reset_clears(self, conn):
        n.bump(conn, "journaling")
        n.bump(conn, "journaling")
        n.reset(conn, "journaling")
        assert n.peek(conn, "journaling") == 0
        # After reset the next breach starts the escalation over.
        assert n.bump(conn, "journaling") == 1


class TestResolveThresholds:
    def test_default_when_no_config(self):
        assert n.resolve_thresholds("journaling", None) == n.DEFAULT_THRESHOLDS

    def test_invariant_override(self):
        cfg = {"nudge": {"thresholds": {"journaling": {"hint": 2, "strong": 9}}}}
        t = n.resolve_thresholds("journaling", cfg)
        assert t["hint"] == 2
        assert t["strong"] == 9
        assert t["warning"] == n.DEFAULT_THRESHOLDS["warning"]  # untouched merges default

    def test_specific_overrides_default_block(self):
        cfg = {
            "nudge": {
                "thresholds": {
                    "default": {"hint": 5},
                    "checkpoint": {"hint": 2},
                }
            }
        }
        assert n.resolve_thresholds("checkpoint", cfg)["hint"] == 2
        assert n.resolve_thresholds("other", cfg)["hint"] == 5

    def test_malformed_config_yields_defaults(self):
        # NEGATIVE: non-dict / wrong-typed config must not raise.
        assert n.resolve_thresholds("x", {"nudge": "oops"}) == n.DEFAULT_THRESHOLDS
        assert (
            n.resolve_thresholds("x", {"nudge": {"thresholds": {"x": {"hint": "no"}}}})["hint"]
            == n.DEFAULT_THRESHOLDS["hint"]
        )
        assert (
            n.resolve_thresholds("x", {"nudge": {"thresholds": {"x": {"hint": -3}}}})["hint"]
            == n.DEFAULT_THRESHOLDS["hint"]
        )


class TestEscalate:
    def test_silent_until_first_threshold(self, conn):
        # With hint=2, the first breach is still silent.
        cfg = {"nudge": {"thresholds": {"journaling": {"hint": 2}}}}
        assert n.escalate(conn, "journaling", "log it", cfg) == ""
        assert "ⓘ" in n.escalate(conn, "journaling", "log it", cfg)

    def test_escalates_then_resets(self, conn):
        for _ in range(5):
            out = n.escalate(conn, "checkpoint", "checkpoint now")
        assert "‼" in out  # reached STRONG at count 5
        n.reset(conn, "checkpoint")
        # Escalation restarts: next breach is count 1 → HINT (not STRONG).
        restarted = n.escalate(conn, "checkpoint", "checkpoint now")
        assert "ⓘ" in restarted and "‼" not in restarted

    def test_broken_conn_never_raises(self):
        bad = sqlite3.connect(":memory:")  # no meta table
        # Must not raise; bump falls back to 0 → silent.
        assert n.escalate(bad, "journaling", "log it") == ""
        bad.close()
