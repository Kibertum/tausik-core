"""The metrics report, built ONCE for both surfaces.

`tausik metrics` printed the whole SENAR report — throughput, lead time, FPSR,
DER, cycle time, knowledge capture, dead-end rate, cost per complexity, the risk
section and the telemetry tails. The MCP tool answered with ONE line: tasks
done, average time, session count. CLAUDE.md tells agents to prefer MCP, so the
primary reader of these numbers was seeing the smallest part of them.

That was not a decision to summarise. It was a second implementation, written
early and never grown, and the CLI kept adding sections it never learned about.

The conversion is deliberately literal: every `print(x)` became `append(x)`,
embedded leading newlines included, so the CLI's output is byte-identical to
what it printed before. A report that changed shape in the same commit that
changed its owner would leave nobody able to say which change did what.

Every optional section stays best-effort. A metrics command that dies because
one telemetry table is missing is worse than one that reports what it has: these
numbers are read to decide what to do next, and refusing to answer at all is the
one answer that helps nobody.
"""

from __future__ import annotations

from typing import Any

from model_pinning import format_model_usage_section

#: Per-tier rows are printed in the tier order the estimator uses, not in the
#: dict's order — a report whose row order depends on insertion is a report that
#: reads differently from one run to the next.
_TIER_ORDER = ("trivial", "light", "moderate", "substantial", "deep", "unset")


def metrics_lines(svc: Any) -> list[str]:
    """The whole metrics report, one element per printed line."""
    m = svc.get_metrics()
    out: list[str] = [f"Tasks: {m['tasks_done']}/{m['tasks_total']} done ({m['completion_pct']}%)"]
    for status, count in sorted(m["tasks"].items()):
        out.append(f"  {status}: {count}")
    out.append("\n--- SENAR Metrics ---")
    out.append(f"Throughput:    {m['throughput']} tasks/session")
    # "n/a" rather than 0: a zero here would be a claim about a measurement that
    # was never taken, and the two are not the same statement.
    lead = f"{m['lead_time_hours']}h" if m.get("lead_time_hours") is not None else "n/a"
    out.append(f"Lead Time:     {lead} (avg created→done)")
    out.append(f"FPSR:          {m['fpsr']}% (first-pass success rate)")
    out.append(f"DER:           {m['der']}% (defect escape rate)")
    cycle = f"{m['cycle_time_hours']}h" if m.get("cycle_time_hours") is not None else "n/a"
    out.append(f"Cycle Time:    {cycle} (avg started→done)")
    out.append(f"Knowledge CR:  {m['knowledge_capture_rate']} entries/task")
    out.append(f"Dead End Rate: {m['dead_end_rate']}% ({m['dead_end_count']} dead ends)")
    cost = m.get("cost_per_task", {})
    if cost:
        out.append("\n--- Cost per Task ---")
        for complexity, data in sorted(cost.items()):
            out.append(f"  {complexity}: {data['avg_hours']}h avg ({data['count']} tasks)")
    out += extended_metrics_lines(m)
    out += _risk_lines(svc)
    out += _routing_lines()
    out += _review_lines(svc)
    out += _root_cause_lines(svc)
    out += _brain_lines(svc)
    out.append(f"\nSessions: {m['sessions_total']} ({m['session_hours']}h total)")
    if m["stories"]:
        total = sum(m["stories"].values())
        out.append(f"Stories: {m['stories'].get('done', 0)}/{total} done")
    out += _usage_lines(m)
    out += list(format_model_usage_section(svc.be.usage_events_cost_rollup_by_model()))
    return out


def _risk_lines(svc: Any) -> list[str]:
    """Closure risk beside DER/FPSR. Absent when the module cannot answer."""
    try:
        from risk_metrics import format_risk_section, risk_summary

        risk = risk_summary(svc.be._conn)
    except Exception:  # noqa: BLE001 — best-effort: a missing tail must not kill the report
        return []
    return [f"\n{format_risk_section(risk)}"] if risk else []


def _routing_lines() -> list[str]:
    """Recommendation FIT, not compliance (decision #183)."""
    try:
        from model_routing_adherence import aggregate_adherence
        from project_config import find_tausik_dir

        adherence = aggregate_adherence(find_tausik_dir())
    except Exception:  # noqa: BLE001 — best-effort: a missing tail must not kill the report
        adherence = None
    from model_routing_adherence import format_recommendation_fit

    block = format_recommendation_fit(adherence)
    return [f"\n{block}"] if block else []


def _review_lines(svc: Any) -> list[str]:
    try:
        rm = svc.be.review_metrics()
    except Exception:  # noqa: BLE001 — best-effort: a missing tail must not kill the report
        return []
    if not (rm and rm.get("l3_reviewed_tasks")):
        return []
    return [
        "\n--- Adversarial Review (SENAR Rule 10.15) ---",
        f"L3 reviewed tasks: {rm['l3_reviewed_tasks']}, "
        f"critical findings: {rm['l3_critical_findings']}, "
        f"ADR: {rm['adr_pct']}% (critical/L3-task)",
    ]


def _root_cause_lines(svc: Any) -> list[str]:
    try:
        from root_cause import root_cause_metrics

        rcm = root_cause_metrics(svc.be._q)
    except Exception:  # noqa: BLE001 — best-effort: a missing tail must not kill the report
        return []
    if not (rcm and rcm.get("defect_done")):
        return []
    return [
        "\n--- Root Cause Coverage (SENAR Rule 7) ---",
        f"Defect tasks done: {rcm['defect_done']}, "
        f"structured: {rcm['structured']}, "
        f"coverage: {rcm['coverage_pct']}%",
    ]


def _brain_lines(svc: Any) -> list[str]:
    try:
        bm = svc.be.brain_event_metrics()
    except Exception:  # noqa: BLE001 — best-effort: a missing tail must not kill the report
        return []
    if not (bm and (bm["session"]["searches"] or bm["all_time"]["searches"])):
        return []
    session, all_time = bm["session"], bm["all_time"]
    return [
        "\n--- Shared Brain (v1.4) ---",
        f"Session: {session['searches']} searches, {session['hits']} hits, "
        f"{session['writes']} writes, {session['ignored']} ignored "
        f"(hit rate: {session['hit_rate_pct']}%)",
        f"All-time: {all_time['searches']} searches, {all_time['hits']} hits, "
        f"{all_time['writes']} writes (hit rate: {all_time['hit_rate_pct']}%)",
    ]


def _usage_lines(m: dict[str, Any]) -> list[str]:
    usage = m.get("session_usage") or {}
    if not usage.get("sessions_with_usage"):
        return []
    out = [
        "\n--- LLM Usage ---",
        f"Sessions tracked: {usage['sessions_with_usage']}, "
        f"tokens: {usage['tokens_total']:,}, cost: ${usage['cost_usd']:.4f}",
    ]
    # The total above spans two arithmetics: everything recorded before
    # `sum_usage_tokens` was corrected counted every message twice (measured
    # 1.9999x over 23,836 live messages). Those rows cannot be recomputed —
    # transcripts survive for only a fraction of the sessions, and the ones
    # predating the API's `iterations` field were never doubled at all — so the
    # share is NAMED rather than silently folded in. Two scales in one column
    # are tolerable only while the reader is told which is which.
    superseded = int(usage.get("superseded_sessions") or 0)
    if superseded:
        out.append(
            f"  of which {superseded} session(s) — {int(usage.get('superseded_tokens') or 0):,} "
            f"tokens, ${float(usage.get('superseded_cost_usd') or 0.0):.4f} — were recorded by a "
            "superseded arithmetic that counted each message twice (~2x inflated, not recomputable)"
        )
    last = usage.get("last_session") or {}
    if last:
        out.append(
            "Last session: "
            f"#{last.get('session_id')} "
            f"{int(last.get('tokens_total') or 0):,} tokens, "
            f"${float(last.get('cost_usd') or 0):.4f}, "
            f"model={last.get('model') or '-'}"
        )
    return out


def extended_metrics_lines(m: dict[str, Any]) -> list[str]:
    """Per-tier, calibration drift, defect escape and the supervision tails.

    Each supervision family gets its OWN heading on purpose. A bypass (somebody
    switched supervision off), a detection (supervision caught something) and a
    degradation (a guard let an edit through because it could not read the DB)
    are three different facts, and one shared heading would let the worst of
    them read as the best.
    """
    out: list[str] = []
    per_tier = m.get("per_tier") or {}
    if per_tier:
        out.append("\n--- Per-tier (agent-native units) ---")
        for tier in _TIER_ORDER:
            d = per_tier.get(tier)
            if not d:
                continue
            budget = d["avg_budget"] if d["avg_budget"] is not None else "-"
            actual = d["avg_actual"] if d["avg_actual"] is not None else "-"
            out.append(
                f"  {tier:>11}: count={d['count']:<4} budget={budget:<6} "
                f"actual={actual:<6} fpsr={d['fpsr_pct']}%"
            )
    drift = m.get("calibration_drift")
    if drift:
        out.append(
            f"\nCalibration drift: {drift['label']} "
            f"(avg actual/budget = {drift['avg_ratio']}, n={drift['samples']})"
        )
    out += _escape_lines(m.get("defect_escape"))
    out += _bypass_lines(m.get("supervision_bypasses") or {})
    for key, heading in (
        ("supervision_detections", "\n--- Supervision detections (l26) ---"),
        (
            "supervision_degradations",
            "\n--- Supervision degradations / fail-open (l26) ---",
        ),
    ):
        section = m.get(key) or {}
        if not section.get("total"):
            continue
        out.append(heading)
        out.append(f"Total: {section['total']}")
        for action, count in section.get("by_action", {}).items():
            out.append(f"  {action:<26}: {count}")
    return out


def _bypass_lines(section: dict[str, Any]) -> list[str]:
    """Bypass frequency and metric 8, printed as NESTED and labelled as such.

    SENAR 1.4 §8.6(i): manual interventions are a subset of bypasses, and the
    standard says the two SHALL NOT be added. Printing them as two totals on
    adjacent lines is an invitation to add them, so the containment is stated in
    the line itself — "of which", not a second total.
    """
    if not section.get("total"):
        return []
    out = [
        "\n--- Supervision bypasses (l26) ---",
        f"Total: {section['total']}"
        + (
            f" — of which {section['manual_intervention']} manual intervention "
            f"(§8.6(j)), {section['other']} other. NESTED: do not add."
            if section.get("nested")
            else ""
        ),
    ]
    for action, count in (section.get("by_action") or {}).items():
        out.append(f"  {action:<26}: {count}")
    return out


def _escape_lines(esc: dict[str, Any] | None) -> list[str]:
    """DER is the crude aggregate; this says whether verification tracks escapes."""
    if not esc:
        return []
    overall = esc["overall"]
    out = [
        "\n--- Defect Escape (l26) ---",
        f"Escape rate:   {overall['rate_pct']}% "
        f"({overall['escaped']}/{overall['done']} done escaped)",
    ]
    by_verification = esc.get("by_verification", {})
    for label in ("verified", "unverified"):
        d = by_verification.get(label)
        if d and d["done"]:
            out.append(f"  {label:<11}: {d['rate_pct']}% ({d['escaped']}/{d['done']})")
    bt = esc.get("risk_backtest", {})
    if bt.get("escaped_avg_risk") is None and bt.get("clean_avg_risk") is None:
        return out
    escaped = bt["escaped_avg_risk"] if bt["escaped_avg_risk"] is not None else "-"
    clean = bt["clean_avg_risk"] if bt["clean_avg_risk"] is not None else "-"
    out.append(
        f"  risk backtest: escaped avg={escaped} (n={bt['escaped_n']}) "
        f"vs clean avg={clean} (n={bt['clean_n']})"
    )
    # Two averages invite "escaped is lower, so the score is inverted". The
    # measured answer is duller and worse: it separates nothing. Printing AUC
    # beside them stops the averages from being read as a verdict, and
    # complexity_auc shows what the comparison is against.
    if bt.get("auc") is not None:
        verdict = "no discriminative power" if abs(bt["auc"] - 0.5) < 0.05 else "check sign"
        line = f"    AUC={bt['auc']} (0.5 = coin flip) — {verdict}"
        if bt.get("complexity_auc") is not None:
            line += f"; complexity alone AUC={bt['complexity_auc']}"
        out.append(line)
    return out
