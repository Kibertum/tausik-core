"""Cursor-specific doctor rows — MCP surface tax on the same plan budget."""

from __future__ import annotations

import json
from pathlib import Path

#: Servers bootstrap may install for TAUSIK. Anything else is "extra" MCP.
_TAUSIK_MCP_NAMES = frozenset({"tausik-project", "codebase-rag", "tausik-brain"})


def check_cursor_mcp_surface(project_dir: str) -> list[tuple[str, str, str]]:
    """Warn when non-TAUSIK MCP servers share Cursor's per-turn tool budget.

    Silent on non-Cursor projects (no `.cursor/mcp.json`). Does not claim we
    can meter third-party token use — only that extra advertise lists cost the
    same subscription.
    """
    cursor_mcp = Path(project_dir) / ".cursor" / "mcp.json"
    if not cursor_mcp.is_file():
        return []
    try:
        data = json.loads(cursor_mcp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return [
            (
                "warn",
                "Cursor MCP surface",
                f"could not parse {cursor_mcp.as_posix()} — check JSON manually",
            )
        ]
    servers = data.get("mcpServers") or data.get("servers") or {}
    if not isinstance(servers, dict) or not servers:
        return []
    names = sorted(str(k) for k in servers)
    extras = [n for n in names if n not in _TAUSIK_MCP_NAMES]
    if not extras:
        return [
            (
                "ok",
                "Cursor MCP surface",
                f"{len(names)} TAUSIK server(s) — no extra MCP advertise tax detected",
            )
        ]
    return [
        (
            "warn",
            "Cursor MCP surface",
            (
                f"{len(extras)} non-TAUSIK MCP server(s) ({', '.join(extras)}) share the "
                "same Cursor plan budget as TAUSIK: each adds per-turn tool-surface tax. "
                "Disable unused project/user MCP for focused TAUSIK work "
                "(Cursor Settings → MCP, or project `.cursor/mcp.json` — not only "
                "`~/.cursor/mcp.json`). TAUSIK cannot meter third-party MCP token use."
            ),
        )
    ]
