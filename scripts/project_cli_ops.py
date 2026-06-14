"""TAUSIK CLI handlers -- metrics, search, events, explore, audit, run, dead-end, brain commands."""

from __future__ import annotations

import os
import sys
from typing import Any

from brain_cli_ops import cmd_brain  # noqa: F401  re-exported for project.py
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
    # Per-tier (agent-native sizing)
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
    if adh and adh.get("n"):
        print("\n--- Routing Adherence (v1.5) ---")
        print(f"Recommended == actual: {adh['pct']}% (n={adh['n']})")
        for d in adh.get("top_deviations", []):
            print(f"  deviation {d['shift']}: {d['count']}")
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


def cmd_hud(svc: ProjectService, args: Any) -> None:
    """Live dashboard: active task + session + gates + recent logs.

    Compact one-screen view for quick situational awareness.
    """
    print("═══ TAUSIK HUD ═══")
    # Session
    try:
        session = svc.session_current()
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        session = None
    if session:
        print(f"Session: #{session.get('id', '?')} started {session.get('started_at', '')}")
    else:
        print("Session: (none — use /start or tausik session start)")
    # Active task
    active = svc.task_list(status="active")
    if active:
        for t in active:
            title = (t.get("title") or "")[:80]
            slug = t.get("slug", "?")
            print(f"\nActive: {slug} — {title}")
            try:
                full = svc.task_show(slug)
                plan = full.get("plan")
                plan_done = full.get("plan_done") or []
                if isinstance(plan, list) and plan:
                    print(f"  Plan progress: {len(plan_done)}/{len(plan)} steps")
            except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
                pass
            try:
                logs = svc.task_logs(slug)
                if logs:
                    print("  Recent logs:")
                    for log in logs[-3:]:
                        msg = (log.get("message") or "")[:80]
                        phase = log.get("phase") or "-"
                        print(f"    [{phase}] {msg}")
            except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
                pass
    else:
        print("\nActive: (no active task)")
    try:
        from project_config import is_task_next_model_hint_enabled

        if is_task_next_model_hint_enabled():
            nxt = svc.task_next(None)
            if nxt:
                ttitle = (nxt.get("title") or "")[:72]
                print(f"\nNext in queue: {nxt['slug']} — {ttitle}")
                mh = nxt.get("model_hint")
                if mh:
                    print(f"  Model hint: {mh['display']} ({mh['model']})")
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        pass
    # Gates
    try:
        from project_config import load_config

        cfg = load_config()
        gates = cfg.get("gates", {})
        enabled = [name for name, g in gates.items() if isinstance(g, dict) and g.get("enabled")]
        disabled = [
            name for name, g in gates.items() if isinstance(g, dict) and not g.get("enabled")
        ]
        print(f"\nGates: {len(enabled)} ON ({', '.join(sorted(enabled)[:6])}), {len(disabled)} OFF")
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        print("\nGates: (config unavailable)")
    print("═══════════════════")


def cmd_suggest_model(svc: ProjectService, args: Any) -> None:
    """Print the recommended Claude model for a given complexity tier."""
    from model_routing import format_suggestion

    print(format_suggestion(getattr(args, "complexity", None)))


def cmd_search(svc: ProjectService, args: Any) -> None:
    results = svc.search(args.query, args.scope, getattr(args, "limit", 20))
    for scope, items in results.items():
        if items:
            print(f"\n--- {scope} ({len(items)} results) ---")
            for item in items:
                if "slug" in item:
                    print(f"  {item['slug']}: {item.get('title', item.get('decision', ''))}")
                else:
                    print(f"  {item.get('title', item.get('decision', str(item)[:80]))}")
                snippet = item.get("_snippet")
                if snippet:
                    print(f"    {snippet}")


def cmd_dead_end(svc: ProjectService, args: Any) -> None:
    print(svc.dead_end(args.approach, args.reason, args.tags, args.task))


def cmd_explore(svc: ProjectService, args: Any) -> None:
    c = args.explore_cmd
    if c == "start":
        print(svc.exploration_start(args.title, args.time_limit))
    elif c == "end":
        print(svc.exploration_end(args.summary, args.create_task))
    elif c == "current":
        exp = svc.exploration_current()
        if exp:
            elapsed = exp.get("elapsed_min", "?")
            limit = exp.get("time_limit_min", 30)
            over = " [OVER LIMIT]" if exp.get("over_limit") else ""
            print(f"Exploration #{exp['id']}: {exp['title']}")
            print(f"  Elapsed: {elapsed} min / {limit} min{over}")
        else:
            print("No active exploration.")
    else:
        print("Usage: tausik explore [start|end|current]")


def cmd_audit(svc: ProjectService, args: Any) -> None:
    c = getattr(args, "audit_cmd", None)
    if c == "mark":
        print(svc.audit_mark())
    elif c == "vendors":
        from project_cli_audit_extra import cmd_audit_vendors

        cmd_audit_vendors(args)
    elif c == "research":
        from project_cli_audit_extra import cmd_audit_research

        cmd_audit_research(args)
    else:
        # Default and "check" -- same behavior
        warning = svc.audit_check()
        if warning:
            print(f"WARNING: {warning}")
        else:
            print("Audit is up to date.")


def cmd_doc(svc: ProjectService, args: Any) -> None:
    """`tausik doc <subcommand>` — extract via markitdown; constants JSON generator."""
    sub = getattr(args, "doc_cmd", None)
    if sub == "constants":
        import gen_doc_constants

        code = gen_doc_constants.run_main(
            gen_doc_constants.find_repo_root(),
            check=bool(getattr(args, "doc_constants_check", False)),
        )
        raise SystemExit(code)
    if sub == "extract":
        import doc_extract

        md = doc_extract.extract_to_markdown(
            args.path, format_hint=getattr(args, "format_hint", None)
        )
        if md is None:
            sys.exit(1)
        print(md)
        return
    print(
        "Usage: tausik doc extract <file> [--format=X] | tausik doc constants [--check]",
        file=sys.stderr,
    )
    sys.exit(2)


def cmd_run(svc: ProjectService, args: Any) -> None:
    """Parse and display a batch-run plan summary."""
    from plan_parser import parse_plan

    plan_file = args.plan_file
    if not os.path.isfile(plan_file):
        print(f"Error: Plan file not found: {plan_file}", file=sys.stderr)
        sys.exit(1)

    with open(plan_file, encoding="utf-8") as f:
        text = f.read()

    plan = parse_plan(text)

    print(f"Plan: {plan.title}")
    if plan.context:
        print(f"Context: {plan.context[:200]}")
    if plan.validation_commands:
        print(f"Validation: {', '.join(plan.validation_commands)}")
    print(f"Tasks: {len(plan.tasks)}")
    for task in plan.tasks:
        done = sum(task.completed)
        total = len(task.steps)
        status = f" ({done}/{total} done)" if total else ""
        print(f"  {task.number}. {task.title}{status}")
        print(f"     Goal: {task.goal}")
        if task.files:
            print(f"     Files: {', '.join(task.files)}")
    print("\nTo execute this plan, use /run in an interactive session.")


def cmd_session_recompute(svc: ProjectService, args: Any) -> None:
    """tausik session recompute — wall vs active minutes for all sessions."""
    import json as _json

    from backend_session_metrics import recompute_all_sessions
    from service_session_metrics import resolve_idle_threshold

    threshold = resolve_idle_threshold(args.threshold)
    rows = recompute_all_sessions(svc.be._q, svc.be._q1, threshold)
    if args.limit:
        rows = rows[-args.limit :]
    if args.json:
        print(_json.dumps({"threshold_min": threshold, "sessions": rows}, indent=2))
        return
    if not rows:
        print("No sessions to recompute.")
        return
    print(f"Idle threshold: {threshold} min  |  showing {len(rows)} session(s)")
    print(f"{'#':>4} {'wall':>6} {'active':>7} {'idle%':>6}  started_at")
    total_wall = 0
    total_active = 0
    for r in rows:
        wall = r["wall_minutes"]
        active = r["active_minutes"]
        total_wall += wall
        total_active += active
        idle_pct = f"{round((1 - active / wall) * 100)}%" if wall > 0 else "  -"
        print(f"{r['id']:>4} {wall:>6} {active:>7} {idle_pct:>6}  {r['started_at']}")
    total_idle = f"{round((1 - total_active / total_wall) * 100)}%" if total_wall > 0 else "  -"
    print(f"{'TOTAL':>4} {total_wall:>6} {total_active:>7} {total_idle:>6}")
