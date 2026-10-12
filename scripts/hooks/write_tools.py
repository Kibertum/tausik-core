"""The one list of tools that write files, and the payload fields that name the file.

Ported from GitHub PR #5 (Okianiwa, "guards must see every tool their action is
reachable with"), which measured on Claude Code 2.1.215 that four hooks kept
four private copies of "which tools write" and that two live write paths —
NotebookEdit and the MCP file editors — reached no guard at all. The lists
live here, in the hooks package, so every guard asks the same question; the
bootstrap matchers restate them (bootstrap must stay runnable without this
package on `sys.path`) and `tests/test_pr5_hook_coverage.py` holds the two in
agreement, the way `shell_channel.SHELL_TOOLS` is held against SHELL_MATCHER.
"""

from __future__ import annotations

import os

#: Claude Code's own file editors. `MultiEdit` is kept although 2.1.215 no
#: longer ships it: the matcher must survive its return.
BUILTIN_WRITE_TOOLS: tuple[str, ...] = ("Write", "Edit", "MultiEdit", "NotebookEdit")

#: MCP file editors named by PR #5 from the servers its author runs
#: (serena, windows-mcp). A tool a project does not have never produces an
#: event, so listing it costs nothing there; one it does have was, until now,
#: a way to write around QG-0 and the scope ACL entirely.
MCP_WRITE_TOOLS: tuple[str, ...] = (
    "mcp__windows-mcp__FileSystem",
    "mcp__serena__replace_symbol_body",
    "mcp__serena__replace_content",
    "mcp__serena__insert_after_symbol",
    "mcp__serena__insert_before_symbol",
    "mcp__serena__rename_symbol",
    "mcp__serena__safe_delete_symbol",
)

#: The shell tool windows-mcp exposes; it carries the command in
#: `tool_input.command` like the built-in PowerShell tool and is parsed as it.
MCP_SHELL_TOOLS: tuple[str, ...] = ("mcp__windows-mcp__PowerShell",)

WRITE_TOOLS: tuple[str, ...] = BUILTIN_WRITE_TOOLS + MCP_WRITE_TOOLS

#: Where a write tool names its target: `file_path` (Write/Edit/MultiEdit),
#: `notebook_path` (NotebookEdit), `path` + `destination` (windows-mcp
#: FileSystem — a move or copy names two, and the destination is the one that
#: matters), `relative_path` (every serena editor).
PATH_FIELDS: tuple[str, ...] = (
    "file_path",
    "notebook_path",
    "path",
    "relative_path",
    "destination",
)


def is_write_tool(tool_name: object) -> bool:
    return isinstance(tool_name, str) and tool_name in WRITE_TOOLS


def edited_paths(tool_input: object) -> list[str]:
    """Every path this call could write, as the payload spells it, in field order.

    A list rather than one path because a move names two. The values are NOT
    resolved here: a relative path belongs to the shell's cwd, which only the
    caller's event carries (`_common.shell_cwd`), and containment is decided by
    `hook_policy.classify_target` — one resolver, not a second one. `~` is
    expanded, since the memory guards compare against home-relative sinks.
    """
    if not isinstance(tool_input, dict):
        return []
    out: list[str] = []
    for key in PATH_FIELDS:
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            out.append(os.path.expanduser(value))
    return out


def edited_path(tool_input: object) -> str | None:
    """The one path a single-target guard should judge: the destination when there is one."""
    paths = edited_paths(tool_input)
    if not paths:
        return None
    dest = tool_input.get("destination") if isinstance(tool_input, dict) else None
    if isinstance(dest, str) and dest.strip():
        return os.path.expanduser(dest)
    return paths[0]
