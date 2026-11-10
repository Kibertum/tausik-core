"""Attest the Cursor hook transport before issuing trusted authority."""

from __future__ import annotations

import hashlib
import json
import os

from hooks.cursor_command import split_cursor_command


def cursor_preflight_hooks_ready(project_dir: str) -> bool:
    """Return whether Cursor's native config invokes exact critical adapters."""
    profile = os.path.join(project_dir, ".cursor")
    try:
        with open(os.path.join(profile, "hooks.json"), encoding="utf-8") as file:
            hooks_text = file.read()
        payload = json.loads(hooks_text)
        with open(os.path.join(profile, "tausik-capability.json"), encoding="utf-8") as file:
            manifest = json.load(file)
    except (OSError, ValueError, TypeError):
        return False
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 2
        or manifest.get("host") != "cursor"
        or manifest.get("hooks_sha256") != hashlib.sha256(hooks_text.encode("utf-8")).hexdigest()
    ):
        return False
    adapters = manifest.get("adapters")
    if not isinstance(adapters, dict):
        return False
    hooks_dir = os.path.realpath(os.path.join(profile, "scripts", "hooks"))
    required = {
        "cursor_hook.py",
        "cursor_command.py",
        "session_start.py",
        "codex_write_gate.py",
        "memory_preflight_posttool.py",
        "user_prompt_submit.py",
        "can_stop_gate.py",
    }
    for name in required:
        path = os.path.join(hooks_dir, name)
        try:
            with open(path, "rb") as file:
                digest = hashlib.sha256(file.read()).hexdigest()
        except OSError:
            return False
        if adapters.get(name) != digest:
            return False
    hooks = payload.get("hooks", {}) if isinstance(payload, dict) else {}
    expected = {
        "sessionStart": "session_start.py",
        "beforeSubmitPrompt": "user_prompt_submit.py",
        "preToolUse": "codex_write_gate.py",
        "postToolUse": "memory_preflight_posttool.py",
        "postToolUseFailure": "memory_preflight_posttool.py",
        "stop": "can_stop_gate.py",
    }
    python_exe = manifest.get("python")
    if not isinstance(python_exe, str) or not python_exe:
        return False
    adapter = "${workspaceFolder}/.cursor/scripts/hooks/cursor_hook.py"
    for event, script in expected.items():
        entries = [entry for entry in hooks.get(event, []) if isinstance(entry, dict)]
        matching = []
        for entry in entries:
            try:
                parts = split_cursor_command(str(entry.get("command", "")))
            except ValueError:
                continue
            if parts[:1] == ["&"]:
                parts = parts[1:]
            if parts[:3] != [python_exe, "-X", "utf8"]:
                continue
            if len(parts) < 9 or parts[3:9] != [
                adapter,
                "--event",
                event,
                "--script",
                script,
                "--project",
            ]:
                continue
            if parts[9:10] != ["${workspaceFolder}"]:
                continue
            matching.append(entry)
        if not matching:
            return False
        if event in {"preToolUse", "stop"} and not all(
            entry.get("failClosed") is True for entry in matching
        ):
            return False
        if event == "stop" and not all(entry.get("loop_limit") == 10 for entry in matching):
            return False
    return True
