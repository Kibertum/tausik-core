"""Closure-risk aggregation for metrics/status (v15-risk-surface-metrics).

Read-only over tasks.risk_score (v31). Sits next to DER/FPSR in
`tausik metrics` so quality trends and closure risk read together:
rising DER with rising avg risk = closures are getting both riskier and
leakier; rising DER with flat risk = the model is missing a factor.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from risk_model import LEVEL_HIGH, LEVEL_MEDIUM


def risk_summary(conn: sqlite3.Connection, *, high_limit: int = 5) -> dict[str, Any] | None:
    """Aggregate over scored tasks; None when nothing was ever scored."""
    rows = conn.execute("SELECT risk_score FROM tasks WHERE risk_score IS NOT NULL").fetchall()
    scores = [float(r[0]) for r in rows]
    if not scores:
        return None
    dist = {"low": 0, "medium": 0, "high": 0}
    for s in scores:
        if s >= LEVEL_HIGH:
            dist["high"] += 1
        elif s >= LEVEL_MEDIUM:
            dist["medium"] += 1
        else:
            dist["low"] += 1
    high_rows = conn.execute(
        "SELECT slug, risk_score FROM tasks WHERE risk_score >= ? "
        "ORDER BY completed_at DESC LIMIT ?",
        (LEVEL_HIGH, high_limit),
    ).fetchall()
    return {
        "count": len(scores),
        "avg": round(sum(scores) / len(scores), 4),
        "distribution": dist,
        "recent_high": [{"slug": r[0], "score": float(r[1])} for r in high_rows],
    }


def format_risk_section(summary: dict[str, Any]) -> str:
    """Multi-line block for `tausik metrics`."""
    d = summary["distribution"]
    lines = [
        "--- Closure Risk (v1.5) ---",
        f"Scored closes: {summary['count']}, avg risk: {summary['avg']}",
        f"Distribution:  low={d['low']}  medium={d['medium']}  high={d['high']}",
    ]
    if summary["recent_high"]:
        slugs = ", ".join(f"{h['slug']} ({h['score']})" for h in summary["recent_high"])
        lines.append(f"Recent high-risk: {slugs}")
    return "\n".join(lines)


def format_risk_status_line(summary: dict[str, Any]) -> str:
    """One-liner for `tausik status`."""
    d = summary["distribution"]
    line = f"Risk: avg {summary['avg']} over {summary['count']} closes"
    if d["high"]:
        line += f", {d['high']} high"
    return line
