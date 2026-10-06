"""MCP handlers for the hierarchy domain — epics, stories, and the roadmap over them.

Split out of handlers.py by mcp-handlers-god-module-split. Follows the
convention already set by handlers_spec.py / handlers_adapt.py: the module owns
its handlers AND the slice of the dispatch table that names them, and
handlers.py merges it with `_DISPATCH.update(...)`.

The roadmap belongs here rather than with tasks: it is a walk over
epic → story → task, and its whole job is to render that hierarchy. A task
unreachable from an epic is invisible to it — the defect the `Backlog hygiene`
doctor check now names.
"""

from __future__ import annotations

from typing import Any

import hierarchy_edit  # scripts/ — the one implementation the CLI shares
from handlers_render import render_list


def _stale_tag(row: dict) -> str:
    """` (stale: N)` when N tasks arrived after the description was last edited."""
    n = int(row.get("stale", 0))
    return f" (stale: {n})" if n else ""


def _do_epic_list(svc: Any, args: dict) -> str:
    return render_list(
        hierarchy_edit.list_with_staleness(svc, "epics"),
        lambda e: f"[{e['status']}] {e['slug']}: {e['title']}{_stale_tag(e)}",
        "No epics.",
    )


def _do_story_add(svc: Any, args: dict) -> str:
    return svc.story_add(args["epic_slug"], args["slug"], args["title"], args.get("description"))


def _do_story_list(svc: Any, args: dict) -> str:
    return render_list(
        hierarchy_edit.list_with_staleness(svc, "stories", args.get("epic_slug")),
        lambda s: f"[{s['status']}] {s['slug']}: {s['title']}{_stale_tag(s)}",
        "No stories.",
    )


def _handle_roadmap(svc: Any, args: dict) -> str:
    from render_hierarchy import roadmap_lines

    return "\n".join(roadmap_lines(svc, args.get("include_done", False)))


def _done_with_optional_handle(svc: Any, args: dict, kind: str) -> str:
    handle = args.get("verify_handle")
    if handle:
        from verify_hierarchy import hierarchy_done_with_handle

        return hierarchy_done_with_handle(svc, args["slug"], kind, handle)
    return (svc.epic_done if kind == "epic" else svc.story_done)(args["slug"])


def _handle_verify_hierarchy(svc: Any, args: dict) -> str:
    from verify_hierarchy import hierarchy_summary, run_hierarchy_verify

    return hierarchy_summary(run_hierarchy_verify(svc, args["slug"], args["kind"]))


def _handle_verify_cohort(svc: Any, args: dict) -> str:
    from verify_cohort import cohort_summary, run_cohort_verify

    return cohort_summary(run_cohort_verify(svc, args["tasks"]))


HIERARCHY_HANDLERS = {
    "tausik_epic_add": lambda svc, args: svc.epic_add(
        args["slug"], args["title"], args.get("description")
    ),
    "tausik_epic_list": _do_epic_list,
    "tausik_epic_update": lambda svc, args: hierarchy_edit.update(
        svc, "epics", args["slug"], args.get("title"), args.get("description")
    ),
    "tausik_epic_done": lambda svc, args: _done_with_optional_handle(svc, args, "epic"),
    "tausik_epic_delete": lambda svc, args: svc.epic_delete(args["slug"]),
    "tausik_story_add": _do_story_add,
    "tausik_story_list": _do_story_list,
    "tausik_story_update": lambda svc, args: hierarchy_edit.update(
        svc, "stories", args["slug"], args.get("title"), args.get("description")
    ),
    "tausik_story_done": lambda svc, args: _done_with_optional_handle(svc, args, "story"),
    "tausik_story_delete": lambda svc, args: svc.story_delete(args["slug"]),
    "tausik_roadmap": lambda svc, args: _handle_roadmap(svc, args),
    "tausik_verify_hierarchy": _handle_verify_hierarchy,
    "tausik_verify_cohort": _handle_verify_cohort,
}
