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
    }
    for label, settings in (("claude", claude_settings), ("qwen", qwen_settings)):
        scripts = _collect_hook_scripts(settings)
        missing = required - scripts
        assert not missing, f"{label} settings.json is missing required hooks: {sorted(missing)}"
