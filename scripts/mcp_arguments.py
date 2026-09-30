"""One answer to "what may this MCP tool be called with", for every TAUSIK server.

mcp-server-drops-unknown-arguments-silently fixed the project server: an
undeclared argument used to be dropped on the floor, so a typo in a parameter
name was indistinguishable from success (`story` for `story_slug` created seven
tasks with no story). sibling-mcp-servers-still-drop-unknown-arguments found the
codebase-rag server doing the same, and a copy of the guard there would have
been the second list of names the original task forbade. So the guard lives
here, once, and both servers import it.

A tool may be given as a dict (the project server's `tools.py`) or as an `mcp`
`Tool` object (the rag server's `rag_tools.py`); both are read the same way.
"""

from __future__ import annotations

import difflib
from typing import Any


def _field(tool: Any, key: str) -> Any:
    return tool.get(key) if isinstance(tool, dict) else getattr(tool, key, None)


def declared_arguments(tools: list[Any], name: str) -> tuple[dict, set] | None:
    """The (properties, required) a tool's inputSchema declares, or None if unknown.

    The single unfolding of a tool schema. Both the usage line and the
    unknown-argument check read it, so there is exactly one answer to "what may
    this tool be called with".

    None means the schema knows nothing about `name`. That is not the same as
    "declares no arguments" ({}, set()), and the callers act on the distinction.
    """
    tool = next((t for t in tools if _field(t, "name") == name), None)
    if tool is None:
        return None
    schema = _field(tool, "inputSchema") or {}
    return (schema.get("properties") or {}), set(schema.get("required") or [])


def usage_hint(tools: list[Any], name: str) -> str:
    """Compact usage line generated from the tool's inputSchema.

    v15p-self-correcting-cli: appended to error replies so the agent can
    correct the call in one retry instead of guessing argument names.
    """
    declared = declared_arguments(tools, name)
    if declared is None:
        return ""
    props, required = declared
    if not props:
        return ""
    parts = [
        f"{key}{'*' if key in required else ''}:{spec.get('type', 'any')}"
        for key, spec in props.items()
    ]
    return f"usage: {name}({', '.join(parts)}) — * = required"


def error_reply(tools: list[Any], name: str, exc: BaseException) -> str:
    """The one shape every refusal takes: the reason, then how to call it right."""
    reply = f"Error: {exc}"
    hint = usage_hint(tools, name)
    return f"{reply}\n{hint}" if hint else reply


def reject_unknown_arguments(tools: list[Any], name: str, arguments: dict | None) -> None:
    """Raise ValueError when the call carries a name the tool never declared.

    Undeclared names only. Values of DECLARED arguments are validated by the
    handlers below and refuse loudly — checking them again here would duplicate
    a working check in a second place.

    An unknown TOOL raises nothing: that is the dispatcher's refusal to make, and
    complaining about its arguments would name the wrong problem.
    """
    declared = declared_arguments(tools, name)
    if declared is None:
        return
    props, _ = declared
    unknown = [key for key in (arguments or {}) if key not in props]
    if not unknown:
        return
    parts = []
    for key in unknown:
        near = difflib.get_close_matches(key, list(props), n=1, cutoff=0.6)
        parts.append(f"{key!r} (did you mean {near[0]!r}?)" if near else repr(key))
    tail = f" {name} declares no arguments." if not props else ""
    raise ValueError(f"{name} does not declare {', '.join(parts)}.{tail}")
