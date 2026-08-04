"""TAUSIK CLI handlers with no module of their own yet — hud, suggest-model,
search, dead-end, explore, doc, run, session-recompute.

NOT a domain. This module is the residue of repeated bleeding to satisfy the
filesize gate — brain_cli_ops.py, project_cli_events.py and
project_cli_metrics.py each say so in their own docstrings. The two commands
whose domain module already existed (metrics, audit) have been moved back to
it; the rest await a per-command split tracked as
cli-ops-residue-split-by-command. Do not add new commands here — create
project_cli_<command>.py, which is what 24 of this family's 26 modules do.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from brain_cli_ops import cmd_brain  # noqa: F401  re-exported for project.py
from project_service import ProjectService


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


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
