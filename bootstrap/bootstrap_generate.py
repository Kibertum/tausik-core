"""TAUSIK bootstrap generators — settings.json, .mcp.json, CLAUDE.md, .cursorrules."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from bootstrap_hooks import build_hooks_dict
from bootstrap_paths import portable_path

# Workspace variables each host expands at launch — used to keep generated
# configs rename-proof (no absolute project paths). Claude's .mcp.json var is
# absent at config-parse time, hence the ``:-.`` fallback.
_CLAUDE_MCP_VAR = "${CLAUDE_PROJECT_DIR:-.}"
_CLAUDE_HOOK_VAR = "${CLAUDE_PROJECT_DIR}"
_CURSOR_VAR = "${workspaceFolder}"


def _stdio_mcp_server(command: str, args: list[str]) -> dict[str, Any]:
    """Cursor / VS Code MCP stdio transport — ``type`` required per host docs."""
    return {"type": "stdio", "command": command, "args": args}


def generate_settings_claude(target_dir: str, project_dir: str, lib_dir: str | None = None) -> None:
    """Generate .claude/settings.json for Claude Code.

    lib_dir: path to TAUSIK library (submodule). Auto-detected from bootstrap location.
    Hooks reference ${CLAUDE_PROJECT_DIR} when in-project (rename-proof), else absolute.
    """
    # Determine library path relative to project
    if lib_dir is None:
        lib_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks_dir = os.path.join(lib_dir, "scripts", "hooks")

    # Reference hooks via ${CLAUDE_PROJECT_DIR} when they live inside the project
    # (always set in the hook environment) so a folder rename doesn't break them;
    # an external lib stays absolute. No quotes — a path with spaces is a
    # pre-existing edge, and quotes would break the hooks-parity tokenizer.
    rel_hooks = portable_path(os.path.abspath(hooks_dir), project_dir, _CLAUDE_HOOK_VAR)

    def _hook_cmd(script: str, suffix: str = "") -> str:
        # -X utf8 forces UTF-8 stdio for every hook (they run directly, not via
        # the CLI wrapper, so they don't inherit its PYTHONUTF8). One injection
        # point covers all hooks — no per-file fix_stdio_encoding() needed.
        return f"python -X utf8 {rel_hooks}/{script}{suffix}"

    settings = {
        "permissions": {
            "allow": [
                "Bash(.tausik/tausik:*)",
                "Bash(.tausik/tausik.cmd:*)",
                "Bash(python .claude/scripts/project.py:*)",
                "Bash(pytest:*)",
                "Bash(git:*)",
            ]
        },
        "hooks": build_hooks_dict(_hook_cmd),
    }
    path = os.path.join(target_dir, "settings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def generate_mcp_json(project_dir: str, ide_dir: str, venv_python: str | None = None) -> None:
    """Generate .mcp.json at project root.

    Merges with existing .mcp.json to preserve user-configured servers.
    TAUSIK-managed servers (codebase-rag, tausik-project) are always updated;
    user-added servers are preserved.
    """
    python_exe = venv_python or sys.executable
    path = os.path.join(project_dir, ".mcp.json")

    # Load existing config to preserve user-added servers
    existing: dict[str, Any] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    servers = existing.get("mcpServers", {})

    # Rename-proof: in-project paths become ${CLAUDE_PROJECT_DIR:-.}-relative;
    # external paths (system venv) stay absolute. --project uses the same var.
    def _pp(p: str) -> str:
        return portable_path(p, project_dir, _CLAUDE_MCP_VAR)

    cmd = _pp(python_exe)
    proj_arg = _CLAUDE_MCP_VAR

    # Core MCP servers (always managed)
    rag_server = os.path.join(ide_dir, "mcp", "codebase-rag", "server.py")
    if os.path.exists(rag_server):
        servers["codebase-rag"] = _stdio_mcp_server(
            cmd,
            [_pp(rag_server), "--project", proj_arg],
        )
    project_server = os.path.join(ide_dir, "mcp", "project", "server.py")
    if os.path.exists(project_server):
        servers["tausik-project"] = _stdio_mcp_server(
            cmd,
            [_pp(project_server), "--project", proj_arg],
        )
    brain_server = os.path.join(ide_dir, "mcp", "brain", "server.py")
    if os.path.exists(brain_server):
        servers["tausik-brain"] = _stdio_mcp_server(
            cmd,
            [_pp(brain_server), "--project", proj_arg],
        )

    mcp_config = {**existing, "mcpServers": servers}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2)


def generate_cursor_mcp_json(
    project_dir: str, ide_dir: str, venv_python: str | None = None
) -> None:
    """Generate project-level Cursor MCP config at .cursor/mcp.json.

    Keeps user-added servers and refreshes TAUSIK-managed servers.
    """
    python_exe = venv_python or sys.executable
    cursor_dir = os.path.join(project_dir, ".cursor")
    os.makedirs(cursor_dir, exist_ok=True)
    path = os.path.join(cursor_dir, "mcp.json")

    existing: dict[str, Any] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    servers = existing.get("mcpServers", {})

    # Cursor expands ${workspaceFolder} at launch → rename-proof for in-project
    # paths; external paths stay absolute.
    def _pp(p: str) -> str:
        return portable_path(p, project_dir, _CURSOR_VAR)

    cmd = _pp(python_exe)
    proj_arg = _CURSOR_VAR

    rag_server = os.path.join(ide_dir, "mcp", "codebase-rag", "server.py")
    if os.path.exists(rag_server):
        servers["codebase-rag"] = _stdio_mcp_server(
            cmd,
            [_pp(rag_server), "--project", proj_arg],
        )
    project_server = os.path.join(ide_dir, "mcp", "project", "server.py")
    if os.path.exists(project_server):
        servers["tausik-project"] = _stdio_mcp_server(
            cmd,
            [_pp(project_server), "--project", proj_arg],
        )
    brain_server = os.path.join(ide_dir, "mcp", "brain", "server.py")
    if os.path.exists(brain_server):
        servers["tausik-brain"] = _stdio_mcp_server(
            cmd,
            [_pp(brain_server), "--project", proj_arg],
        )

    mcp_config = {**existing, "mcpServers": servers}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2)


def generate_claude_md(
    project_dir: str, project_name: str, stacks: list[str], context_tier: str = "standard"
) -> None:
    """Generate CLAUDE.md — load-bearing instructions for Claude Code.

    Constraints-first structure prevents agent drift: hard rules before softer guidance.
    Shared body lives in bootstrap_templates to keep CLAUDE.md / AGENTS.md / .cursorrules / QWEN.md in sync.
    Preserves existing CLAUDE.md if present (user customizations).
    """
    from bootstrap_templates import build_full_body

    body = build_full_body(
        project_name,
        stacks,
        "an AI agent (Claude Code)",
        ".claude",
        ide="claude",
        context_tier=context_tier,
    )
    content = f"# CLAUDE.md\n\n{body}"
    path = os.path.join(project_dir, "CLAUDE.md")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def generate_agents_md(
    project_dir: str, project_name: str, stacks: list[str], context_tier: str = "standard"
) -> None:
    """Generate AGENTS.md — universal agent onboarding (OpenCode/Codex/Cursor/Claude compatible).

    Shares the same hard constraints and SENAR rules as CLAUDE.md so no IDE gets a weaker ruleset.
    Preserves existing AGENTS.md if present.
    """
    from bootstrap_templates import build_full_body

    body = build_full_body(
        project_name, stacks, "an AI agent", ".claude", ide=None, context_tier=context_tier
    )
    content = f"# AGENTS.md — AI Agent Onboarding\n\n{body}"
    path = os.path.join(project_dir, "AGENTS.md")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


# generate_settings_qwen + generate_qwen_md moved to bootstrap_qwen.py


def generate_cursorrules(
    project_dir: str, project_name: str, stacks: list[str], context_tier: str = "standard"
) -> None:
    """Generate .cursorrules for Cursor IDE — same constraints as CLAUDE.md.

    Preserves existing .cursorrules if present.
    """
    from bootstrap_templates import build_full_body

    body = build_full_body(
        project_name,
        stacks,
        "Cursor (an AI coding agent)",
        ".cursor",
        ide="cursor",
        context_tier=context_tier,
    )
    content = f"# Cursor Rules\n\n{body}"
    path = os.path.join(project_dir, ".cursorrules")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


# generate_skill_catalog moved to bootstrap_catalog.py
