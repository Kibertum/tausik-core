"""MCP handlers for the status domain — what this project and this server are right now.

Split out of handlers.py by mcp-handlers-god-module-split. Follows the
convention already set by handlers_spec.py / handlers_adapt.py: the module owns
its handlers AND the slice of the dispatch table that names them, and
handlers.py merges it with `_DISPATCH.update(...)`.

Health, self-check, status, metrics, search and the event log answer one
question in different resolutions — "what is true here now" — which is also why
handlers_session.py composes `_handle_status` and `_handle_self_check` into the
session_open envelope rather than duplicating them.
"""

from __future__ import annotations

import json
from typing import Any


def _handle_health(svc: Any) -> str:
    from tausik_version import __version__

    try:
        info = svc.be.health_info()
        return json.dumps(
            {
                "status": "ok",
                "version": __version__,
                "schema_version": info["schema_version"],
                "tables": info["tables"],
            }
        )
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return json.dumps({"status": "error", "error": str(e)})


def _handle_self_check() -> str:
    """v14b-mcp-stale-module-detector — return MCP-server freshness report."""
    try:
        import self_check  # type: ignore[import-not-found]

        return json.dumps(self_check.collect(), ensure_ascii=False, default=str)
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return json.dumps(
            {
                "server": "tausik-project",
                "drift_detected": None,
                "error": f"self_check unavailable: {e}",
                "remediation": (
                    "self_check module failed to load — likely an old MCP "
                    "server. Restart IDE so a fresh server boots with the "
                    "diagnostic available."
                ),
            },
            ensure_ascii=False,
        )


def _handle_status(svc: Any, args: dict | None = None) -> str:
    # status-cli-mcp-divergence: both channels render from the shared
    # status_view so the CLI and the MCP handler surface the SAME signal set
    # (this handler used to hide risk / RENAR / epics / calibration / capacity
    # that the CLI showed). build_status_view already reads config scoped to
    # svc.tausik_dir() — the mcp-config-read-paths-ignore-project-handle fix.
    from status_view import build_status_view, render_status_mcp
    from tausik_utils import format_status_compact_json

    args = args or {}
    compact = bool(args.get("compact"))
    view = build_status_view(svc, verbose=bool(args.get("verbose")), include_rich=not compact)
    if compact:
        return format_status_compact_json(view["data"], view["duration_warning"])
    return render_status_mcp(view)


def _handle_metrics(svc: Any) -> str:
    m = svc.get_metrics()
    parts = [f"Tasks: {m['tasks_done']}/{m['tasks_total']} ({m['completion_pct']}%)"]
    if m["avg_task_hours"]:
        parts.append(f"Avg time: {m['avg_task_hours']}h")
    parts.append(f"Sessions: {m['sessions_total']} ({m['session_hours']}h)")
    return ", ".join(parts)


def _handle_search(svc: Any, args: dict) -> str:
    results = svc.search(args["query"], args.get("scope", "all"))
    lines = []
    for scope, items in results.items():
        if items:
            lines.append(f"--- {scope} ({len(items)}) ---")
            for item in items[:10]:
                if "slug" in item:
                    lines.append(f"  {item['slug']}: {item.get('title', item.get('decision', ''))}")
                elif "query" in item:
                    lines.append(f"  {item['query']}")
                else:
                    lines.append(f"  {item.get('title', str(item)[:80])}")
    return "\n".join(lines) if lines else "No results."


def _handle_events(svc: Any, args: dict) -> str:
    events = svc.events_list(
        entity_type=args.get("entity_type"),
        entity_id=args.get("entity_id"),
        n=args.get("limit", 50),
    )
    if not events:
        return "No events."
    lines = []
    for ev in events:
        actor = f" by {ev['actor']}" if ev.get("actor") else ""
        lines.append(
            f"[{ev['created_at']}] {ev['entity_type']}/{ev['entity_id']}: {ev['action']}{actor}"
        )
    return "\n".join(lines)


def _do_team(svc: Any, args: dict) -> str:
    data = svc.team_status()
    if not data:
        return "No active tasks."
    lines = []
    for group in data:
        lines.append(f"{group['agent']}:")
        for t in group["tasks"]:
            lines.append(f"  [{t['status']}] {t['slug']}: {t['title']}")
    return "\n".join(lines)


def _do_usage_event_log(svc: Any, args: dict) -> str:
    from tausik_utils import ServiceError

    required = ("tokens_input", "tokens_output", "tokens_total", "cost_usd")
    missing = [k for k in required if k not in args]
    if missing:
        return f"Error: missing required fields: {', '.join(missing)}"

    try:
        return svc.metrics_log_usage_event(
            tokens_input=int(args["tokens_input"]),
            tokens_output=int(args["tokens_output"]),
            tokens_total=int(args["tokens_total"]),
            cost_usd=float(args["cost_usd"]),
            tool_calls=int(args.get("tool_calls") or 0),
            model=str(args.get("model") or ""),
            task_slug=args.get("task_slug"),
            session_id=args.get("session_id"),
        )
    except ServiceError as e:
        return f"Error: {e}"


def _do_snippet_search(svc: Any, args: dict) -> str:
    """Ranked FTS5 search over reusable snippets — JSON envelope for the agent."""
    from snippet_storage import search_snippets_ranked

    query = args.get("query", "")
    language = args.get("language")
    raw_limit = args.get("limit")
    if isinstance(raw_limit, bool):
        limit = 20  # bool is an int subclass — reject True/False as a count
    elif isinstance(raw_limit, (int, float)):
        limit = int(raw_limit)
    elif isinstance(raw_limit, str) and raw_limit.strip().lstrip("-").isdigit():
        limit = int(raw_limit)
    else:
        limit = 20  # missing / non-numeric -> default (never crashes the tool)
    results = search_snippets_ranked(svc.be._conn, query, language=language, limit=limit)
    return json.dumps(
        {"query": query, "language": language, "count": len(results), "results": results},
        ensure_ascii=False,
        indent=2,
    )


STATUS_HANDLERS = {
    "tausik_health": lambda svc, args: _handle_health(svc),
    "tausik_self_check": lambda svc, args: _handle_self_check(),
    "tausik_status": lambda svc, args: _handle_status(svc, args),
    "tausik_metrics": lambda svc, args: _handle_metrics(svc),
    "tausik_usage_event_log": _do_usage_event_log,
    "tausik_search": lambda svc, args: _handle_search(svc, args),
    "tausik_snippet_search": _do_snippet_search,
    "tausik_events": lambda svc, args: _handle_events(svc, args),
    "tausik_team": _do_team,
}
