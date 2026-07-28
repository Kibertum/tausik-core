"""TAUSIK CLI handler for `tausik metrics` — command + subcommand dispatch.

Holds `cmd_metrics` itself, not just its helpers. It previously lived in
project_cli_ops.py while this file — named for the domain — held only the
dispatcher it calls, so the command and its own module were separated by a
line count rather than by a domain (filesize-rejoin-cap-deformed-wrappers,
decision #199).
"""

from __future__ import annotations

from typing import Any

from model_pinning import format_model_usage_section
from project_service import ProjectService


def _print_usage_cost_rollup(svc: ProjectService, since: str | None, until: str | None) -> None:
    rows = svc.usage_cost_rollup_by_task(since=since, until=until)
    if not rows:
        print(
            "No usage data for tasks in the selected window (usage_events with non-null task_slug)."
        )
        return
    print("task_slug".ljust(32), "events".rjust(8), "tokens".rjust(12), "cost_usd".rjust(12))
    for r in rows:
        slug = str(r.get("task_slug") or "")
        ev = int(r.get("event_count") or 0)
        tok = int(r.get("tokens_total") or 0)
        cost = float(r.get("cost_usd") or 0.0)
        print(
            slug[:32].ljust(32),
            str(ev).rjust(8),
            f"{tok:,}".rjust(12),
            f"{cost:.4f}".rjust(12),
        )


def cmd_metrics(svc: ProjectService, args: Any) -> None:
    from project_cli_metrics import dispatch_metrics_subcmd

    if dispatch_metrics_subcmd(svc, args):
        return
    m = svc.get_metrics()
    print(f"Tasks: {m['tasks_done']}/{m['tasks_total']} done ({m['completion_pct']}%)")
    for status, cnt in sorted(m["tasks"].items()):
        print(f"  {status}: {cnt}")
    # SENAR mandatory metrics
    print("\n--- SENAR Metrics ---")
    print(f"Throughput:    {m['throughput']} tasks/session")
    lt = f"{m['lead_time_hours']}h" if m.get("lead_time_hours") is not None else "n/a"
    print(f"Lead Time:     {lt} (avg created→done)")
    print(f"FPSR:          {m['fpsr']}% (first-pass success rate)")
    print(f"DER:           {m['der']}% (defect escape rate)")
    # Recommended
    ct = f"{m['cycle_time_hours']}h" if m.get("cycle_time_hours") is not None else "n/a"
    print(f"Cycle Time:    {ct} (avg started→done)")
    print(f"Knowledge CR:  {m['knowledge_capture_rate']} entries/task")
    print(f"Dead End Rate: {m['dead_end_rate']}% ({m['dead_end_count']} dead ends)")
    # Cost per Task by complexity (SENAR v1.3)
    cost = m.get("cost_per_task", {})
    if cost:
        print("\n--- Cost per Task ---")
        for complexity, data in sorted(cost.items()):
            print(f"  {complexity}: {data['avg_hours']}h avg ({data['count']} tasks)")
    # Per-tier / calibration / defect-escape tail — extracted to project_cli_metrics
    # for the 400-line filesize gate (l26-defect-escape-rate). Output unchanged.
    from project_cli_metrics import render_extended_metrics

    render_extended_metrics(m)
    # v15-risk-surface-metrics: closure risk next to DER/FPSR for trends.
    try:
        from risk_metrics import format_risk_section, risk_summary

        risk = risk_summary(svc.be._conn)
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        risk = None
    if risk:
        print(f"\n{format_risk_section(risk)}")
    # v15mr-routing-telemetry: recommended-vs-actual model adherence (matrix calibration).
    try:
        from model_routing_adherence import aggregate_adherence
        from project_config import find_tausik_dir

        adh = aggregate_adherence(find_tausik_dir())
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        adh = None
    # routing-adherence-metric-measures-nothing (decision #183): recommendation
    # FIT, not compliance — the formatter names the manual-choice caveat and
    # prints nothing when there is no data.
    from model_routing_adherence import format_recommendation_fit

    fit_block = format_recommendation_fit(adh)
    if fit_block:
        print(f"\n{fit_block}")
    try:
        rm = svc.be.review_metrics()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        rm = None
    if rm and rm.get("l3_reviewed_tasks"):
        print("\n--- Adversarial Review (SENAR Rule 10.15) ---")
        print(
            f"L3 reviewed tasks: {rm['l3_reviewed_tasks']}, "
            f"critical findings: {rm['l3_critical_findings']}, "
            f"ADR: {rm['adr_pct']}% (critical/L3-task)"
        )
    try:
        from root_cause import root_cause_metrics

        rcm = root_cause_metrics(svc.be._q)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        rcm = None
    if rcm and rcm.get("defect_done"):
        print("\n--- Root Cause Coverage (SENAR Rule 7) ---")
        print(
            f"Defect tasks done: {rcm['defect_done']}, "
            f"structured: {rcm['structured']}, "
            f"coverage: {rcm['coverage_pct']}%"
        )
    try:
        bm = svc.be.brain_event_metrics()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        bm = None
    if bm and (bm["session"]["searches"] or bm["all_time"]["searches"]):
        print("\n--- Shared Brain (v1.4) ---")
        s = bm["session"]
        a = bm["all_time"]
        print(
            f"Session: {s['searches']} searches, {s['hits']} hits, "
            f"{s['writes']} writes, {s['ignored']} ignored "
            f"(hit rate: {s['hit_rate_pct']}%)"
        )
        print(
            f"All-time: {a['searches']} searches, {a['hits']} hits, "
            f"{a['writes']} writes (hit rate: {a['hit_rate_pct']}%)"
        )
    print(f"\nSessions: {m['sessions_total']} ({m['session_hours']}h total)")
    if m["stories"]:
        total_s = sum(m["stories"].values())
        done_s = m["stories"].get("done", 0)
        print(f"Stories: {done_s}/{total_s} done")
    usage = m.get("session_usage") or {}
    if usage.get("sessions_with_usage"):
        print("\n--- LLM Usage ---")
        print(
            f"Sessions tracked: {usage['sessions_with_usage']}, "
            f"tokens: {usage['tokens_total']:,}, cost: ${usage['cost_usd']:.4f}"
        )
        last = usage.get("last_session") or {}
        if last:
            print(
                "Last session: "
                f"#{last.get('session_id')} "
                f"{int(last.get('tokens_total') or 0):,} tokens, "
                f"${float(last.get('cost_usd') or 0):.4f}, "
                f"model={last.get('model') or '-'}"
            )
    for line in format_model_usage_section(svc.be.usage_events_cost_rollup_by_model()):
        print(line)


def render_extended_metrics(m: dict[str, Any]) -> None:
    """Print the per-tier, calibration-drift and defect-escape tail of the metrics
    summary. Extracted from project_cli_ops._print_metrics so that file stays under
    the 400-line filesize gate when l26-defect-escape-rate added the escape section.
    Output is byte-identical to the inline version it replaced."""
    per_tier = m.get("per_tier") or {}
    if per_tier:
        print("\n--- Per-tier (agent-native units) ---")
        order = ["trivial", "light", "moderate", "substantial", "deep", "unset"]
        for tier in order:
            d = per_tier.get(tier)
            if not d:
                continue
            ab = d["avg_budget"] if d["avg_budget"] is not None else "-"
            aa = d["avg_actual"] if d["avg_actual"] is not None else "-"
            print(
                f"  {tier:>11}: count={d['count']:<4} budget={ab:<6} "
                f"actual={aa:<6} fpsr={d['fpsr_pct']}%"
            )
    drift = m.get("calibration_drift")
    if drift:
        print(
            f"\nCalibration drift: {drift['label']} "
            f"(avg actual/budget = {drift['avg_ratio']}, n={drift['samples']})"
        )
    # l26-defect-escape-rate: the outcome metric. DER is the crude aggregate; this
    # shows whether verification and risk_score actually track escapes.
    esc = m.get("defect_escape")
    if esc:
        ov = esc["overall"]
        print("\n--- Defect Escape (l26) ---")
        print(f"Escape rate:   {ov['rate_pct']}% ({ov['escaped']}/{ov['done']} done escaped)")
        bv = esc.get("by_verification", {})
        for label in ("verified", "unverified"):
            d = bv.get(label)
            if d and d["done"]:
                print(f"  {label:<11}: {d['rate_pct']}% ({d['escaped']}/{d['done']})")
        bt = esc.get("risk_backtest", {})
        if bt.get("escaped_avg_risk") is not None or bt.get("clean_avg_risk") is not None:
            ea = bt["escaped_avg_risk"] if bt["escaped_avg_risk"] is not None else "-"
            ca = bt["clean_avg_risk"] if bt["clean_avg_risk"] is not None else "-"
            print(
                f"  risk backtest: escaped avg={ea} (n={bt['escaped_n']}) "
                f"vs clean avg={ca} (n={bt['clean_n']})"
            )
            # Two averages invite "escaped is lower, so the score is inverted".
            # The measured answer is duller and worse: it separates nothing.
            # Printing AUC next to them stops the averages from being read as a
            # verdict, and complexity_auc shows what the comparison is against.
            if bt.get("auc") is not None:
                cauc = bt.get("complexity_auc")
                verdict = "no discriminative power" if abs(bt["auc"] - 0.5) < 0.05 else "check sign"
                line = f"    AUC={bt['auc']} (0.5 = coin flip) — {verdict}"
                if cauc is not None:
                    line += f"; complexity alone AUC={cauc}"
                print(line)
    # l26-bypass-telemetry: how many times supervision was switched off. Only
    # rendered when non-zero — a clean run stays quiet, but a bypass can no
    # longer hide as silence (the whole point: the count is falsifiable).
    byp = m.get("supervision_bypasses") or {}
    if byp.get("total"):
        print("\n--- Supervision bypasses (l26) ---")
        print(f"Total: {byp['total']}")
        for action, cnt in byp.get("by_action", {}).items():
            print(f"  {action:<26}: {cnt}")
    # l26-complexity-self-declared: detections are supervision that WORKED —
    # rendered under their OWN heading so they are never misread as bypasses.
    det = m.get("supervision_detections") or {}
    if det.get("total"):
        print("\n--- Supervision detections (l26) ---")
        print(f"Total: {det['total']}")
        for action, cnt in det.get("by_action", {}).items():
            print(f"  {action:<26}: {cnt}")
    # hook-fail-open-db-error-telemetry: silent fail-open degradations — a guard
    # that let an edit through because it could not read the DB. Its OWN heading
    # so it is never misread as a bypass (nobody switched it off) or a detection
    # (nothing was caught). Rendered only when non-zero.
    deg = m.get("supervision_degradations") or {}
    if deg.get("total"):
        print("\n--- Supervision degradations / fail-open (l26) ---")
        print(f"Total: {deg['total']}")
        for action, cnt in deg.get("by_action", {}).items():
            print(f"  {action:<26}: {cnt}")


def dispatch_metrics_subcmd(svc: ProjectService, args: Any) -> bool:
    """Handle `metrics <sub>`: record-session, log-usage, cost, tokens.

    Returns True if a subcommand was dispatched (caller should return),
    False if the request is for the default `metrics` summary view.
    """
    sub = getattr(args, "metrics_cmd", None)
    if sub == "record-session":
        kw = dict(
            tokens_input=args.tokens_input,
            tokens_output=args.tokens_output,
            tokens_total=args.tokens_total,
            cost_usd=args.cost_usd,
            tool_calls=getattr(args, "tool_calls", 0),
            model=getattr(args, "model", ""),
            session_id=getattr(args, "session_id", None),
        )
        print(svc.metrics_record_session(**kw))
        return True
    if sub == "log-usage":
        kw = dict(
            tokens_input=args.tokens_input,
            tokens_output=args.tokens_output,
            tokens_total=args.tokens_total,
            cost_usd=args.cost_usd,
            tool_calls=getattr(args, "tool_calls", 0),
            model=getattr(args, "model", ""),
            task_slug=getattr(args, "task_slug", None),
            session_id=getattr(args, "session_id", None),
        )
        print(svc.metrics_log_usage_event(**kw))
        return True
    if sub == "cost" or getattr(args, "cost", False):
        # Local now: the helper crossed back from project_cli_ops with cmd_metrics.
        _print_usage_cost_rollup(svc, getattr(args, "since", None), getattr(args, "until", None))
        return True
    if sub == "tokens":
        from service_token_metrics import print_cli

        print_cli(int(getattr(args, "last", 10) or 10), bool(getattr(args, "as_json", False)))
        return True
    return False


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
