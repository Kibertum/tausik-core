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

from handlers_render import render_list


def _do_epic_list(svc: Any, args: dict) -> str:
    return render_list(
        svc.epic_list(),
        lambda e: f"[{e['status']}] {e['slug']}: {e['title']}",
        "No epics.",
    )


def _do_story_add(svc: Any, args: dict) -> str:
    return svc.story_add(args["epic_slug"], args["slug"], args["title"], args.get("description"))


def _do_story_list(svc: Any, args: dict) -> str:
    return render_list(
        svc.story_list(args.get("epic_slug")),
        lambda s: f"[{s['status']}] {s['slug']}: {s['title']}",
        "No stories.",
    )


def _handle_roadmap(svc: Any, args: dict) -> str:
    data = svc.get_roadmap(args.get("include_done", False))
    if not data:
        return "No epics."
    lines = []
    for epic in data:
        lines.append(f"[{epic['status']}] {epic['slug']}: {epic['title']}")
        for story in epic.get("stories", []):
            lines.append(f"  [{story['status']}] {story['slug']}: {story['title']}")
            for task in story.get("tasks", []):
                lines.append(f"    [{task['status']}] {task['slug']}: {task['title']}")
    return "\n".join(lines)


HIERARCHY_HANDLERS = {
    "tausik_epic_add": lambda svc, args: svc.epic_add(
        args["slug"], args["title"], args.get("description")
    ),
    "tausik_epic_list": _do_epic_list,
    "tausik_epic_done": lambda svc, args: svc.epic_done(args["slug"]),
    "tausik_epic_delete": lambda svc, args: svc.epic_delete(args["slug"]),
    "tausik_story_add": _do_story_add,
    "tausik_story_list": _do_story_list,
    "tausik_story_done": lambda svc, args: svc.story_done(args["slug"]),
    "tausik_story_delete": lambda svc, args: svc.story_delete(args["slug"]),
    "tausik_roadmap": lambda svc, args: _handle_roadmap(svc, args),
}
