"""The text of `roadmap`, rendered ONCE for both surfaces.

The epic/story/task tree was printed by the CLI and rebuilt line for line by the
MCP handler. The two agreed when this was collapsed, which is the ordinary case
and not a reason to leave them: agreement between two implementations has to be
re-established after every change, and nothing was checking it.

Lines, not printing: the CLI prints them, the MCP handler joins them.
"""

from __future__ import annotations

from typing import Any


def roadmap_lines(svc: Any, include_done: bool = False) -> list[str]:
    """The whole tree, indented by level."""
    data = svc.get_roadmap(include_done)
    if not data:
        return ["No epics."]
    lines: list[str] = []
    for epic in data:
        lines.append(f"[{epic['status']}] {epic['slug']}: {epic['title']}")
        for story in epic.get("stories", []):
            lines.append(f"  [{story['status']}] {story['slug']}: {story['title']}")
            for task in story.get("tasks", []):
                lines.append(f"    [{task['status']}] {task['slug']}: {task['title']}")
    return lines
