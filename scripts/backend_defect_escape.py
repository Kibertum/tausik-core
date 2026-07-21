"""Defect escape rate — the one metric that can falsify "the gates work".

l26-defect-escape-rate. Everything else TAUSIK measures is an INPUT (risk score,
budget calibration, gate activity): computed at closure, never checked against
what actually happened. `tasks.defect_of` already records that a later task was
filed to fix an earlier closure, but nothing counted the OUTCOME — the share of
done tasks that a defect later escaped from.

This module computes that share and slices it by the escaped task's own
attributes (complexity, role, tier, and whether it carried a verify run), plus a
first-order backtest of `risk_score` against the outcome: if the score has
signal, escaped closures should average a higher risk than clean ones. A crude
aggregate `der` already lives in get_metrics; this is the principled, sliced
version that keeps the escaped task's identity so the number can be interrogated.

`defect_of` holds the PARENT slug (the closure being fixed), so the escaped set
is exactly the done tasks that appear as some row's `defect_of`.
"""

from __future__ import annotations

from typing import Any, Callable

QueryFn = Callable[..., list]


def _rate(escaped: int, done: int) -> dict[str, Any]:
    """One bucket: how many done closures escaped, out of how many. done=0 →
    rate 0, never a ZeroDivisionError (an empty slice is 0% escaped, not undefined
    for our purpose — the count alongside makes an empty bucket legible)."""
    return {
        "escaped": escaped,
        "done": done,
        "rate_pct": round(escaped / done * 100, 1) if done else 0,
    }


def _group_rates(rows: list, key: str) -> dict[str, dict[str, Any]]:
    """Escape rate grouped by one attribute of the escaped task. A NULL value
    (e.g. a task with no tier) buckets under 'unknown' rather than vanishing —
    silence would hide exactly the untracked closures this metric exists to see."""
    buckets: dict[str, list] = {}
    for r in rows:
        buckets.setdefault(r[key] or "unknown", []).append(r)
    return {
        name: _rate(sum(1 for r in items if r["escaped"]), len(items))
        for name, items in sorted(buckets.items())
    }


def _done_rows(q: QueryFn) -> list:
    """Every done task tagged with escaped (a defect points at it) and verified
    (it carried a verify run). Falls back to verified=0 when verification_runs is
    absent (a partially-migrated DB) so the metric degrades rather than crashes."""
    base = (
        "SELECT t.slug, t.complexity, t.role, t.tier, t.risk_score, "
        "CASE WHEN EXISTS(SELECT 1 FROM tasks d WHERE d.defect_of = t.slug) "
        "THEN 1 ELSE 0 END AS escaped, {verified} AS verified "
        "FROM tasks t WHERE t.status='done'"
    )
    verified_expr = (
        "CASE WHEN EXISTS(SELECT 1 FROM verification_runs v "
        "WHERE v.task_slug = t.slug) THEN 1 ELSE 0 END"
    )
    try:
        return q(base.format(verified=verified_expr))
    except Exception:  # noqa: BLE001 — metric must degrade, not crash, on a missing table
        return q(base.format(verified="0"))


def defect_escape_metrics(q: QueryFn) -> dict[str, Any]:
    """Escape rate overall and sliced, plus a risk_score backtest.

    Read-only. Safe on an empty DB (every rate 0, no division by zero). The
    backtest averages `risk_score` over escaped vs non-escaped done closures
    (NULL scores excluded), so a higher escaped average is direct evidence the
    score predicts outcomes — the check risk_score never got until now.
    """
    rows = _done_rows(q)
    escaped_scores = [r["risk_score"] for r in rows if r["escaped"] and r["risk_score"] is not None]
    clean_scores = [
        r["risk_score"] for r in rows if not r["escaped"] and r["risk_score"] is not None
    ]
    total_escaped = sum(1 for r in rows if r["escaped"])
    return {
        "overall": _rate(total_escaped, len(rows)),
        "by_complexity": _group_rates(rows, "complexity"),
        "by_role": _group_rates(rows, "role"),
        "by_tier": _group_rates(rows, "tier"),
        "by_verification": {
            "verified": _rate(
                sum(1 for r in rows if r["verified"] and r["escaped"]),
                sum(1 for r in rows if r["verified"]),
            ),
            "unverified": _rate(
                sum(1 for r in rows if not r["verified"] and r["escaped"]),
                sum(1 for r in rows if not r["verified"]),
            ),
        },
        "risk_backtest": {
            "escaped_avg_risk": round(sum(escaped_scores) / len(escaped_scores), 4)
            if escaped_scores
            else None,
            "clean_avg_risk": round(sum(clean_scores) / len(clean_scores), 4)
            if clean_scores
            else None,
            "escaped_n": len(escaped_scores),
            "clean_n": len(clean_scores),
        },
    }
