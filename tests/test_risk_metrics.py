"""Tests for scripts/risk_metrics.py (v15-risk-surface-metrics)."""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest
from conftest import canonical_ddl

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from risk_metrics import (  # noqa: E402
    format_risk_section,
    format_risk_status_line,
    risk_summary,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute(canonical_ddl("tasks"))
    yield c
    c.close()


def _seed(conn, rows):
    """rows: [(slug, risk_score, completed_at)].

    Колонки перечислены поимённо: позиционный INSERT привязывался бы к порядку
    колонок канона и молча разъезжался бы при вставке новой.
    """
    conn.executemany(
        "INSERT INTO tasks (slug, title, risk_score, completed_at, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
        [(slug, slug, score, done) for slug, score, done in rows],
    )
    conn.commit()


class TestSummary:
    def test_empty_returns_none(self, conn):
        assert risk_summary(conn) is None

    def test_unscored_rows_ignored(self, conn):
        _seed(conn, [("t1", None, "2026-01-01")])
        assert risk_summary(conn) is None

    def test_aggregation(self, conn):
        _seed(
            conn,
            [
                ("low1", 0.1, "2026-01-01"),
                ("med1", 0.4, "2026-01-02"),
                ("high1", 0.7, "2026-01-03"),
                ("high2", 0.9, "2026-01-04"),
                ("unscored", None, "2026-01-05"),
            ],
        )
        s = risk_summary(conn)
        assert s["count"] == 4
        assert s["avg"] == pytest.approx(0.525)
        assert s["distribution"] == {"low": 1, "medium": 1, "high": 2}
        # newest first
        assert [h["slug"] for h in s["recent_high"]] == ["high2", "high1"]

    def test_boundaries_escalate(self, conn):
        _seed(conn, [("b1", 0.33, "x"), ("b2", 0.66, "y")])
        s = risk_summary(conn)
        assert s["distribution"] == {"low": 0, "medium": 1, "high": 1}

    def test_high_limit(self, conn):
        _seed(conn, [(f"h{i}", 0.8, f"2026-01-{i:02d}") for i in range(1, 9)])
        s = risk_summary(conn, high_limit=3)
        assert len(s["recent_high"]) == 3


class TestFormatting:
    def _summary(self, conn):
        _seed(conn, [("ok", 0.2, "a"), ("bad", 0.8, "b")])
        return risk_summary(conn)

    def test_section(self, conn):
        text = format_risk_section(self._summary(conn))
        assert "Closure Risk" in text
        assert "low=1" in text and "high=1" in text
        assert "bad (0.8)" in text

    def test_status_line(self, conn):
        line = format_risk_status_line(self._summary(conn))
        assert line.startswith("Risk: avg 0.5 over 2 closes")
        assert "1 high" in line

    def test_status_line_no_high(self, conn):
        _seed(conn, [("ok", 0.2, "a")])
        line = format_risk_status_line(risk_summary(conn))
        assert "high" not in line
