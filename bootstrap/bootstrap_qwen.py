"""TAUSIK bootstrap — Qwen Code (GigaCode) IDE generators.

Generates .qwen/settings.json (MCP + hooks) and QWEN.md project instructions.
Qwen Code uses the same hook format as Claude Code (PreToolUse, PostToolUse, SessionEnd).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


def generate_settings_qwen(
    target_dir: str,
    project_dir: str,
    venv_python: str | None = None,
    lib_dir: str | None = None,
) -> None:
    """Generate .qwen/settings.json with MCP servers and hooks for Qwen Code.

    Qwen Code uses the same hook format as Claude Code (PreToolUse, PostToolUse,
    SessionEnd) — so we generate identical SENAR enforcement hooks.
    MCP config goes into mcpServers key in the same file.
    """
    python_exe = venv_python or sys.executable

    def _p(p: str) -> str:
        return p.replace("\\", "/")

    if lib_dir is None:
        lib_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks_dir = os.path.join(lib_dir, "scripts", "hooks")
    abs_hooks = _p(os.path.abspath(hooks_dir))

    def _hook_cmd(script: str, suffix: str = "") -> str:
        return f"python {abs_hooks}/{script}{suffix}"

    path = os.path.join(target_dir, "settings.json")

    # Load existing to preserve user settings
    existing: dict[str, Any] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # MCP servers
    servers = existing.get("mcpServers", {})
    rag_server = os.path.join(target_dir, "mcp", "codebase-rag", "server.py")
    if os.path.exists(rag_server):
        servers["codebase-rag"] = {
            "command": _p(python_exe),
            "args": [_p(rag_server), "--project", _p(project_dir)],
        }
    project_server = os.path.join(target_dir, "mcp", "project", "server.py")
    if os.path.exists(project_server):
        servers["tausik-project"] = {
            "command": _p(python_exe),
            "args": [_p(project_server), "--project", _p(project_dir)],
        }

    # Hooks — same SENAR enforcement as Claude Code
    hooks = {
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
            },
        ],
    }

    settings = {**existing, "mcpServers": servers, "hooks": hooks}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def generate_qwen_md(project_dir: str, project_name: str, stacks: list[str]) -> None:
    """Generate QWEN.md project instructions for Qwen Code CLI."""
    stack_str = ", ".join(stacks) if stacks else "not detected"
    content = f"""# QWEN.md

This file provides guidance to Qwen Code when working with this project.

## Project: {project_name}

Stack: {stack_str}
Framework: TAUSIK (AI Agent Governance)

## TAUSIK Commands

```bash
.tausik/tausik status                  # project overview
.tausik/tausik session start           # start session
.tausik/tausik task list               # list tasks
.tausik/tausik task start <slug>       # claim + activate task
.tausik/tausik task done <slug>        # complete task
```

Full CLI ref: `.qwen/references/project-cli.md`

## Workflow
- NEVER start coding without a task. Use `task start` first.
- ALWAYS use `.tausik/tausik` to run CLI commands (ensures correct venv Python).
- Always respond in the user's language.

## External Skills
External skills are managed via `skills.json` and auto-synced during bootstrap.
See `.qwen/references/skill-catalog.md` for the full catalog with trigger keywords.
**When a user's request matches a trigger keyword for a not-installed skill, proactively suggest installing it.**

<!-- DYNAMIC:START -->
<!-- DYNAMIC:END -->
"""
    path = os.path.join(project_dir, "QWEN.md")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
