"""The current session: what it is, what it advises, and its recomputed numbers.

Carved out of `project_cli_ops.py`, whose own docstring said "NOT a domain ... the
residue of repeated bleeding to satisfy the filesize gate". The family has 33
modules and 31 were already named after a command or a domain; these three
handlers share one subject, so the subject gets the name.
"""

from __future__ import annotations

from typing import Any
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


def cmd_session_recompute(svc: ProjectService, args: Any) -> None:
    """tausik session recompute — wall vs active minutes for all sessions."""
    import json as _json

    from backend_session_metrics import recompute_all_sessions
    from service_session_metrics import resolve_idle_threshold

    threshold = resolve_idle_threshold(args.threshold)
    rows = recompute_all_sessions(svc.be._q, svc.be._q1, threshold)
    if args.limit:
        rows = rows[-args.limit :]
    from project_config import DEFAULT_SESSION_MAX_MINUTES, load_config
    from session_pressure import summary

    advisory = int(load_config().get("session_max_minutes", DEFAULT_SESSION_MAX_MINUTES))
    stats = summary(rows, advisory)
    if args.json:
        print(
            _json.dumps({"threshold_min": threshold, "summary": stats, "sessions": rows}, indent=2)
        )
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
    # The basis a self-set threshold owes (SENAR 1.5 §9.4(c)), as a command's
    # output rather than a remembered number.
    print(
        f"SUMMARY active minutes over {stats['sessions']} session(s): "
        f"median {stats.get('median_active')}, p90 {stats.get('p90_active')}, "
        f"max {stats.get('max_active')}; above the {advisory}-min advisory "
        f"threshold: {stats.get('over_threshold')}"
    )


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
