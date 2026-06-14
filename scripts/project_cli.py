"""TAUSIK CLI handlers — dispatch + formatting for core commands."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from project_config import find_tausik_dir, get_config_path, save_config
from project_service import ProjectService
from tausik_utils import format_status_compact_json


def _print_table(rows: list[dict[str, Any]], columns: list[str]) -> None:
    """Print a simple table."""
    if not rows:
        print("  (none)")
        return
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in columns}
    header = "  ".join(c.ljust(widths[c]) for c in columns)
    print(header)
    print("-" * len(header))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns))


def cmd_init(svc: ProjectService, args: Any) -> None:
    """Initialize TAUSIK project."""
    import re

    template = getattr(args, "template", None)
    if template:
        from project_cli_aidd import cmd_init_template

        rc = cmd_init_template(template, force=getattr(args, "force", False))
        if rc != 0:
            sys.exit(rc)
        return

    name = args.name
    if not name:
        # Derive from directory name: "My Project" -> "my-project"
        raw = os.path.basename(os.getcwd())
        name = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-") or "my-project"
    tausik_dir = find_tausik_dir()
    os.makedirs(tausik_dir, exist_ok=True)
    cfg_path = get_config_path()
    if not os.path.exists(cfg_path):
        save_config({"project": name, "version": 1})
        print(f"Config created: {cfg_path}")
    else:
        print(f"Config already exists: {cfg_path}")
    print(f"Database: {os.path.join(tausik_dir, 'tausik.db')}")
    print(f"Project '{name}' initialized.")


def cmd_aidd(svc: ProjectService, args: Any) -> None:
    """AIDD layer commands. Dispatches on the `aidd_command` subcommand."""
    sub = getattr(args, "aidd_command", None)
    if sub == "autogen":
        from project_cli_aidd_autogen import cmd_aidd_autogen

        rc = cmd_aidd_autogen(
            write=getattr(args, "write", False),
            force=getattr(args, "force", False),
        )
        if rc != 0:
            sys.exit(rc)
        return
    if sub == "validate":
        from project_cli_aidd_validate import cmd_aidd_validate

        rc = cmd_aidd_validate()
        if rc != 0:
            sys.exit(rc)
        return
    print("Usage: tausik aidd {autogen,validate}", file=sys.stderr)
    sys.exit(2)


def cmd_status(svc: ProjectService, args: Any) -> None:
    data = svc.get_status()
    if getattr(args, "compact", False):
        from project_config import DEFAULT_SESSION_MAX_MINUTES, load_config

        cfg = load_config()
        max_min = cfg.get("session_max_minutes", DEFAULT_SESSION_MAX_MINUTES)
        warning = svc.session_check_duration(max_min)
        print(format_status_compact_json(data, warning))
        return
    counts = data["task_counts"]
    total = sum(counts.values())
    done = counts.get("done", 0)
    print(f"Tasks: {done}/{total} done", end="")
    for st in ("planning", "active", "blocked", "review"):
        if counts.get(st):
            print(f", {counts[st]} {st}", end="")
    print()
    # v15-risk-surface-metrics: one-line closure risk, only when scored rows exist.
    try:
        from risk_metrics import format_risk_status_line, risk_summary

        _risk = risk_summary(svc.be._conn)
        if _risk:
            print(format_risk_status_line(_risk))
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        pass
    try:
        # Best-effort RENAR adoption level (rich status only — kept off the
        # compact JSON hot path to avoid per-call signal queries). Display-only;
        # a failure must never break `status`.
        from renar_conformance import current_level, format_status_line

        print(format_status_line(current_level(svc.be._conn)))
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        pass
    if data["session"]:
        active = svc.session_active_minutes()
        wall = svc.session_wall_minutes()
        # SENAR Rule 9.2 metric is active; wall is informational under --verbose
        # only. v14b-session-active-time: lead with `active / limit` so the
        # primary signal is the limit progress, not idle ratio.
        from project_config import DEFAULT_SESSION_MAX_MINUTES, load_config

        cfg = load_config()
        max_min = cfg.get("session_max_minutes", DEFAULT_SESSION_MAX_MINUTES)
        verbose = bool(getattr(args, "verbose", False))
        if verbose:
            idle_pct = (
                f", {round((1 - active / wall) * 100)}% idle" if wall > 0 and active < wall else ""
            )
            sess_line = (
                f"Session: #{data['session']['id']} "
                f"(active {active}m / {max_min}m, wall {wall}m{idle_pct})"
            )
        else:
            sess_line = f"Session: #{data['session']['id']} (active {active}m / {max_min}m)"
        print(sess_line)
        warning = svc.session_check_duration(max_min)
        if warning:
            print(f"  WARNING: {warning}")
    else:
        print("Session: none active")
    if data["epics"]:
        print(f"Epics: {len(data['epics'])}")
    drift = svc.get_metrics().get("calibration_drift")
    if drift:
        print(
            f"Calibration: {drift['label']} "
            f"(actual/budget={drift['avg_ratio']}, n={drift['samples']})"
        )
    if data["session"]:
        from project_config import DEFAULT_SESSION_CAPACITY_CALLS, load_config

        cfg2 = load_config()
        cap = cfg2.get("session_capacity_calls", DEFAULT_SESSION_CAPACITY_CALLS)
        cs = svc.be.session_capacity_summary(cap)
        marker = " ⚠ overshoot" if cs["remaining"] < 0 else ""
        print(
            f"Capacity: {cs['used']}/{cs['capacity']} used, "
            f"{cs['planned_active']} planned, {cs['remaining']} remaining{marker}"
        )

    # v14b-skill-core-cleanup: surface a one-line nudge when the deployed
    # skill set is well above the v1.4 default of 12 (counting brain when
    # gated). Helps users notice the new opt-in default without reading
    # changelog. The message points to safe migration paths only — no
    # automatic mutation.
    _maybe_print_skill_set_warning()


def _maybe_print_skill_set_warning() -> None:
    """Warn when .claude/skills/ holds many more skills than v1.4 default."""
    skills_dir = os.path.join(".claude", "skills")
    if not os.path.isdir(skills_dir):
        return
    try:
        deployed = [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))]
    except OSError:
        return
    n = len(deployed)
    # Default 12 + brain conditional + small slack for explicitly installed.
    if n <= 14:
        return
    print(
        f"  WARNING: Skills: {n} deployed (v1.4 default = 12 core + 1 conditional). "
        "Re-bootstrap to shrink: `python bootstrap/bootstrap.py --ide claude` "
        "(use `--include-official` to keep registry stubs). Per-skill: "
        "`tausik skill activate <name>`."
    )


def cmd_epic(svc: ProjectService, args: Any) -> None:
    if args.epic_cmd == "add":
        print(svc.epic_add(args.slug, args.title, args.description))
    elif args.epic_cmd == "list":
        _print_table(svc.epic_list(), ["slug", "title", "status"])
    elif args.epic_cmd == "done":
        print(svc.epic_done(args.slug))
    elif args.epic_cmd == "delete":
        print(svc.epic_delete(args.slug))
    else:
        print("Usage: tausik epic [add|list|done|delete]")


def cmd_story(svc: ProjectService, args: Any) -> None:
    if args.story_cmd == "add":
        print(svc.story_add(args.epic_slug, args.slug, args.title, args.description))
    elif args.story_cmd == "list":
        _print_table(svc.story_list(args.epic), ["slug", "title", "status", "epic_slug"])
    elif args.story_cmd == "done":
        print(svc.story_done(args.slug))
    elif args.story_cmd == "delete":
        print(svc.story_delete(args.slug))
    else:
        print("Usage: tausik story [add|list|done|delete]")


# cmd_task -> moved to project_cli_task.py (filesize-debt-paydown-2)
from project_cli_task import cmd_task  # noqa: E402,F401


def cmd_team(svc: ProjectService, args: Any) -> None:
    data = svc.team_status()
    if not data:
        print("No active tasks.")
        return
    for group in data:
        print(f"\n{group['agent']}:")
        for t in group["tasks"]:
            print(f"  [{t['status']}] {t['slug']}: {t['title']}")


def cmd_session(svc: ProjectService, args: Any) -> None:
    c = args.session_cmd
    if c == "start":
        print(svc.session_start())
    elif c == "end":
        print(svc.session_end(args.summary))
    elif c == "current":
        s = svc.session_current()
        if s:
            print(f"Session #{s['id']} started {s['started_at']}")
        else:
            print("No active session.")
    elif c == "list":
        sessions = svc.session_list(args.limit)
        _print_table(sessions, ["id", "started_at", "ended_at", "summary"])
    elif c == "handoff":
        try:
            data = json.loads(args.json_data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error: invalid JSON for handoff: {e}", file=sys.stderr)
            return
        print(svc.session_handoff(data))
    elif c == "last-handoff":
        ho = svc.session_last_handoff()
        if ho:
            print(json.dumps(ho, indent=2, ensure_ascii=False))
        else:
            print("No handoff found.")
    elif c == "extend":
        print(svc.session_extend(args.minutes))
    elif c == "recompute":
        from project_cli_ops import cmd_session_recompute

        cmd_session_recompute(svc, args)
    else:
        print(
            "Usage: tausik session [start|end|current|list|handoff|last-handoff|extend|recompute]"
        )


def cmd_decide(svc: ProjectService, args: Any) -> None:
    print(svc.decide(args.text, args.task, args.rationale))


def cmd_decisions(svc: ProjectService, args: Any) -> None:
    _print_table(svc.decisions(args.limit), ["id", "decision", "task_slug", "created_at"])


def cmd_roadmap(svc: ProjectService, args: Any) -> None:
    data = svc.get_roadmap(args.include_done)
    if not data:
        print("No epics.")
        return
    for epic in data:
        print(f"[{epic['status']}] {epic['slug']}: {epic['title']}")
        for story in epic.get("stories", []):
            print(f"  [{story['status']}] {story['slug']}: {story['title']}")
            for task in story.get("tasks", []):
                print(f"    [{task['status']}] {task['slug']}: {task['title']}")


# cmd_metrics, cmd_search, cmd_events, cmd_dead_end, cmd_explore, cmd_audit, cmd_run
# -> moved to project_cli_extra.py


# _print_with_warnings, _auto_slug, _print_task_detail
# -> moved to project_cli_task.py (filesize-debt-paydown-2)
