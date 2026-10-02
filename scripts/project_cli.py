"""TAUSIK CLI handlers — dispatch + formatting for core commands."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import hierarchy_edit  # one implementation for CLI and MCP; see its docstring
from project_config import TAUSIK_DIR, find_tausik_dir, get_config_path, save_config
from project_service import ProjectService
from tausik_utils import ServiceError, format_status_compact_json


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


def _init_target(here: bool) -> str:
    """Куда `init` РАЗВОРАЧИВАЕТ проект — всегда текущий каталог.

    Раньше здесь стоял `find_tausik_dir()`, то есть init ИСКАЛ вместо того,
    чтобы СОЗДАВАТЬ. Поиск отдавал ему первый `.tausik` выше по дереву, и в
    пустом каталоге команда печатала «Project 'probe' initialized», не создав
    ничего: конфигурация и база оставались чужими. Сообщение об успехе было
    ложным — самый дорогой вид тихого отказа, потому что проверять его никто не
    станет.

    Усыновление предка — это отдельный вопрос, и на него отвечают вслух. Если
    текущий каталог лежит ВНУТРИ другого проекта, второй проект рядом обычно не
    нужен: у него будет своя база, и половина работы уедет не туда. Поэтому
    отказ называет найденный корень, а `--here` остаётся для тех, кому вложенный
    проект нужен на самом деле.
    """
    target = os.path.join(os.getcwd(), TAUSIK_DIR)
    if os.path.isdir(target) or here:
        return target
    enclosing = find_tausik_dir()
    if not os.path.isdir(enclosing):
        return target
    raise ServiceError(
        f"Текущий каталог уже внутри проекта TAUSIK: {os.path.dirname(enclosing)}\n"
        "Ничего не создано. Вложенный проект завёл бы ВТОРУЮ базу, и часть работы "
        "уехала бы в неё незаметно.\n"
        "Работайте в найденном проекте, либо повторите с `--here`, если вложенный "
        "проект нужен намеренно."
    )


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
    tausik_dir = _init_target(here=getattr(args, "here", False))
    os.makedirs(tausik_dir, exist_ok=True)
    cfg_path = get_config_path(tausik_dir)
    if not os.path.exists(cfg_path):
        save_config({"project": name, "version": 1}, tausik_dir)
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


def _stale_rows(rows: list[dict[str, Any]], args: Any) -> list[dict[str, Any]]:
    """`--stale-over N` keeps rows whose description fell behind by more than N tasks.

    N is None when the flag is absent: every row prints with its number — the
    report names, it never hides, and it is not a gate anywhere. An explicit
    `--stale-over 0` is a filter like any other N: rows with stale > 0.
    """
    over = getattr(args, "stale_over", None)
    if over is None:
        return rows
    return [r for r in rows if int(r.get("stale", 0)) > int(over)]


def cmd_epic(svc: ProjectService, args: Any) -> None:
    if args.epic_cmd == "add":
        print(svc.epic_add(args.slug, args.title, args.description))
    elif args.epic_cmd == "list":
        rows = _stale_rows(hierarchy_edit.list_with_staleness(svc, "epics"), args)
        _print_table(rows, ["slug", "title", "status", "stale"])
    elif args.epic_cmd == "update":
        print(hierarchy_edit.update(svc, "epics", args.slug, args.title, args.description))
    elif args.epic_cmd == "done":
        print(svc.epic_done(args.slug))
    elif args.epic_cmd == "delete":
        print(svc.epic_delete(args.slug))
    else:
        print("Usage: tausik epic [add|list|update|done|delete]")


def cmd_story(svc: ProjectService, args: Any) -> None:
    if args.story_cmd == "add":
        print(svc.story_add(args.epic_slug, args.slug, args.title, args.description))
    elif args.story_cmd == "list":
        rows = _stale_rows(hierarchy_edit.list_with_staleness(svc, "stories", args.epic), args)
        _print_table(rows, ["slug", "title", "status", "epic_slug", "stale"])
    elif args.story_cmd == "update":
        print(hierarchy_edit.update(svc, "stories", args.slug, args.title, args.description))
    elif args.story_cmd == "done":
        print(svc.story_done(args.slug))
    elif args.story_cmd == "delete":
        print(svc.story_delete(args.slug))
    else:
        print("Usage: tausik story [add|list|update|done|delete]")


# cmd_task -> moved to project_cli_task.py (filesize-debt-paydown-2)
from project_cli_task import cmd_task  # noqa: E402,F401


def cmd_team(svc: ProjectService, args: Any) -> None:
    from render_status import team_lines

    print("\n".join(team_lines(svc)))


def cmd_session(svc: ProjectService, args: Any) -> None:
    c = args.session_cmd
    if c == "start":
        host_id = getattr(args, "host_id", None)
        if host_id:
            from service_host_context import native_identity, open_session

            host, native_thread = native_identity()
            result = open_session(
                svc,
                host=host or "unknown-host",
                thread_id=host_id or native_thread,
            )
            session = result.get("session")
            if isinstance(session, dict):
                result["session"] = {
                    key: session.get(key)
                    for key in ("id", "started_at", "ended_at", "host_session_id")
                }
            print(json.dumps(result, ensure_ascii=False, default=str))
        else:
            print(svc.session_start())
    elif c == "end":
        print(svc.session_end(args.summary, getattr(args, "host_id", None)))
    elif c == "current":
        from render_session import session_current_line

        print(session_current_line(svc))
    elif c == "list":
        sessions = svc.session_list(args.limit)
        for s in sessions:
            s["handoff"] = "yes" if s.get("handoff") else "-"
        _print_table(sessions, ["id", "started_at", "ended_at", "handoff", "summary"])
    elif c == "handoff":
        data = None
        if args.json_data:
            try:
                data = json.loads(args.json_data)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error: invalid JSON for handoff: {e}", file=sys.stderr)
                return
        print(svc.session_handoff(data, getattr(args, "host_id", None)))
    elif c == "last-handoff":
        ho = svc.session_last_handoff(getattr(args, "session", None))
        if ho:
            print(json.dumps(ho, indent=2, ensure_ascii=False))
        else:
            print("No handoff found.")
    elif c == "extend":
        print(svc.session_extend(args.minutes))
    elif c == "recompute":
        from project_cli_session import cmd_session_recompute

        cmd_session_recompute(svc, args)
    else:
        print(
            "Usage: tausik session [start|end|current|list|handoff|last-handoff|extend|recompute]"
        )


def cmd_decide(svc: ProjectService, args: Any) -> None:
    rationale = args.rationale or getattr(args, "because", None)
    print(
        svc.decide(
            args.text,
            args.task,
            rationale,
            getattr(args, "to_global", False),
            getattr(args, "rejected", None),
            getattr(args, "supersedes", None),
        )
    )


def cmd_decisions(svc: ProjectService, args: Any) -> None:
    rows = svc.decisions(
        args.limit,
        getattr(args, "status", "all"),
        getattr(args, "task", None),
        getattr(args, "rejected", None),
    )
    cols = ["id", "decision", "task_slug", "superseded_by", "created_at"]
    if getattr(args, "rejected", None):
        cols.insert(2, "rejected")
    _print_table(rows, cols)


def cmd_roadmap(svc: ProjectService, args: Any) -> None:
    from render_hierarchy import roadmap_lines

    print("\n".join(roadmap_lines(svc, args.include_done)))


# cmd_metrics, cmd_search, cmd_events, cmd_dead_end, cmd_explore, cmd_audit, cmd_run
# -> moved to project_cli_knowledge.py


# _print_with_warnings, _auto_slug, _print_task_detail
# -> moved to project_cli_task.py (filesize-debt-paydown-2)


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
