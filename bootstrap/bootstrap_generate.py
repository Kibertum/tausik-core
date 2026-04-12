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
    """Generate CLAUDE.md project instructions."""
    stack_str = ", ".join(stacks) if stacks else "not detected"
    content = f"""# CLAUDE.md

This file provides guidance to Claude Code when working with this project.

## Project: {project_name}

Stack: {stack_str}
Framework: TAUSIK (FRamework AI)

## TAUSIK Commands

```bash
.tausik/tausik status                  # project overview
.tausik/tausik session start           # start session
.tausik/tausik task list               # list tasks
.tausik/tausik task start <slug>       # claim + activate task
.tausik/tausik task done <slug>        # complete task
```

Full CLI ref: `.claude/references/project-cli.md`

## Workflow
- NEVER start coding without a task. Use `task start` first.
- ALWAYS use `.tausik/tausik` to run CLI commands (ensures correct venv Python).
- Always respond in the user's language.

## External Skills
External skills are managed via `skills.json` and auto-synced during bootstrap.
See `.claude/references/skill-catalog.md` for the full catalog with trigger keywords.
**When a user's request matches a trigger keyword for a not-installed skill, proactively suggest installing it.**

<!-- DYNAMIC:START -->
<!-- DYNAMIC:END -->
"""
    path = os.path.join(project_dir, "CLAUDE.md")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def generate_agents_md(project_dir: str, project_name: str, stacks: list[str]) -> None:
    """Generate AGENTS.md for OpenCode/Codex compatibility."""
    stack_str = ", ".join(stacks) if stacks else "not detected"
    content = f"""# AGENTS.md — AI Agent Onboarding

**You are an AI agent working on a project that uses TAUSIK.**

## Project: {project_name}

Stack: {stack_str}
Framework: [TAUSIK](https://github.com/Kibertum/tausik-core) — AI agent governance implementing [SENAR v1.3](https://senar.tech)

## Rules

1. **No code without a task.** Create a task before writing any code.
2. **QG-0:** Every task needs a goal + acceptance criteria before `task start`.
3. **QG-2:** Log AC verification evidence before `task done --ac-verified`.
4. **Log progress.** Use `tausik task log <slug> "message"` after each step.
5. **Document dead ends.** Use `tausik dead-end "what" "why"` on failures.
6. **Session limit: 180 min.** Use checkpoints to save progress.
7. **Ask before committing.** Never commit or push without user confirmation.
8. **MCP-first.** Prefer MCP tools (`tausik_*`) over CLI when available.

## Commands

```bash
.tausik/tausik status                        # project overview
.tausik/tausik task start <slug>             # begin (QG-0: goal + AC required)
.tausik/tausik task done <slug> --ac-verified # complete (QG-2: evidence required)
.tausik/tausik task log <slug> "message"     # log progress
.tausik/tausik dead-end "approach" "reason"  # document failed approach
.tausik/tausik metrics                       # SENAR metrics
```

## Documentation

- `CLAUDE.md` — project constraints and overview
- `.tausik-lib/references/QUICKSTART.en.md` — detailed agent quickstart
- `.tausik-lib/docs/en/` — full user documentation (EN + RU)
- `.tausik-lib/references/project-cli.md` — CLI reference
"""
    path = os.path.join(project_dir, "AGENTS.md")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


# generate_settings_qwen + generate_qwen_md moved to bootstrap_qwen.py


def generate_cursorrules(
    project_dir: str, project_name: str, stacks: list[str]
) -> None:
    """Generate .cursorrules for Cursor IDE."""
    stack_str = ", ".join(stacks) if stacks else "not detected"
    content = f"""# Cursor Rules — {project_name}

Stack: {stack_str}
Framework: TAUSIK (FRamework AI)

## TAUSIK Commands

```bash
.tausik/tausik status                  # project overview
.tausik/tausik session start           # start session
.tausik/tausik task list               # list tasks
.tausik/tausik task start <slug>       # claim + activate task
.tausik/tausik task done <slug>        # complete task
```

## Workflow
- NEVER start coding without a task.
- ALWAYS use `.tausik/tausik` to run CLI commands.
- Always respond in the user's language.
"""
    path = os.path.join(project_dir, ".cursorrules")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


# generate_skill_catalog moved to bootstrap_catalog.py
