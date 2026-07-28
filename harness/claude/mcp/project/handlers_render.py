"""Shared text rendering for MCP handlers.

Almost every list-returning handler in this package ends the same way: format
each row, join with newlines, or say something specific when there is nothing
to show. That last part is the reason this is shared rather than inlined — an
empty result must read as "No tasks found." / "No memories.", not as an empty
string the agent cannot distinguish from a failure.
"""

from __future__ import annotations

from typing import Any, Callable


def render_list(items: list, fmt: Callable[[Any], str], empty_msg: str = "None.") -> str:
    """Render rows with `fmt`, or `empty_msg` when there are none."""
    if not items:
        return empty_msg
    return "\n".join(fmt(item) for item in items)
