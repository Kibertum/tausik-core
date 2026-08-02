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
    # status-cli-mcp-divergence: render from the shared status_view so the CLI
    # and the MCP handler surface the SAME signal set. build_status_view reads
    # config exactly once (scoped to svc.tausik_dir(), not the process cwd) —
    # the CLI's former three load_config() calls all resolved off the cwd.
    from status_view import build_status_view, render_status_cli

    td = svc.tausik_dir() if hasattr(svc, "tausik_dir") else None
    if getattr(args, "compact", False):
        view = build_status_view(svc, tausik_dir=td, include_rich=False)
        print(format_status_compact_json(view["data"], view["duration_warning"]))
        return
    view = build_status_view(svc, verbose=bool(getattr(args, "verbose", False)), tausik_dir=td)
    print(render_status_cli(view))


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
    print(svc.decide(args.text, args.task, args.rationale, getattr(args, "to_global", False)))


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


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
