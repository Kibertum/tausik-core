"""Per-tier metrics + calibration drift helpers (agent-native sizing).

Extracted from backend_queries.py to keep that file under the 400-line gate.
Both functions take a callable `q` matching SQLiteBackend._q.
"""

from __future__ import annotations

from typing import Any, Callable

QueryFn = Callable[..., list[dict[str, Any]]]

# A tier's inclusive upper bound may sit at most this far above the p50 of
# that tier's measured actuals; further out it decorates instead of
# constraining (recalibrate-tier-call-budgets-against-observed: substantial
# budget 105.1 vs actual 53.3 — a 2x cushion that never bound anything).
BUDGET_CALIBRATION_FACTOR = 3.0


def _percentile(sorted_vals: list[float], frac: float) -> float | None:
    """Linear-interpolated percentile of an already-sorted list."""
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * frac
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return round(float(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)), 1)


def per_tier_metrics(q: QueryFn) -> dict[str, dict[str, Any]]:
    """Group done tasks by tier; emit count, avg_budget, avg_actual, fpsr.

    Also emits p50/p90 of the measured actuals per tier — the evidence the
    tier thresholds are calibrated against (avg alone hides the spread that
    decides whether a budget blocks real work).
    """
    rows = q(
        "SELECT COALESCE(tier, 'unset') AS tier, call_budget AS b, "
        "call_actual AS a, attempts AS attempts "
        "FROM tasks WHERE status='done' AND resolution IS NULL"
    )
    by_tier: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_tier.setdefault(r["tier"], []).append(r)
    out: dict[str, dict[str, Any]] = {}
    for tier, rs in by_tier.items():
        cnt = len(rs)
        budgets = [r["b"] for r in rs if r["b"] is not None]
        actuals = sorted(float(r["a"]) for r in rs if r["a"] is not None)
        ab = sum(budgets) / len(budgets) if budgets else None
        aa = sum(actuals) / len(actuals) if actuals else None
        ratio = round(aa / ab, 2) if ab and aa is not None and ab > 0 else None
        first_pass = sum(1 for r in rs if r["attempts"] == 1)
        out[tier] = {
            "count": cnt,
            "avg_budget": round(ab, 1) if ab is not None else None,
            "avg_actual": round(aa, 1) if aa is not None else None,
            "fpsr_pct": round(first_pass / cnt * 100, 1) if cnt else 0,
            "ratio_actual_over_budget": ratio,
            "p50_actual": _percentile(actuals, 0.5),
            "p90_actual": _percentile(actuals, 0.9),
        }
    return out


def budget_calibration_check(
    q: QueryFn,
    thresholds: tuple[tuple[int, str], ...] | None = None,
    factor: float = BUDGET_CALIBRATION_FACTOR,
) -> dict[str, Any] | None:
    """Compare tier thresholds against rolling actuals; None if nothing measured.

    Rule (both directions, stated once):
    - STARVED (hard fail): a tier's upper bound sits BELOW the p50 of that
      tier's measured actuals — half of real work would exceed the budget,
      i.e. the budget blocks legitimate work.
    - DECORATED: the upper bound sits more than ``factor`` x p50 — the budget
      constrains nothing and only labels the task.
    """
    if thresholds is None:
        from backend_crud import _TIER_THRESHOLDS  # lazy: avoid a cycle
        thresholds = _TIER_THRESHOLDS
    per_tier = per_tier_metrics(q)
    tiers: dict[str, dict[str, Any]] = {}
    measured = 0
    worst = "ok"
    for upper, label in thresholds:
        stats = per_tier.get(label) or {}
        p50 = stats.get("p50_actual")
        # n<5 is noise, not calibration: a single deep task at 66 calls must
        # not brand the whole tier. Unmeasured tiers never set the verdict.
        if p50 is None or (stats.get("count") or 0) < 5:
            tiers[label] = {"upper": upper, "p50_actual": p50, "verdict": "unmeasured"}
            continue
        measured += 1
        if upper < p50:
            verdict = "starved"
        elif upper > factor * p50:
            verdict = "decorated"
        else:
            verdict = "ok"
        # Severity order: starved > decorated > ok; unmeasured never wins.
        if verdict == "starved" or worst == "starved":
            worst = "starved"
        elif verdict == "decorated" or worst == "decorated":
            worst = "decorated"
        tiers[label] = {"upper": upper, "p50_actual": p50, "verdict": verdict}
    if not tiers or not measured:
        # All-unmeasured is no verdict: thresholds judged only by tiers with
        # n>=5 carry the check; an empty or n<5-only corpus must not print
        # "ok" it did not earn.
        return None
    return {"status": worst, "factor": factor, "tiers": tiers}


def session_capacity_summary(
    q: QueryFn, q1: Callable[..., dict[str, Any] | None], capacity: int
) -> dict[str, Any]:
    """Per-session tool-call accounting: used, planned, remaining."""
    sess = q1("SELECT id, started_at FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")
    if not sess:
        return {
            "session": None,
            "capacity": capacity,
            "used": 0,
            "planned_active": 0,
            "remaining": capacity,
        }
    # THE CALLS THIS SHIFT MADE, from `usage_events` — which carries `session_id`
    # for exactly this question.
    #
    # It used to sum `call_actual` over tasks CLOSED since the session started,
    # and `call_actual` is a task's WHOLE LIFE. The two agree while a task opens
    # and closes inside one shift, which is the ordinary case, and that is why
    # the defect survived. It breaks on a long-lived task: observed in session
    # #236, `release-18-breaking-change-notes` had accrued 395 calls since
    # session #177 against a budget of 12, and closing it printed
    #
    #     Capacity: 419/200 used, 0 planned, -219 remaining ⚠ overshoot
    #
    # sixteen minutes and about twenty-five calls into the shift. The operating
    # rule is "end the shift on capacity, do not force it", so a gauge that says
    # 419 after twenty-five calls stops work for no reason — and it does so
    # precisely when a long-standing task was finally closed.
    used_row = q1(
        "SELECT COALESCE(COUNT(*),0) AS used FROM usage_events WHERE session_id = ?",
        (sess["id"],),
    )
    # What active tasks still RESERVE: the part of each budget not yet spent,
    # in any session. It used to be the full budget, so a task that spent 140
    # of 150 calls in an earlier shift reserved 150 in every new one (GitLab #8,
    # the second layer). The calls spent THIS session are in `used`; taking
    # them off the reservation is what keeps them from being counted twice.
    planned_row = q1(
        "SELECT COALESCE(SUM(MAX(0, t.call_budget - ("
        "  SELECT COUNT(*) FROM usage_events u WHERE u.task_slug = t.slug"
        "))),0) AS planned FROM tasks t "
        "WHERE t.status='active' AND t.call_budget IS NOT NULL"
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
    """Drift label from the MEDIAN of the last 30 measured closures; None if <5.

    calibration-window-too-small-to-forecast (1.10): the mean of the last 10
    moved 0.71 -> 0.49 within one session on the same backlog. Backtest over 580
    forecast points (predicting the next 20 closures): mean10 MAE 0.463, jitter
    0.094; median30 MAE 0.364, jitter 0.016 — the winner, 21% less error and 6x
    steadier. The spread (p25..p75) and n travel with the point, because a
    coefficient without its spread misleads more than none.

    TOKENIZER-INDEPENDENT (l26-tokenizer-calibration re-check). This ratio is
    ``call_actual / call_budget`` — TOOL-CALL COUNTS, integers unaffected by the
    2026 tokenizer change (Opus 4.7+/Fable 5/Mythos 5/Sonnet 5 emit ~30% more
    tokens for the same text). The hypothesis that part of the observed drift is
    a tokenizer artifact was tested and rejected: **0%** of this signal's drift
    is attributable to the tokenizer, because call counts carry no tokens. The
    ~30% correction (``token_accounting``) belongs only where TOKENS or DOLLARS
    are compared across the boundary (usage rollups, token budgets), never here.
    """
    rows = q(
        "SELECT call_budget AS b, call_actual AS a "
        "FROM tasks WHERE status='done' AND resolution IS NULL "
        "AND call_budget IS NOT NULL AND call_actual IS NOT NULL "
        "AND call_budget > 0 "
        "ORDER BY completed_at DESC LIMIT 30"
    )
    if len(rows) < 5:
        return None
    ratios = sorted(r["a"] / r["b"] for r in rows)

    def _q(frac: float) -> float:
        k = (len(ratios) - 1) * frac
        lo, hi = int(k), min(int(k) + 1, len(ratios) - 1)
        return float(ratios[lo] + (ratios[hi] - ratios[lo]) * (k - lo))

    avg_ratio = _q(0.5)  # the median; the key name is kept for its readers
    if avg_ratio > 1.3:
        label = "underestimating"
    elif avg_ratio < 0.7:
        label = "overestimating"
    else:
        label = "calibrated"
    return {
        "label": label,
        "avg_ratio": round(avg_ratio, 2),
        "samples": len(rows),
        "p25": round(_q(0.25), 2),
        "p75": round(_q(0.75), 2),
    }
