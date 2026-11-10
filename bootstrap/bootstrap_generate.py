"""TAUSIK bootstrap generators for host settings, MCP, hooks, and rules."""

from __future__ import annotations

import json
import hashlib
import os
import shlex
import sys
from typing import Any

from bootstrap_hooks import build_hooks_dict, deployed_hooks_dir
from bootstrap_paths import portable_path

# Workspace variables each host expands at launch — used to keep generated
# configs rename-proof (no absolute project paths). Claude's .mcp.json var is
# absent at config-parse time, hence the ``:-.`` fallback.
_CLAUDE_MCP_VAR = "${CLAUDE_PROJECT_DIR:-.}"
_CLAUDE_HOOK_VAR = "${CLAUDE_PROJECT_DIR}"
_CURSOR_VAR = "${workspaceFolder}"


# Managed entries from older bootstrap versions that no longer ship.
RETIRED_MCP_SERVERS: tuple[str, ...] = ("tausik-brain",)


def _load_existing_json_object(path: str, *, field: str | None = None) -> dict[str, Any]:
    """Read a user-owned JSON object without ever replacing unreadable bytes."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"refusing to overwrite unreadable JSON config {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"refusing to overwrite {path}: JSON root must be an object")
    if field is not None and field in value and not isinstance(value[field], dict):
        raise RuntimeError(f"refusing to overwrite {path}: {field} must be an object")
    return value


def retire_managed_servers(servers: dict) -> list[str]:
    """Drop retired managed entries from a live ``mcpServers``-style dict; return the names removed."""
    removed = [name for name in RETIRED_MCP_SERVERS if name in servers]
    for name in removed:
        del servers[name]
    return removed


def _stdio_mcp_server(
    command: str, args: list[str], *, env: dict[str, str] | None = None
) -> dict[str, Any]:
    """Cursor / VS Code MCP stdio transport — ``type`` required per host docs."""
    entry: dict[str, Any] = {"type": "stdio", "command": command, "args": args}
    if env:
        entry["env"] = env
    return entry


def generate_settings_claude(
    target_dir: str,
    project_dir: str,
    lib_dir: str | None = None,
    governance_profile: str = "full",
) -> None:
    """Generate .claude/settings.json for Claude Code.

    lib_dir: path to TAUSIK library (submodule). Auto-detected from bootstrap location.
    Hooks reference ${CLAUDE_PROJECT_DIR} when in-project (rename-proof), else absolute.
    """
    # Point at the DEPLOYED hooks, not the library's. See deployed_hooks_dir:
    # in a consumer project the library is a submodule, and a plain clone
    # leaves those paths empty — every hook command would name a file that is
    # not there. lib_dir is still accepted and used elsewhere in this function.
    if lib_dir is None:
        lib_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks_dir = deployed_hooks_dir(target_dir)

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
        "hooks": build_hooks_dict(_hook_cmd, governance_profile),
    }
    path = os.path.join(target_dir, "settings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def generate_mcp_json(project_dir: str, ide_dir: str, venv_python: str | None = None) -> None:
    """Refresh managed root MCP servers while preserving user servers."""
    python_exe = venv_python or sys.executable
    path = os.path.join(project_dir, ".mcp.json")

    # Load existing config to preserve user-added servers
    existing = _load_existing_json_object(path, field="mcpServers")

    servers = existing.get("mcpServers", {})
    retire_managed_servers(servers)

    # Rename-proof: in-project paths become ${CLAUDE_PROJECT_DIR:-.}-relative;
    # external paths (system venv) stay absolute. --project uses the same var.
    def _pp(p: str) -> str:
        return portable_path(p, project_dir, _CLAUDE_MCP_VAR)

    cmd = _pp(python_exe)
    proj_arg = _CLAUDE_MCP_VAR

    # Core MCP servers (always managed)
    rag_server = os.path.join(ide_dir, "mcp", "codebase-rag", "rag_server.py")
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

    mcp_config = {**existing, "mcpServers": servers}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2)


def generate_cursor_mcp_json(
    project_dir: str, ide_dir: str, venv_python: str | None = None
) -> None:
    """Refresh TAUSIK servers in `.cursor/mcp.json` while preserving user servers."""
    python_exe = venv_python or sys.executable
    cursor_dir = os.path.join(project_dir, ".cursor")
    os.makedirs(cursor_dir, exist_ok=True)
    path = os.path.join(cursor_dir, "mcp.json")

    existing = _load_existing_json_object(path, field="mcpServers")

    servers = existing.get("mcpServers", {})
    retire_managed_servers(servers)

    # Cursor expands ${workspaceFolder} at launch → rename-proof for in-project
    # External paths stay absolute.
    def _pp(p: str) -> str:
        return portable_path(p, project_dir, _CURSOR_VAR)

    cmd = _pp(python_exe)
    proj_arg = _CURSOR_VAR

    rag_server = os.path.join(ide_dir, "mcp", "codebase-rag", "rag_server.py")
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
            env={
                "TAUSIK_ENFORCE_EXECUTION_LEASE": "1",
                "TAUSIK_TRUSTED_HOST": "cursor",
            },
        )

    mcp_config = {**existing, "mcpServers": servers}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2)


_CURSOR_EVENT_NAMES = {
    "PreToolUse": "preToolUse",
    "PostToolUse": "postToolUse",
    "SessionStart": "sessionStart",
    "UserPromptSubmit": "beforeSubmitPrompt",
    "Stop": "stop",
    "SessionEnd": "sessionEnd",
}


def _cursor_matcher(matcher: str) -> str:
    """Translate the shared Claude tool vocabulary to Cursor's native names."""
    translated: list[str] = []
    for name in matcher.split("|") if matcher else []:
        if name in {"Bash", "PowerShell"}:
            mapped = "Shell"
        elif name in {"Edit", "MultiEdit", "NotebookEdit"}:
            mapped = "Write"
        elif name.startswith("mcp__"):
            mapped = f"MCP:{name.rsplit('__', 1)[-1]}"
        elif name == "Glob":
            continue  # Cursor documents no Glob matcher.
        else:
            mapped = name
        if mapped not in translated:
            translated.append(mapped)
    if "Write" in translated and "Delete" not in translated:
        translated.append("Delete")
    return "|".join(translated)


def generate_cursor_hooks_json(
    project_dir: str,
    target_dir: str,
    governance_profile: str = "full",
    venv_python: str | None = None,
) -> None:
    """Generate native project hooks while preserving every user hook entry."""
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, "hooks.json")
    existing = _load_existing_json_object(path)
    if "hooks" in existing and not isinstance(existing["hooks"], dict):
        raise RuntimeError(f"refusing to overwrite {path}: hooks must be an object")
    for event, entries in existing.get("hooks", {}).items():
        if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
            raise RuntimeError(
                f"refusing to overwrite {path}: hooks.{event} must be a list of objects"
            )

    def source_command(script: str, suffix: str = "") -> str:
        return f"{script}{suffix}"

    python_exe = portable_path(venv_python or sys.executable, project_dir, _CURSOR_VAR)
    adapter = f"{_CURSOR_VAR}/.cursor/scripts/hooks/cursor_hook.py"

    def adapter_command(event: str, command: str) -> str:
        parts = command.split()
        script = parts[0]
        tokens = [
            python_exe,
            "-X",
            "utf8",
            adapter,
            "--event",
            event,
            "--script",
            script,
            "--project",
            _CURSOR_VAR,
            *(f"--script-arg={part}" for part in parts[1:] if part.startswith("--")),
        ]

        def quote(token: str) -> str:
            if os.name == "nt":
                # Cursor uses PowerShell on Windows; doubled apostrophes are literal.
                return f"'{token.replace(chr(39), chr(39) * 2)}'"
            return shlex.quote(token)

        prefix = "& " if os.name == "nt" else ""
        return prefix + " ".join(quote(token) for token in tokens)

    shared = build_hooks_dict(source_command, governance_profile)
    generated: dict[str, list[dict[str, Any]]] = {}
    for source_event, groups in shared.items():
        event = _CURSOR_EVENT_NAMES.get(source_event)
        if event is None:
            continue
        entries: list[dict[str, Any]] = []
        for group in groups:
            matcher = _cursor_matcher(str(group.get("matcher", "")))
            for hook in group.get("hooks", []):
                shared_command = str(hook.get("command", ""))
                item: dict[str, Any] = {
                    "command": adapter_command(event, shared_command),
                    "timeout": int(hook.get("timeout", 10)),
                }
                if matcher:
                    item["matcher"] = matcher
                if event in {"preToolUse", "stop"}:
                    item["failClosed"] = True
                if event == "stop":
                    item["loop_limit"] = 10
                entries.append(item)
        generated[event] = entries
    if governance_profile == "full":
        generated.setdefault("preToolUse", []).append(
            {
                "command": adapter_command("preToolUse", "codex_write_gate.py"),
                "timeout": 10,
                "failClosed": True,
            }
        )
        generated.setdefault("postToolUse", []).append(
            {
                "command": adapter_command("postToolUse", "memory_preflight_posttool.py"),
                "timeout": 10,
            }
        )
        generated.setdefault("postToolUseFailure", []).append(
            {
                "command": adapter_command("postToolUseFailure", "memory_preflight_posttool.py"),
                "timeout": 10,
            }
        )

    hooks = dict(existing.get("hooks", {}))
    for event in sorted(set(hooks) | set(generated)):
        user_entries = []
        for entry in hooks.get(event, []):
            if not isinstance(entry, dict):
                user_entries.append(entry)
                continue
            command = str(entry.get("command", "")).replace("\\", "/")
            legacy_owned = ".cursor/scripts/hooks/cursor_hook.py" in command
            if not legacy_owned:
                user_entries.append(entry)
        if event in generated:
            hooks[event] = user_entries + generated[event]
        elif user_entries:
            hooks[event] = user_entries
        else:
            hooks.pop(event, None)
    payload = {**existing, "version": 1, "hooks": hooks}
    encoded_hooks = json.dumps(payload, indent=2)
    with open(path, "w", encoding="utf-8") as file:
        file.write(encoded_hooks)
    critical = (
        "cursor_hook.py",
        "cursor_command.py",
        "session_start.py",
        "codex_write_gate.py",
        "memory_preflight_posttool.py",
        "user_prompt_submit.py",
        "can_stop_gate.py",
    )
    adapters: dict[str, str] = {}
    hooks_dir = deployed_hooks_dir(target_dir)
    for name in critical:
        adapter = os.path.join(hooks_dir, name)
        if not os.path.isfile(adapter):
            manifest = os.path.join(target_dir, "tausik-capability.json")
            if os.path.isfile(manifest):
                os.remove(manifest)
            return
        with open(adapter, "rb") as file:
            adapters[name] = hashlib.sha256(file.read()).hexdigest()
    with open(os.path.join(target_dir, "tausik-capability.json"), "w", encoding="utf-8") as file:
        json.dump(
            {
                "schema_version": 2,
                "host": "cursor",
                "adapters": adapters,
                "hooks_sha256": hashlib.sha256(encoded_hooks.encode("utf-8")).hexdigest(),
                "python": python_exe,
            },
            file,
            indent=2,
        )


def generate_cursor_rule(
    project_dir: str,
    project_name: str,
    stacks: list[str],
    context_tier: str = "minimal",
    output_mode: str = "off",
    governance_profile: str = "full",
) -> None:
    """Write Cursor's current always-apply project-rule format."""
    from bootstrap_templates import build_full_body, write_generated_rules

    body = build_full_body(
        project_name,
        stacks,
        "Cursor (an AI coding agent)",
        ".cursor",
        ide="cursor",
        context_tier=context_tier,
        output_mode=output_mode,
        project_dir=project_dir,
        governance_profile=governance_profile,
    )
    path = os.path.join(project_dir, ".cursor", "rules", "tausik.mdc")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    content = f"---\nalwaysApply: true\n---\n# TAUSIK\n\n{body}"
    write_generated_rules(path, content, output_mode, governance_profile)


def generate_claude_md(
    project_dir: str,
    project_name: str,
    stacks: list[str],
    context_tier: str = "minimal",
    output_mode: str = "off",
    governance_profile: str = "full",
) -> None:
    """Generate CLAUDE.md — load-bearing instructions for Claude Code.

    Constraints-first structure prevents agent drift: hard rules before softer guidance.
    Shared body lives in bootstrap_templates to keep host instruction files in sync.
    Preserves existing CLAUDE.md if present (user customizations).
    """
    from bootstrap_templates import build_full_body, write_generated_rules

    body = build_full_body(
        project_name,
        stacks,
        "an AI agent (Claude Code)",
        ".claude",
        ide="claude",
        context_tier=context_tier,
        output_mode=output_mode,
        project_dir=project_dir,
        governance_profile=governance_profile,
    )
    content = f"# CLAUDE.md\n\n{body}"
    path = os.path.join(project_dir, "CLAUDE.md")
    write_generated_rules(path, content, output_mode, governance_profile)


def generate_agents_md(
    project_dir: str,
    project_name: str,
    stacks: list[str],
    context_tier: str = "minimal",
    output_mode: str = "off",
    governance_profile: str = "full",
) -> None:
    """Generate AGENTS.md — universal agent onboarding (OpenCode/Codex/Cursor/Claude compatible).

    Shares the same hard constraints and SENAR rules as CLAUDE.md so no IDE gets a weaker ruleset.
    Preserves existing AGENTS.md if present.
    """
    from bootstrap_templates import build_full_body, write_generated_rules

    body = build_full_body(
        project_name,
        stacks,
        "an AI agent",
        ".claude",
        ide=None,
        context_tier=context_tier,
        output_mode=output_mode,
        governance_profile=governance_profile,
        # project_dir is withheld deliberately. AGENTS.md is read by kilo, codex
        # and others, so no profile on disk answers for it, and the enforcement
        # notice must say UNKNOWN rather than borrow Claude's answer.
    )
    content = f"# AGENTS.md — AI Agent Onboarding\n\n{body}"
    path = os.path.join(project_dir, "AGENTS.md")
    write_generated_rules(path, content, output_mode, governance_profile)


# generate_settings_qwen + generate_qwen_md moved to bootstrap_qwen.py


def generate_cursorrules(
    project_dir: str,
    project_name: str,
    stacks: list[str],
    context_tier: str = "minimal",
    output_mode: str = "off",
    governance_profile: str = "full",
) -> None:
    """Generate the legacy .cursorrules format for compatibility callers.

    New bootstrap flows use ``generate_cursor_rule`` and preserve this file.
    """
    from bootstrap_templates import build_full_body, write_generated_rules

    body = build_full_body(
        project_name,
        stacks,
        "Cursor (an AI coding agent)",
        ".cursor",
        ide="cursor",
        context_tier=context_tier,
        output_mode=output_mode,
        project_dir=project_dir,
        governance_profile=governance_profile,
    )
    content = f"# Cursor Rules\n\n{body}"
    path = os.path.join(project_dir, ".cursorrules")
    write_generated_rules(path, content, output_mode, governance_profile)


# generate_skill_catalog moved to bootstrap_catalog.py
