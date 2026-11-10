"""Cursor-specific doctor rows — MCP surface tax on the same plan budget."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

#: Servers bootstrap may install for TAUSIK. Anything else is "extra" MCP.
_TAUSIK_MCP_NAMES = frozenset({"tausik-project", "codebase-rag", "tausik-brain"})


def _binds_path(value: str, expected: Path, workspace_form: str) -> bool:
    """Accept Cursor's portable token or bootstrap's exact absolute Windows path."""
    if value == workspace_form:
        return True
    try:
        return Path(value).resolve() == expected.resolve()
    except (OSError, RuntimeError, ValueError):
        return False


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
    if not isinstance(data, dict):
        return [("warn", "Cursor MCP transport", "mcp.json root must be an object")]
    servers = data.get("mcpServers") or data.get("servers") or {}
    if not isinstance(servers, dict) or not servers:
        return [
            (
                "warn",
                "Cursor MCP transport",
                "managed tausik-project server is missing — rerun bootstrap --ide cursor",
            )
        ]
    broken: list[str] = []
    if "tausik-project" not in servers:
        broken.append("tausik-project: managed server is missing")
    for name in sorted(_TAUSIK_MCP_NAMES & set(servers)):
        entry = servers[name]
        if not isinstance(entry, dict):
            broken.append(f"{name}: entry is not an object")
            continue
        command = entry.get("command")
        args = entry.get("args")
        if entry.get("type") != "stdio" or not isinstance(command, str) or not command.strip():
            broken.append(f"{name}: requires type=stdio and a non-empty command")
            continue
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            broken.append(f"{name}: args must be a string array")
            continue
        try:
            project_arg = args[args.index("--project") + 1]
        except (ValueError, IndexError):
            project_arg = ""
        project_root = Path(project_dir)
        if not _binds_path(project_arg, project_root, "${workspaceFolder}"):
            broken.append(f"{name}: --project does not bind to this project root")
            continue
        server_rel = (
            ".cursor/mcp/project/server.py"
            if name == "tausik-project"
            else f".cursor/mcp/{name}/rag_server.py"
        )
        expected_server = project_root / server_rel
        workspace_server = f"${{workspaceFolder}}/{server_rel}"
        if not args or not _binds_path(args[0], expected_server, workspace_server):
            broken.append(f"{name}: server path does not resolve to {server_rel}")
            continue
        if not (Path(project_dir) / server_rel).is_file():
            broken.append(f"{name}: deployed server file is missing")
        resolved_command = command.replace("${workspaceFolder}", str(Path(project_dir)))
        if not (Path(resolved_command).is_file() or shutil.which(resolved_command)):
            broken.append(f"{name}: command is not executable")
        if name == "tausik-project":
            env = entry.get("env")
            if not isinstance(env, dict) or env.get("TAUSIK_ENFORCE_EXECUTION_LEASE") != "1":
                broken.append("tausik-project: execution-lease enforcement is not enabled")
            elif env.get("TAUSIK_TRUSTED_HOST") != "cursor":
                broken.append("tausik-project: trusted host is not cursor")
    if broken:
        return [
            (
                "warn",
                "Cursor MCP transport",
                "; ".join(broken) + " â€” rerun bootstrap --ide cursor",
            )
        ]
    from hooks.cursor_capability import cursor_preflight_hooks_ready

    if not cursor_preflight_hooks_ready(project_dir):
        return [
            (
                "fail",
                "Cursor hook capability",
                "hook/config attestation is missing or stale — rerun bootstrap --ide cursor",
            )
        ]
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
