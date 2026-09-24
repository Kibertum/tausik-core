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
from bootstrap_hooks import build_hooks_dict, deployed_hooks_dir


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
    rag_server = os.path.join(target_dir, "mcp", "codebase-rag", "rag_server.py")
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

    # Hooks: the SAME declaration Claude and Codex use (bootstrap_hooks.build_hooks_dict);
    # only the command line is Qwen's own. This used to be a hand-kept copy that had
    # drifted in 15 PostToolUse registrations (qwen-hooks-are-a-second-copy-of-the-declaration).
    hooks = build_hooks_dict(_hook_cmd)

    settings = {**existing, "mcpServers": servers, "hooks": hooks}
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
