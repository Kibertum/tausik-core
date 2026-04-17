"""TAUSIK CLI handlers -- metrics, search, events, explore, audit, run, dead-end commands."""

from __future__ import annotations

import os
import sys
from typing import Any

from project_service import ProjectService


def cmd_metrics(svc: ProjectService, args: Any) -> None:
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
    print(f"\nSessions: {m['sessions_total']} ({m['session_hours']}h total)")
    if m["stories"]:
        total_s = sum(m["stories"].values())
        done_s = m["stories"].get("done", 0)
        print(f"Stories: {done_s}/{total_s} done")


def cmd_hud(svc: ProjectService, args: Any) -> None:
    """Live dashboard: active task + session + gates + recent logs.

    Compact one-screen view for quick situational awareness.
    """
    print("═══ TAUSIK HUD ═══")
    # Session
    try:
        session = svc.session_current()
    except Exception:
        session = None
    if session:
        print(
            f"Session: #{session.get('id', '?')} started {session.get('started_at', '')}"
        )
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
            except Exception:
                pass
            try:
                logs = svc.task_logs(slug)
                if logs:
                    print("  Recent logs:")
                    for log in logs[-3:]:
                        msg = (log.get("message") or "")[:80]
                        phase = log.get("phase") or "-"
                        print(f"    [{phase}] {msg}")
            except Exception:
                pass
    else:
        print("\nActive: (no active task)")
    # Gates
    try:
        from project_config import load_config

        cfg = load_config()
        gates = cfg.get("gates", {})
        enabled = [
            name
            for name, g in gates.items()
            if isinstance(g, dict) and g.get("enabled")
        ]
        disabled = [
            name
            for name, g in gates.items()
            if isinstance(g, dict) and not g.get("enabled")
        ]
        print(
            f"\nGates: {len(enabled)} ON ({', '.join(sorted(enabled)[:6])}), {len(disabled)} OFF"
        )
    except Exception:
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
                    print(
                        f"  {item['slug']}: {item.get('title', item.get('decision', ''))}"
                    )
                else:
                    print(
                        f"  {item.get('title', item.get('decision', str(item)[:80]))}"
                    )
                snippet = item.get("_snippet")
                if snippet:
                    print(f"    {snippet}")


def cmd_events(svc: ProjectService, args: Any) -> None:
    events = svc.events_list(
        entity_type=args.entity,
        entity_id=args.entity_id,
        n=args.limit,
    )
    if not events:
        print("No events found.")
        return
    for ev in events:
        actor = f" by {ev['actor']}" if ev.get("actor") else ""
        print(
            f"[{ev['created_at']}] {ev['entity_type']}/{ev['entity_id']}: "
            f"{ev['action']}{actor}"
        )
        if ev.get("details"):
            print(f"  {ev['details']}")


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
    else:
        # Default and "check" -- same behavior
        warning = svc.audit_check()
        if warning:
            print(f"WARNING: {warning}")
        else:
            print("Audit is up to date.")


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
