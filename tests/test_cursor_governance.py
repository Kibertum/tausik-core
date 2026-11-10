"""Behavioral contract for Cursor rules, hooks, adapter, and host coexistence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "bootstrap"), str(ROOT / "scripts"), str(ROOT / "scripts" / "hooks")]

from bootstrap_generate import generate_cursor_hooks_json, generate_cursor_rule  # noqa: E402
from bootstrap_copy import copy_scripts  # noqa: E402
from bootstrap_modes import resolve_bootstrap_targets, run_post_bootstrap  # noqa: E402
from claudemd_state import resolve_claudemd  # noqa: E402
from hooks.cursor_capability import cursor_preflight_hooks_ready  # noqa: E402
from hooks.cursor_hook import adapt_output, normalize_event  # noqa: E402
from hooks.cursor_command import split_cursor_command  # noqa: E402
from hooks.codex_write_gate import check_event  # noqa: E402
from ide_utils import detect_ide  # noqa: E402
from service_execution_lease import assertion_from_session_start  # noqa: E402


def test_cursor_rule_is_current_owned_format_and_preserves_user_rules(tmp_path: Path):
    custom = tmp_path / ".cursor" / "rules" / "team.mdc"
    custom.parent.mkdir(parents=True)
    custom.write_text("---\nalwaysApply: true\n---\ncustom\n", encoding="utf-8")
    legacy = tmp_path / ".cursorrules"
    legacy.write_text("user legacy content\n", encoding="utf-8")

    generate_cursor_rule(str(tmp_path), "demo", ["python"])
    generated = tmp_path / ".cursor" / "rules" / "tausik.mdc"
    text = generated.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "alwaysApply: true" in text
    assert "TAUSIK:GENERATED-SHA256" in text
    assert custom.read_text(encoding="utf-8").endswith("custom\n")
    assert legacy.read_text(encoding="utf-8") == "user legacy content\n"


def test_cursor_hooks_preserve_user_entries_and_are_idempotent(tmp_path: Path):
    profile = tmp_path / ".cursor"
    profile.mkdir()
    custom = {"command": ".cursor/hooks/custom.ps1", "matcher": "Shell"}
    name_collision = {
        "command": "python tools/cursor_hook.py --event custom",
        "matcher": "Shell",
    }
    (profile / "hooks.json").write_text(
        json.dumps({"version": 1, "hooks": {"preToolUse": [custom, name_collision]}}),
        encoding="utf-8",
    )
    generate_cursor_hooks_json(str(tmp_path), str(profile))
    first = (profile / "hooks.json").read_bytes()
    generate_cursor_hooks_json(str(tmp_path), str(profile))
    assert (profile / "hooks.json").read_bytes() == first
    data = json.loads(first)
    pre = data["hooks"]["preToolUse"]
    assert custom in pre
    assert name_collision in pre
    managed = [entry for entry in pre if ".cursor/scripts/hooks/cursor_hook.py" in entry["command"]]
    assert managed and all(entry["failClosed"] is True for entry in managed)
    assert any("Shell" in entry.get("matcher", "") for entry in managed)
    assert all(entry["failClosed"] is True for entry in data["hooks"]["stop"])
    assert data["hooks"]["postToolUseFailure"]
    assert any(
        "--script-arg=--auto" in entry["command"] and "--script-arg=--record" in entry["command"]
        for entry in data["hooks"]["sessionEnd"]
    )


def test_cursor_security_capability_is_digest_attested(tmp_path: Path):
    profile = tmp_path / ".cursor"
    profile.mkdir()
    copy_scripts(str(ROOT), str(profile))
    generate_cursor_hooks_json(str(tmp_path), str(profile))
    assert cursor_preflight_hooks_ready(str(tmp_path)) is True
    adapter = profile / "scripts" / "hooks" / "cursor_hook.py"
    adapter.write_text(adapter.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    assert cursor_preflight_hooks_ready(str(tmp_path)) is False


def test_cursor_capability_attests_session_start_authority(tmp_path: Path):
    profile = tmp_path / ".cursor"
    profile.mkdir()
    copy_scripts(str(ROOT), str(profile))
    generate_cursor_hooks_json(str(tmp_path), str(profile), venv_python=sys.executable)
    (profile / "scripts" / "hooks" / "session_start.py").unlink()
    assert cursor_preflight_hooks_ready(str(tmp_path)) is False


def test_cursor_capability_rejects_inert_command_even_with_script_substrings(tmp_path: Path):
    profile = tmp_path / ".cursor"
    profile.mkdir()
    copy_scripts(str(ROOT), str(profile))
    generate_cursor_hooks_json(str(tmp_path), str(profile), venv_python=sys.executable)
    hooks_path = profile / "hooks.json"
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    hooks["hooks"]["preToolUse"][-1]["command"] = (
        "echo cursor_hook.py --event preToolUse --script codex_write_gate.py "
        "--project ${workspaceFolder}"
    )
    hooks_path.write_text(json.dumps(hooks, indent=2), encoding="utf-8")
    assert cursor_preflight_hooks_ready(str(tmp_path)) is False


def test_cursor_session_start_can_mint_host_bound_assertion(tmp_path: Path):
    assertion = assertion_from_session_start(
        {"hook_event_name": "SessionStart", "session_id": "conversation"},
        str(tmp_path),
        trusted_host="cursor",
    )
    assert assertion.host_instance == "cursor"
    assert assertion.thread_id == "conversation"


@pytest.mark.parametrize(
    "original",
    [
        b'{"hooks": ',
        b'{"hooks":{"preToolUse":{}}}',
        b'{"hooks":{"preToolUse":["not-an-object"]}}',
    ],
)
def test_cursor_hooks_refuse_malformed_user_config_without_rewrite(tmp_path: Path, original: bytes):
    profile = tmp_path / ".cursor"
    profile.mkdir()
    path = profile / "hooks.json"
    path.write_bytes(original)
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        generate_cursor_hooks_json(str(tmp_path), str(profile))
    assert path.read_bytes() == original


def test_fresh_multi_host_init_refreshes_every_instruction_file(tmp_path: Path, monkeypatch):
    (tmp_path / ".tausik").mkdir()
    targets = [
        tmp_path / "CLAUDE.md",
        tmp_path / ".cursor" / "rules" / "tausik.mdc",
        tmp_path / "AGENTS.md",
        tmp_path / "QWEN.md",
    ]
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("dynamic", encoding="utf-8")
    calls: list[list[str]] = []

    def record(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("subprocess.run", record)
    run_post_bootstrap(SimpleNamespace(init="demo"), str(tmp_path))

    refreshes = [call for call in calls if "update-claudemd" in call]
    assert [Path(call[call.index("--claudemd") + 1]) for call in refreshes] == targets


def test_cursor_adapter_normalizes_native_tools(monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    shell = normalize_event({"tool_name": "Shell", "tool_input": {"command": "x"}}, "preToolUse")
    assert shell["tool_name"] == "PowerShell"
    assert normalize_event({"tool_name": "Delete"}, "preToolUse")["tool_name"] == "Write"
    assert (
        normalize_event({"tool_name": "MCP:FileSystem"}, "preToolUse")["tool_name"]
        == "mcp__windows-mcp__FileSystem"
    )
    identity = normalize_event({"conversation_id": "chat", "generation_id": "turn"}, "stop")
    assert identity["session_id"] == "chat" and identity["turn_id"] == "turn"
    assert (
        normalize_event({"tool_name": "MCP:tausik_task_quick"}, "preToolUse")["tool_name"]
        == "mcp__tausik-project__tausik_task_quick"
    )
    failed = normalize_event(
        {"failure_type": "PERMISSION_DENIED", "error_message": "denied"},
        "postToolUseFailure",
    )
    assert failed["hook_event_name"] == "PostToolUse"
    assert failed["tool_response"] == {
        "is_error": True,
        "error_code": "PERMISSION_DENIED",
        "error": "denied",
    }


def test_cursor_write_gate_uses_cursor_bound_lease(monkeypatch, tmp_path: Path):
    observed = {}

    def accept(_event, _project, **kwargs):
        observed.update(kwargs)
        return True, ""

    monkeypatch.setattr("hooks.codex_write_gate.execution_lease_gate.require_live_lease", accept)
    event = {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "x")}}
    assert check_event(event, str(tmp_path), trusted_host="cursor") == 0
    assert observed["trusted_host"] == "cursor"


def test_generated_cursor_adapter_executes_read_gate_in_space_path(tmp_path: Path):
    project = tmp_path / "cursor project with spaces"
    profile = project / ".cursor"
    profile.mkdir(parents=True)
    copy_scripts(str(ROOT), str(profile))
    generate_cursor_hooks_json(str(project), str(profile), venv_python=sys.executable)
    hooks = json.loads((profile / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    managed = next(
        entry
        for entry in hooks["preToolUse"]
        if "codex_write_gate.py" in split_cursor_command(entry["command"])
    )
    command = [
        part.replace("${workspaceFolder}", str(project))
        for part in split_cursor_command(managed["command"])
    ]
    if command[:1] == ["&"]:
        command = command[1:]
    result = subprocess.run(
        command,
        input=json.dumps(
            {
                "conversation_id": "cursor-thread",
                "tool_name": "Read",
                "tool_input": {"file_path": str(project / "README.md")},
            }
        ),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"permission": "allow"}


def test_cursor_hook_command_quotes_external_python_with_spaces_for_host_shell(tmp_path: Path):
    profile = tmp_path / ".cursor"
    profile.mkdir()
    generate_cursor_hooks_json(
        str(tmp_path), str(profile), venv_python="C:/Python With Spaces/python.exe"
    )
    command = json.loads((profile / "hooks.json").read_text(encoding="utf-8"))["hooks"][
        "preToolUse"
    ][-1]["command"]
    parts = split_cursor_command(command)
    if os.name == "nt":
        assert parts[:2] == ["&", "C:/Python With Spaces/python.exe"]
    else:
        assert parts[:2] == ["C:/Python With Spaces/python.exe", "-X"]


@pytest.mark.skipif(os.name != "nt", reason="PowerShell hook contract is Windows-specific")
def test_cursor_hook_command_preserves_powershell_path_metacharacters(tmp_path: Path):
    project = tmp_path / "cursor-project"
    profile = project / ".cursor"
    profile.mkdir(parents=True)
    runner = tmp_path / "100% & O'Brien (x)" / "runner.cmd"
    runner.parent.mkdir()
    runner.write_text("@echo cmd-quoted\n", encoding="utf-8")
    generate_cursor_hooks_json(str(project), str(profile), venv_python=str(runner))
    command = json.loads((profile / "hooks.json").read_text(encoding="utf-8"))["hooks"][
        "preToolUse"
    ][-1]["command"].replace("${workspaceFolder}", str(project))

    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "cmd-quoted" in result.stdout


def test_cursor_adapter_emits_valid_native_responses():
    assert json.loads(adapt_output("", "preToolUse", 0)) == {"permission": "allow"}
    denied = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "blocked",
        }
    }
    assert json.loads(adapt_output(json.dumps(denied), "preToolUse", 0))["permission"] == "deny"
    post = adapt_output(
        json.dumps({"systemMessage": "attempt_event_id=7", "continue": True}),
        "postToolUse",
        0,
    )
    assert json.loads(post) == {"additional_context": "attempt_event_id=7"}
    failed_post = adapt_output(
        json.dumps({"systemMessage": "attempt_event_id=8", "continue": True}),
        "postToolUseFailure",
        0,
    )
    assert json.loads(failed_post) == {"additional_context": "attempt_event_id=8"}
    stop = adapt_output(json.dumps({"decision": "block", "reason": "continue"}), "stop", 0)
    assert json.loads(stop) == {"followup_message": "continue"}


def test_cursor_dynamic_state_resolves_owned_rule(tmp_path: Path, monkeypatch):
    (tmp_path / ".tausik").mkdir()
    (tmp_path / ".tausik" / "config.json").write_text(
        json.dumps({"bootstrap": {"primary_ide": "cursor"}}), encoding="utf-8"
    )
    generate_cursor_rule(str(tmp_path), "demo", ["python"])
    monkeypatch.delenv("CODEX_SANDBOX_DIR", raising=False)
    monkeypatch.delenv("CURSOR_DIR", raising=False)
    assert resolve_claudemd(str(tmp_path)) == str(tmp_path / ".cursor" / "rules" / "tausik.mdc")


def test_runtime_host_env_wins_but_upgrade_preserves_recorded_targets(tmp_path: Path, monkeypatch):
    (tmp_path / ".tausik").mkdir()
    (tmp_path / ".tausik" / "config.json").write_text(
        json.dumps({"bootstrap": {"primary_ide": "codex", "ides": ["codex", "cursor"]}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("CURSOR_DIR", "1")
    monkeypatch.delenv("TAUSIK_IDE", raising=False)
    monkeypatch.delenv("CODEX_SANDBOX_DIR", raising=False)
    assert detect_ide(str(tmp_path)) == "cursor"
    assert resolve_bootstrap_targets(
        None, str(tmp_path), {"primary_ide": "codex", "ides": ["codex", "cursor"]}
    ) == ("codex", ["codex", "cursor"])
