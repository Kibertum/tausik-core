"""TAUSIK bootstrap generators — settings.json, .mcp.json, CLAUDE.md, .cursorrules."""

from __future__ import annotations

import json
import os
import sys
from typing import Any


def generate_settings_claude(
    target_dir: str, project_dir: str, lib_dir: str | None = None
) -> None:
    """Generate .claude/settings.json for Claude Code.

    lib_dir: path to TAUSIK library (submodule). Auto-detected from bootstrap location.
    Hooks use absolute paths to avoid breakage when CWD changes mid-session.
    """

    def _p(p: str) -> str:
        return p.replace("\\", "/")

    # Determine library path relative to project
    if lib_dir is None:
        lib_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks_dir = os.path.join(lib_dir, "scripts", "hooks")

    # Always use absolute paths for hooks — relative paths break when
    # Claude Code CWD changes (e.g. after `cd frontend && npm install`)
    rel_hooks = _p(os.path.abspath(hooks_dir))

    def _hook_cmd(script: str, suffix: str = "") -> str:
        return f"python {rel_hooks}/{script}{suffix}"

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
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": _hook_cmd("task_gate.py"),
                            "timeout": 10,
                        }
                    ],
                },
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": _hook_cmd("bash_firewall.py"),
                            "timeout": 5,
                        }
                    ],
                },
                {
                    "matcher": "Bash",
                    "if": "Bash(git push *)",
                    "hooks": [
                        {
                            "type": "command",
                            "command": _hook_cmd("git_push_gate.py"),
                            "timeout": 5,
                        }
                    ],
                },
            ],
            "PostToolUse": [
                {
                    "matcher": "Write|Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": _hook_cmd("auto_format.py"),
                            "timeout": 15,
                        }
                    ],
                },
                {
                    "matcher": "mcp__tausik-project__tausik_task_done|Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": _hook_cmd("task_done_verify.py"),
                            "timeout": 6,
                        }
                    ],
                },
            ],
            "SessionStart": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": _hook_cmd("session_start.py"),
                            "timeout": 6,
                        }
                    ],
                }
            ],
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": _hook_cmd("user_prompt_submit.py"),
                            "timeout": 5,
                        }
                    ],
                }
            ],
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": _hook_cmd("keyword_detector.py"),
                            "timeout": 5,
                        },
                        {
                            "type": "command",
                            "command": _hook_cmd("session_cleanup_check.py"),
                            "timeout": 5,
                        },
                    ],
                }
            ],
            "SessionEnd": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": _hook_cmd(
                                "session_metrics.py", " --auto --record 2>&1 || true"
                            ),
                        }
                    ],
                }
            ],
        },
    }
    path = os.path.join(target_dir, "settings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def generate_mcp_json(
    project_dir: str, ide_dir: str, venv_python: str | None = None
) -> None:
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

    def _p(p: str) -> str:
        return p.replace("\\", "/")

    # Core MCP servers (always managed)
    rag_server = os.path.join(ide_dir, "mcp", "codebase-rag", "server.py")
    if os.path.exists(rag_server):
        servers["codebase-rag"] = {
            "command": _p(python_exe),
            "args": [_p(rag_server), "--project", _p(project_dir)],
        }
    project_server = os.path.join(ide_dir, "mcp", "project", "server.py")
    if os.path.exists(project_server):
        servers["tausik-project"] = {
            "command": _p(python_exe),
            "args": [_p(project_server), "--project", _p(project_dir)],
        }

    mcp_config = {**existing, "mcpServers": servers}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2)


def generate_claude_md(project_dir: str, project_name: str, stacks: list[str]) -> None:
    """Generate CLAUDE.md — load-bearing instructions for Claude Code.

    Constraints-first structure prevents agent drift: hard rules before softer guidance.
    Shared body lives in bootstrap_templates to keep CLAUDE.md / AGENTS.md / .cursorrules / QWEN.md in sync.
    Preserves existing CLAUDE.md if present (user customizations).
    """
    from bootstrap_templates import build_full_body

    body = build_full_body(project_name, stacks, "an AI agent (Claude Code)", ".claude")
    content = f"# CLAUDE.md\n\n{body}"
    path = os.path.join(project_dir, "CLAUDE.md")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def generate_agents_md(project_dir: str, project_name: str, stacks: list[str]) -> None:
    """Generate AGENTS.md — universal agent onboarding (OpenCode/Codex/Cursor/Claude compatible).

    Shares the same hard constraints and SENAR rules as CLAUDE.md so no IDE gets a weaker ruleset.
    Preserves existing AGENTS.md if present.
    """
    from bootstrap_templates import build_full_body

    body = build_full_body(project_name, stacks, "an AI agent", ".claude")
    content = f"# AGENTS.md — AI Agent Onboarding\n\n{body}"
    path = os.path.join(project_dir, "AGENTS.md")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


# generate_settings_qwen + generate_qwen_md moved to bootstrap_qwen.py


def generate_cursorrules(
    project_dir: str, project_name: str, stacks: list[str]
) -> None:
    """Generate .cursorrules for Cursor IDE — same constraints as CLAUDE.md.

    Preserves existing .cursorrules if present.
    """
    from bootstrap_templates import build_full_body

    body = build_full_body(
        project_name, stacks, "Cursor (an AI coding agent)", ".cursor"
    )
    content = f"# Cursor Rules\n\n{body}"
    path = os.path.join(project_dir, ".cursorrules")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


# generate_skill_catalog moved to bootstrap_catalog.py
