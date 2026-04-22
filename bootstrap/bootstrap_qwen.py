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
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("memory_pretool_block.py"),
                        "timeout": 5,
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
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("memory_posttool_audit.py"),
                        "timeout": 5,
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
            },
        ],
    }

    settings = {**existing, "mcpServers": servers, "hooks": hooks}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def generate_qwen_md(project_dir: str, project_name: str, stacks: list[str]) -> None:
    """Generate QWEN.md for Qwen Code CLI — same constraints as CLAUDE.md.

    Preserves existing QWEN.md if present.
    """
    from bootstrap_templates import build_full_body

    body = build_full_body(
        project_name, stacks, "Qwen Code (an AI coding agent)", ".qwen"
    )
    content = f"# QWEN.md\n\n{body}"
    path = os.path.join(project_dir, "QWEN.md")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
