"""The text of `search`, `events` and `team`, rendered ONCE for both surfaces.

Each of these was written twice, and in each case the MCP copy showed LESS than
the CLI — which matters more than it sounds, because the agent reads the MCP one:

* `search` — the handler capped every scope at ten hits and dropped the FTS
  snippet, the one part of a search result that says why the row matched.
* `events` — the handler had no rollup, so a long audit log arrived in full, and
  it dropped `details`, the field that says what actually changed.
* `team` — the same lines either way; two copies of an agreement is still two
  copies, and agreement is not a property that maintains itself.

The copies were not deliberate reductions. They were written first and then not
updated when the CLI grew, which is what a second implementation always does.

Lines, not printing: the CLI prints them, the MCP handler joins them.
"""

from __future__ import annotations

from typing import Any

#: `search --limit` default. Named because BOTH surfaces now take it from here;
#: the handler used to carry its own cap of ten, silently narrower.
SEARCH_LIMIT = 20

#: `events --limit` default, likewise shared.
EVENTS_LIMIT = 50


def search_lines(svc: Any, query: str, scope: str = "all", limit: int = SEARCH_LIMIT) -> list[str]:
    """Search hits grouped by scope, with the snippet that explains the match."""
    results = svc.search(query, scope, limit)
    lines: list[str] = []
    for group, items in results.items():
        if not items:
            continue
        if lines:
            lines.append("")
        lines.append(f"--- {group} ({len(items)} results) ---")
        for item in items:
            if "slug" in item:
                title = item.get("title", item.get("decision", ""))
                lines.append(f"  {item['slug']}: {title}")
            elif "query" in item:
                lines.append(f"  {item['query']}")
            else:
                lines.append(f"  {item.get('title', item.get('decision', str(item)[:80]))}")
            snippet = item.get("_snippet")
            if snippet:
                lines.append(f"    {snippet}")
    return lines or ["No results."]


def events_lines(
    svc: Any,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = EVENTS_LIMIT,
    full: bool = False,
    top_n: int | None = None,
    max_lines: int | None = None,
) -> list[str]:
    """The audit log, rolled up unless `full` — an agent's read stays bounded."""
    from output_rollup import render_rollup, should_rollup

    events = svc.events_list(entity_type=entity_type, entity_id=entity_id, n=limit)
    if not events:
        return ["No events found."]
    if should_rollup(len(events), full=full):
        return list(
            render_rollup(
                events,
                ["entity_type", "action"],
                title="Events",
                top_n=top_n,
                max_lines=max_lines,
            )
        )
    lines: list[str] = []
    for ev in events:
        actor = f" by {ev['actor']}" if ev.get("actor") else ""
        lines.append(
            f"[{ev['created_at']}] {ev['entity_type']}/{ev['entity_id']}: {ev['action']}{actor}"
        )
        if ev.get("details"):
            lines.append(f"  {ev['details']}")
    return lines


def team_lines(svc: Any) -> list[str]:
    """Who holds what. Groups are separated by a blank line, not preceded by one."""
    data = svc.team_status()
    if not data:
        return ["No active tasks."]
    lines: list[str] = []
    for group in data:
        if lines:
            lines.append("")
        lines.append(f"{group['agent']}:")
        for task in group["tasks"]:
            lines.append(f"  [{task['status']}] {task['slug']}: {task['title']}")
    return lines
