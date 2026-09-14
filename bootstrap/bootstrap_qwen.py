"""TAUSIK bootstrap — Qwen Code (GigaCode) IDE generators.

Generates .qwen/settings.json (MCP + hooks) and QWEN.md project instructions.
Qwen Code uses the same hook format as Claude Code (PreToolUse, PostToolUse, SessionEnd).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from bootstrap_generate import _stdio_mcp_server, retire_managed_servers

# The shell-tool matcher is IMPORTED, not restated. Every matcher below used to
# carry its own copy of the string "Bash" under a comment promising parity with
# bootstrap_hooks.py — and a promise in a comment is not a mechanism. When a
# second shell tool appeared, the Claude generator and this one would have had
# to be edited in lockstep by whoever remembered. Sharing the constant makes
# that impossible to get wrong.
from bootstrap_hooks import (
    BUILTIN_WRITE_MATCHER,
    SHELL_MATCHER,
    deployed_hooks_dir,
    with_mcp_registrations,
)


def generate_settings_qwen(
    target_dir: str,
    project_dir: str,
    venv_python: str | None = None,
    lib_dir: str | None = None,
) -> None:
    """Generate .qwen/settings.json with MCP servers and hooks for Qwen Code.

    Qwen Code uses the same hook format as Claude Code (PreToolUse, PostToolUse,
    SessionEnd) — so we generate the **same** SENAR enforcement hooks. v1.4
    closed the hook gap audited as r14-qwen-parity-or-honesty; parity is pinned
    by tests/test_bootstrap_hooks_parity.py.
    MCP config goes into mcpServers key in the same file.
    """
    python_exe = venv_python or sys.executable

    def _p(p: str) -> str:
        return p.replace("\\", "/")

    # Тот же разрез, что и у claude-генератора: конфиг обязан указывать на
    # РАЗВЁРНУТУЮ копию хуков, а не на библиотечную. В потребительском проекте
    # библиотека — сабмодуль, и обычный клон оставляет эти пути пустыми.
    if lib_dir is None:
        lib_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    abs_hooks = _p(os.path.abspath(deployed_hooks_dir(target_dir)))

    def _hook_cmd(script: str, suffix: str = "") -> str:
        # -X utf8 forces UTF-8 stdio for every hook (they run directly, not via
        # the CLI wrapper, so they don't inherit its PYTHONUTF8). One injection
        # point covers all hooks — no per-file fix_stdio_encoding() needed.
        return f"python -X utf8 {abs_hooks}/{script}{suffix}"

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
    retire_managed_servers(servers)
    rag_server = os.path.join(target_dir, "mcp", "codebase-rag", "server.py")
    if os.path.exists(rag_server):
        servers["codebase-rag"] = _stdio_mcp_server(
            _p(python_exe),
            [_p(rag_server), "--project", _p(project_dir)],
        )
    project_server = os.path.join(target_dir, "mcp", "project", "server.py")
    if os.path.exists(project_server):
        servers["tausik-project"] = _stdio_mcp_server(
            _p(python_exe),
            [_p(project_server), "--project", _p(project_dir)],
        )

    # Hooks — same SENAR enforcement as Claude Code
    hooks = {
        "PreToolUse": [
            {
                # l26-hook-contract-review parity: MultiEdit/NotebookEdit also write.
                "matcher": BUILTIN_WRITE_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("task_gate.py"),
                        "timeout": 10,
                    }
                ],
            },
            {
                # v15-scope-enforce-write parity with bootstrap_hooks.py
                # (+ l26-hook-contract-review: NotebookEdit added).
                "matcher": BUILTIN_WRITE_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("scope_write_gate.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                # read-ledger: same mechanism as the Claude profile, and the
                # parity test is the reason it is here rather than an
                # afterthought. A guarantee that exists on one host and not
                # another is exactly what this release refuses to ship.
                "matcher": "Read",
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("read_ledger_gate.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                # memory-route-gate: shell parity with bootstrap_hooks.py — a
                # heredoc or a Set-Content writes what the Write path refuses.
                "matcher": f"{BUILTIN_WRITE_MATCHER}|{SHELL_MATCHER}",
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("memory_pretool_block.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                # secret-scan-covers-no-shell-channel (Decision #178): shell
                # parity with bootstrap_hooks.py — a heredoc or `Set-Content
                # -Value 'AKIA...'` carries the secret the Write path warns on.
                "matcher": f"{BUILTIN_WRITE_MATCHER}|{SHELL_MATCHER}",
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("secret_scan.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                "matcher": SHELL_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("bash_firewall.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                # l26-hook-contract-review parity: close the shell-write bypass
                # of QG-0 + scope-ACL (see bootstrap_hooks.py for the rationale).
                "matcher": SHELL_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("bash_write_gate.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                # `if` dropped for the reason bootstrap_hooks.py records: it was
                # a second, dialect-specific copy of the decision the hook makes
                # itself, and it named one shell.
                "matcher": SHELL_MATCHER,
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
                # The tool TAUSIK ships, named at the moment an alternative was chosen:
                # an MCP twin for a CLI call, and `symbol` for a grep after
                # a definition. Measured before it existed — MCP 29.1% of
                # framework calls, `symbol` 2 uses against 226 greps.
                # Measured in session #233: 1,216 of 1,530 CLI invocations had an
                # MCP twin and used the shell anyway — 79.5% — while the rules
                # call MCP-first a hard constraint and nothing checked it.
                #
                # Shell tools only: the nudge is about choosing the shell over a
                # tool, and it has nothing to say about a Write or a Read. It
                # lands on BOTH hook-bearing hosts: a capability on one and not
                # the other is what `cross_model_parity` refuses.
                "matcher": SHELL_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("tool_choice_nudge.py"),
                        "timeout": 6,
                    }
                ],
            },
            {
                "matcher": "Write|Edit|MultiEdit",  # MultiEdit was off this hook (PR #5)
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("auto_format.py"),
                        "timeout": 15,
                    }
                ],
            },
            {
                "matcher": BUILTIN_WRITE_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("memory_posttool_audit.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                "matcher": (
                    "mcp__tausik-project__tausik_task_done"
                    "|mcp__tausik-project__tausik_task_done_v2"
                    f"|{SHELL_MATCHER}"
                ),
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("task_done_verify.py"),
                        "timeout": 6,
                    }
                ],
            },
            {
                "matcher": "*",
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("task_call_counter.py"),
                        "timeout": 5,
                    },
                    {
                        "type": "command",
                        "command": _hook_cmd("posttool_usage.py"),
                        "timeout": 4,
                    },
                    {
                        "type": "command",
                        "command": _hook_cmd("activity_event.py"),
                        "timeout": 5,
                    },
                    {
                        "type": "command",
                        "command": _hook_cmd("tool_output_truncation_nudge.py"),
                        "timeout": 3,
                    },
                    {
                        "type": "command",
                        "command": _hook_cmd("task_cost_budget_check.py"),
                        "timeout": 3,
                    },
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
                        "command": _hook_cmd("session_metrics.py", " --auto --record 2>&1 || true"),
                    }
                ],
            },
        ],
    }

    settings = {**existing, "mcpServers": servers, "hooks": with_mcp_registrations(hooks)}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def generate_qwen_md(
    project_dir: str,
    project_name: str,
    stacks: list[str],
    context_tier: str = "standard",
    output_mode: str = "off",
) -> None:
    """Generate QWEN.md for Qwen Code CLI — same constraints as CLAUDE.md.

    Preserves existing QWEN.md if present.
    """
    from bootstrap_templates import build_full_body, warn_output_mode_not_applied

    body = build_full_body(
        project_name,
        stacks,
        "Qwen Code (an AI coding agent)",
        ".qwen",
        ide="qwen",
        context_tier=context_tier,
        output_mode=output_mode,
        project_dir=project_dir,
    )
    content = f"# QWEN.md\n\n{body}"
    path = os.path.join(project_dir, "QWEN.md")
    if os.path.exists(path):
        # Preserving the user's file must not silently drop a mode they asked for.
        warn_output_mode_not_applied(path, output_mode)
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
