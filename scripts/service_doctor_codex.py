"""Doctor check for the installed Codex composite-MCP authorization capability."""

from __future__ import annotations

import json
import hashlib
import os
import tomllib

from hooks.codex_capability import exact_hook_command, manifest_error


def _hook_registered(
    hooks: object,
    *,
    event: str,
    script_path: str,
    project_dir: str,
    python_executable: str,
) -> bool:
    """Require the exact generated command at its security-relevant event."""
    if not isinstance(hooks, dict):
        return False
    hook_events = hooks.get("hooks")
    if not isinstance(hook_events, dict):
        return False
    entries = hook_events.get(event)
    if not isinstance(entries, list):
        return False
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("matcher") != "":
            continue
        commands = entry.get("hooks")
        if not isinstance(commands, list):
            continue
        for hook in commands:
            if not isinstance(hook, dict) or hook.get("type") != "command":
                continue
            if exact_hook_command(
                hook.get("command", ""), script_path, project_dir, python_executable
            ):
                return True
    return False


def check_codex_mcp_transport(project_dir: str) -> list[tuple[str, str, str]]:
    config = os.path.join(project_dir, ".codex", "config.toml")
    if not os.path.isfile(config):
        return []
    try:
        with open(config, "rb") as fh:
            payload = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [("fail", "Codex MCP authorization", f"config.toml is unreadable: {exc}")]
    server = payload.get("mcp_servers", {}).get("tausik-project")
    if not isinstance(server, dict):
        return []
    raw_env = server.get("env")
    env: dict[str, object] = raw_env if isinstance(raw_env, dict) else {}
    capability_error = env.get("TAUSIK_MCP_CAPABILITY_ERROR")
    if isinstance(capability_error, str) and capability_error:
        return [("fail", "Codex MCP authorization", capability_error)]
    if env.get("TAUSIK_ENFORCE_EXECUTION_LEASE") != "1":
        return [
            (
                "fail",
                "Codex MCP authorization",
                "CAPABILITY_MISMATCH: rerun bootstrap --ide codex; enforcement is not enabled",
            )
        ]
    target_dir = os.path.join(project_dir, ".codex")
    try:
        with open(os.path.join(target_dir, "tausik-capability.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
        reason = manifest_error(manifest)
        if reason is not None:
            transport_error = f"CAPABILITY_MISMATCH: rerun bootstrap --ide codex; {reason}"
        else:
            adapters = manifest.get("adapters")
            transport_error = None
            for name in (
                "codex_write_gate.py",
                "memory_preflight_posttool.py",
                "codex_composite_mcp.py",
                "user_prompt_submit.py",
                "can_stop_gate.py",
            ):
                path = os.path.join(target_dir, "scripts", "hooks", name)
                try:
                    with open(path, "rb") as fh:
                        digest = hashlib.sha256(fh.read()).hexdigest()
                except OSError:
                    transport_error = (
                        f"CAPABILITY_MISMATCH: rerun bootstrap --ide codex; {name} is missing"
                    )
                    break
                if adapters.get(name) != digest:
                    transport_error = (
                        f"CAPABILITY_MISMATCH: rerun bootstrap --ide codex; {name} drifted"
                    )
                    break
    except (OSError, ValueError, TypeError, AttributeError):
        transport_error = "CAPABILITY_MISMATCH: rerun bootstrap --ide codex; manifest is missing"
    if transport_error is not None:
        return [
            (
                "fail",
                "Codex MCP authorization",
                transport_error,
            )
        ]
    hooks_path = os.path.join(target_dir, "hooks.json")
    try:
        with open(hooks_path, encoding="utf-8") as fh:
            hooks = json.load(fh)
    except (OSError, ValueError, TypeError, AttributeError):
        hooks = None
    registrations = (
        ("PreToolUse", "codex_write_gate.py"),
        ("PostToolUse", "memory_preflight_posttool.py"),
        ("UserPromptSubmit", "user_prompt_submit.py"),
        ("Stop", "can_stop_gate.py"),
    )
    if not all(
        _hook_registered(
            hooks,
            event=event,
            script_path=os.path.join(target_dir, "scripts", "hooks", adapter),
            project_dir=project_dir,
            python_executable=manifest["python_executable"],
        )
        for event, adapter in registrations
    ):
        return [
            (
                "fail",
                "Codex MCP authorization",
                "CAPABILITY_MISMATCH: rerun bootstrap --ide codex; hook registrations are stale",
            )
        ]
    return [("ok", "Codex MCP authorization", "direct and functions.exec transports attested")]


__all__ = ["check_codex_mcp_transport"]
