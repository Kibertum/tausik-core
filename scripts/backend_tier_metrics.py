"""Per-tier metrics + calibration drift helpers (agent-native sizing).

Extracted from backend_queries.py to keep that file under the 400-line gate.
Both functions take a callable `q` matching SQLiteBackend._q.
"""

from __future__ import annotations

from typing import Any, Callable

QueryFn = Callable[..., list[dict[str, Any]]]


def per_tier_metrics(q: QueryFn) -> dict[str, dict[str, Any]]:
    """Group done tasks by tier; emit count, avg_budget, avg_actual, fpsr."""
    out: dict[str, dict[str, Any]] = {}
    rows = q(
        "SELECT COALESCE(tier, 'unset') AS tier, COUNT(*) AS cnt, "
        "AVG(call_budget) AS avg_budget, AVG(call_actual) AS avg_actual, "
        "SUM(CASE WHEN attempts = 1 THEN 1 ELSE 0 END) AS first_pass "
        "FROM tasks WHERE status='done' "
        "GROUP BY COALESCE(tier, 'unset')"
    )
    for r in rows:
        cnt = r["cnt"] or 0
        ab, aa = r["avg_budget"], r["avg_actual"]
        ratio = round(aa / ab, 2) if ab and aa is not None and ab > 0 else None
        out[r["tier"]] = {
            "count": cnt,
            "avg_budget": round(ab, 1) if ab is not None else None,
            "avg_actual": round(aa, 1) if aa is not None else None,
            "fpsr_pct": round(r["first_pass"] / cnt * 100, 1) if cnt else 0,
            "ratio_actual_over_budget": ratio,
        }
    return out


def session_capacity_summary(
    q: QueryFn, q1: Callable[..., dict[str, Any] | None], capacity: int
) -> dict[str, Any]:
    """Per-session tool-call accounting: used, planned, remaining."""
    sess = q1(
        "SELECT id, started_at FROM sessions "
        "WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
    )
    if not sess:
        return {
            "session": None,
            "capacity": capacity,
            "used": 0,
            "planned_active": 0,
            "remaining": capacity,
        }
    used_row = q1(
        "SELECT COALESCE(SUM(call_actual),0) AS used FROM tasks "
        "WHERE status='done' AND call_actual IS NOT NULL AND completed_at >= ?",
        (sess["started_at"],),
    )
    planned_row = q1(
        "SELECT COALESCE(SUM(call_budget),0) AS planned FROM tasks "
        "WHERE status='active' AND call_budget IS NOT NULL"
    )
    used = int(used_row["used"] or 0) if used_row else 0
    planned = int(planned_row["planned"] or 0) if planned_row else 0
    return {
        "session": sess["id"],
        "capacity": capacity,
        "used": used,
        "planned_active": planned,
        "remaining": capacity - used - planned,
    }


def calibration_drift(q: QueryFn) -> dict[str, Any] | None:
    """Return drift label from last 10 measured done tasks; None if <5 samples."""
    rows = q(
        "SELECT call_budget AS b, call_actual AS a "
        "FROM tasks WHERE status='done' "
        "AND call_budget IS NOT NULL AND call_actual IS NOT NULL "
        "AND call_budget > 0 "
        "ORDER BY completed_at DESC LIMIT 10"
    )
    if len(rows) < 5:
        return None
    ratios = [r["a"] / r["b"] for r in rows]
    avg_ratio = sum(ratios) / len(ratios)
    if avg_ratio > 1.3:
        label = "underestimating"
    elif avg_ratio < 0.7:
        label = "overestimating"
    else:
        label = "calibrated"
    return {"label": label, "avg_ratio": round(avg_ratio, 2), "samples": len(rows)}
