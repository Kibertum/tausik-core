"""TAUSIK CLI handlers -- metrics, search, events, explore, audit, run, dead-end, brain commands."""

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


def cmd_brain(svc: ProjectService, args: Any) -> None:
    """`tausik brain <subcommand>` — init wizard, status."""
    sub = getattr(args, "brain_cmd", None)
    if sub == "status":
        import json as _json

        import brain_status

        snapshot = brain_status.collect_status()
        if getattr(args, "as_json", False):
            print(_json.dumps(snapshot, indent=2, ensure_ascii=False))
        else:
            print(brain_status.format_status(snapshot))
        return
    if sub == "move":
        import json as _json

        import brain_move

        if getattr(args, "to_brain", False):
            kind = getattr(args, "kind", None)
            if not kind:
                print("Error: --kind is required with --to-brain", file=sys.stderr)
                sys.exit(2)
            try:
                src_id = int(args.source_id)
            except (TypeError, ValueError):
                print(
                    f"Error: source_id must be an integer, got {args.source_id!r}",
                    file=sys.stderr,
                )
                sys.exit(2)
            result = brain_move.move_to_brain(
                svc, kind, src_id, keep_source=args.keep_source
            )
        else:
            cat = getattr(args, "category", None)
            if not cat:
                print("Error: --category is required with --to-local", file=sys.stderr)
                sys.exit(2)
            result = brain_move.move_to_local(
                svc,
                args.source_id,
                cat,
                force=args.force,
                keep_source=args.keep_source,
            )
        print(_json.dumps(result, indent=2, ensure_ascii=False))
        if result.get("status") not in ("ok",):
            sys.exit(1 if result.get("status") in ("failed", "not_found") else 0)
        return
    if sub != "init":
        print(
            "Usage:\n"
            "  tausik brain init [--parent-page-id X] [--token-env Y] "
            "[--project-name Z] [--yes] [--force] [--non-interactive]\n"
            "  tausik brain status [--json]",
            file=sys.stderr,
        )
        sys.exit(1)

    import brain_init
    from brain_notion_client import NotionClient
    from project_config import load_config, save_config

    class _ConfigOps:
        def load(self) -> dict:
            return load_config()

        def save(self, cfg: dict) -> None:
            save_config(cfg)

    def _factory(token: str):
        return NotionClient(token)

    interactive = None
    if getattr(args, "non_interactive", False):
        interactive = False

    wizard_args = {
        "parent_page_id": getattr(args, "parent_page_id", None),
        "token_env": getattr(args, "token_env", None),
        "project_name": getattr(args, "project_name", None),
        "yes": getattr(args, "yes", False),
        "force": getattr(args, "force", False),
        "interactive": interactive,
    }

    try:
        result = brain_init.run_wizard(
            wizard_args, brain_init.CliIO(), _factory, _ConfigOps()
        )
    except brain_init.WizardError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nBrain initialized.")
    print(f"  parent_page_id: {result['parent_page_id']}")
    print(f"  token_env:      {result['token_env']}")
    print(f"  project_name:   {result['project_name']}")
    for cat, db_id in result["database_ids"].items():
        print(f"  {cat:>10}: {db_id}")


def cmd_doc(svc: ProjectService, args: Any) -> None:
    """`tausik doc <subcommand>` — optional document extraction via markitdown."""
    sub = getattr(args, "doc_cmd", None)
    if sub != "extract":
        print(
            "Usage: tausik doc extract <file> [--format=X]",
            file=sys.stderr,
        )
        sys.exit(2)
    import doc_extract

    md = doc_extract.extract_to_markdown(
        args.path, format_hint=getattr(args, "format_hint", None)
    )
    if md is None:
        sys.exit(1)
    print(md)


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
