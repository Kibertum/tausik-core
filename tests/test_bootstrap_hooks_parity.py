"""r14-qwen-parity-or-honesty: Qwen Code hooks must match Claude Code.

Pre-1.4 the Qwen bootstrap quietly omitted four hooks that Claude shipped:
- brain_search_proactive (PreToolUse on Web*)
- brain_post_webfetch (PostToolUse on WebFetch)
- task_call_counter (PostToolUse on every tool)
- activity_event (PostToolUse on every tool)

The README claimed "same SENAR enforcement as Claude Code" — so users on
Qwen Code lost gap-based active-time tracking, call-budget warnings, and
shared-brain plumbing without knowing it. This test compares the hook
command set between the two generators and fails if they drift again.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO / "bootstrap"

# Cross-cutting: guards claude/qwen hook parity across the bootstrap generators.
CROSSCUTTING_SCOPE = ["bootstrap/"]
sys.path.insert(0, str(BOOTSTRAP))


def _collect_hook_scripts(settings: dict) -> set[str]:
    """Flatten settings.hooks into a set of script basenames."""
    scripts: set[str] = set()
    for stage_entries in (settings.get("hooks") or {}).values():
        for entry in stage_entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                for token in cmd.replace("\\", "/").split():
                    if token.endswith(".py"):
                        scripts.add(os.path.basename(token))
    return scripts


@pytest.fixture
def claude_settings(tmp_path):
    from bootstrap_generate import generate_settings_claude

    target = tmp_path / "claude"
    target.mkdir()
    generate_settings_claude(
        str(target),
        str(tmp_path / "project"),
        lib_dir=str(REPO),
    )
    return json.loads((target / "settings.json").read_text(encoding="utf-8"))


@pytest.fixture
def qwen_settings(tmp_path):
    from bootstrap_qwen import generate_settings_qwen

    target = tmp_path / "qwen"
    target.mkdir()
    generate_settings_qwen(
        str(target),
        str(tmp_path / "project"),
        venv_python=sys.executable,
        lib_dir=str(REPO),
    )
    return json.loads((target / "settings.json").read_text(encoding="utf-8"))


def test_qwen_has_every_claude_hook(claude_settings, qwen_settings):
    claude_scripts = _collect_hook_scripts(claude_settings)
    qwen_scripts = _collect_hook_scripts(qwen_settings)
    missing = claude_scripts - qwen_scripts
    assert not missing, (
        f"Qwen settings.json is missing hooks present in Claude: {sorted(missing)}. "
        "Update bootstrap/bootstrap_qwen.py to keep parity, or update this test "
        "AND the README/multimodel docs to honestly enumerate the gap."
    )


def test_qwen_does_not_invent_hooks(claude_settings, qwen_settings):
    claude_scripts = _collect_hook_scripts(claude_settings)
    qwen_scripts = _collect_hook_scripts(qwen_settings)
    extra = qwen_scripts - claude_scripts
    assert not extra, (
        f"Qwen settings.json declares hooks not in Claude: {sorted(extra)}. "
        "If intentional, update this test to allow-list the difference."
    )


def test_critical_hooks_present_in_both(claude_settings, qwen_settings):
    """Pin the hooks the audit specifically called out."""
    required = {
        "task_gate.py",
        "scope_write_gate.py",
        "memory_pretool_block.py",
        "secret_scan.py",
        "bash_firewall.py",
        "git_push_gate.py",
        "brain_search_proactive.py",
        "auto_format.py",
        "memory_posttool_audit.py",
        "task_done_verify.py",
        "brain_post_webfetch.py",
        "task_call_counter.py",
        "activity_event.py",
        "session_start.py",
        "user_prompt_submit.py",
        "keyword_detector.py",
        "session_cleanup_check.py",
        "session_metrics.py",
        "task_cost_budget_check.py",
    }
    for label, settings in (("claude", claude_settings), ("qwen", qwen_settings)):
        scripts = _collect_hook_scripts(settings)
        missing = required - scripts
        assert not missing, f"{label} settings.json is missing required hooks: {sorted(missing)}"


def test_shell_matcher_covers_every_dialect_the_parser_knows():
    """The registration and the parser must name the SAME set of shell tools.

    `powershell-tool-bypasses-bash-firewall`: the registration said "Bash" and
    the agent was also being handed a `PowerShell` tool. Nothing failed —
    the gates were correct, they were simply never invoked for that channel, and
    no test could notice because every test spelled "Bash" too.

    So the two are pinned against each other. `shell_channel.SHELL_TOOLS` is the
    producer: a dialect gains a parser only by being added there, and this test
    then requires a matcher for it. Adding one without the other is a failing
    test rather than a silent hole.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
    import shell_channel
    from bootstrap_hooks import SHELL_MATCHER

    assert SHELL_MATCHER == "|".join(shell_channel.SHELL_TOOLS)


def test_every_shell_gate_is_registered_for_every_shell_tool(claude_settings, qwen_settings):
    """A gate that reads a COMMAND must match every tool that produces one.

    Pins the actual defect: `bash_firewall`, `bash_write_gate` and
    `git_push_gate` were registered for one shell tool while two existed, so on
    win32 the firewall, QG-0-over-shell and the push ticket all applied to
    roughly half the commands the agent ran. `memory_pretool_block` is in the
    list too — it also reads a command line, alongside its file-path tools.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))
    import shell_channel

    command_reading_gates = {
        "bash_firewall.py",
        "bash_write_gate.py",
        "git_push_gate.py",
        "memory_pretool_block.py",
    }
    for label, settings in (("claude", claude_settings), ("qwen", qwen_settings)):
        for entry in settings.get("hooks", {}).get("PreToolUse", []):
            scripts = {os.path.basename(h["command"].split()[-1]) for h in entry["hooks"]}
            for gate in scripts & command_reading_gates:
                tools = set(entry["matcher"].split("|"))
                missing = set(shell_channel.SHELL_TOOLS) - tools
                assert not missing, (
                    f"{label}: {gate} reads a shell command but is not registered "
                    f"for {sorted(missing)} — that channel reaches no gate. "
                    f"matcher={entry['matcher']!r}"
                )
            # A narrowing `if` clause is a second copy of the gate's own
            # decision and can only name one dialect; the push gate carried one
            # and that is how the PowerShell push went ungated.
            if scripts & command_reading_gates:
                assert "if" not in entry, (
                    f"{label}: {sorted(scripts & command_reading_gates)} carries an "
                    f"`if` pre-filter ({entry.get('if')!r}). The hook decides for "
                    "itself; a second copy of that decision drifts per dialect."
                )
