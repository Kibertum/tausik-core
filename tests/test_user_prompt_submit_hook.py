"""Test UserPromptSubmit hook: coding-intent detection + nudge injection.

The hook must never block (always exit 0). It should nudge only when
(a) prompt looks like a coding request, (b) there is no active task, (c) TAUSIK is set up.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

_HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "hooks", "user_prompt_submit.py"
)


def _run(
    project_dir: str, prompt: str, extra_env: dict | None = None
) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir), "PYTHONUTF8": "1"}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, _HOOK_PATH],
        input=json.dumps({"prompt": prompt}),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


def _setup_empty_tausik(tmp_path):
    """Create .tausik/tausik.db placeholder + mock CLI returning '(none)' for active task list."""
    tausik = tmp_path / ".tausik"
    tausik.mkdir()
    (tausik / "tausik.db").write_text("")
    wrapper = "tausik.cmd" if sys.platform == "win32" else "tausik"
    wrapper_path = tausik / wrapper
    if sys.platform == "win32":
        wrapper_path.write_text("@echo off\r\necho (none)\r\n")
    else:
        wrapper_path.write_text("#!/bin/sh\necho '(none)'\n")
        os.chmod(wrapper_path, 0o755)
    return tausik


def _setup_active_task(tmp_path):
    """Mock CLI returning a populated active-task listing."""
    tausik = tmp_path / ".tausik"
    tausik.mkdir()
    (tausik / "tausik.db").write_text("")
    wrapper = "tausik.cmd" if sys.platform == "win32" else "tausik"
    wrapper_path = tausik / wrapper
    mock_output = "slug      title          status\nsome-slug Real task     active\n"
    if sys.platform == "win32":
        wrapper_path.write_text(
            "@echo off\r\necho slug      title          status\r\necho some-slug Real task     active\r\n"
        )
    else:
        wrapper_path.write_text(f"#!/bin/sh\nprintf '%s\\n' '{mock_output}'\n")
        os.chmod(wrapper_path, 0o755)


class TestIntentDetection:
    def test_english_coding_intent_triggers_nudge(self, tmp_path):
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, "fix the bug in the login endpoint")
        assert result.returncode == 0
        assert result.stdout.strip(), "expected nudge output"
        parsed = json.loads(result.stdout)
        assert parsed["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        assert "TAUSIK nudge" in parsed["hookSpecificOutput"]["additionalContext"]

    def test_russian_coding_intent_triggers_nudge(self, tmp_path):
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, "напиши функцию для логина")
        assert result.returncode == 0
        assert result.stdout.strip(), "expected nudge output"

    def test_question_about_code_does_not_nudge(self, tmp_path):
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, "что такое этот модуль?")
        assert result.returncode == 0
        assert result.stdout.strip() == "", "question should not trigger nudge"

    def test_explain_prompt_does_not_nudge(self, tmp_path):
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, "explain how this function works")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_empty_prompt_does_not_nudge(self, tmp_path):
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, "")
        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestActiveTaskCheck:
    def test_active_task_skips_nudge(self, tmp_path):
        """With an active task, coding intent should NOT trigger reminder."""
        _setup_active_task(tmp_path)
        result = _run(tmp_path, "add a new endpoint")
        assert result.returncode == 0
        assert result.stdout.strip() == "", "active task should suppress nudge"


class TestGracefulDegradation:
    def test_no_db_exits_silently(self, tmp_path):
        result = _run(tmp_path, "fix the bug")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_skip_flag_bypasses(self, tmp_path):
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, "fix the bug", {"TAUSIK_SKIP_HOOKS": "1"})
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_malformed_stdin(self, tmp_path):
        _setup_empty_tausik(tmp_path)
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"}
        result = subprocess.run(
            [sys.executable, _HOOK_PATH],
            input="not-json{{{",
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_emoji_and_special_chars(self, tmp_path):
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, "fix the bug 🐛 with login")
        assert result.returncode == 0
        # Should still nudge — "fix" keyword is present
        assert result.stdout.strip()

    def test_non_latin_non_cyrillic_prompt(self, tmp_path):
        """Prompt in another language shouldn't crash; no keyword match → no nudge."""
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, "これは何ですか")
        assert result.returncode == 0


class TestSettingsGeneration:
    def test_claude_settings_has_userpromptsubmit(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_generate import generate_settings_claude

        target = tmp_path / ".claude"
        target.mkdir()
        generate_settings_claude(str(target), str(tmp_path))
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "UserPromptSubmit" in hooks
        cmds = [
            h["command"] for entry in hooks["UserPromptSubmit"] for h in entry["hooks"]
        ]
        assert any("user_prompt_submit.py" in c for c in cmds)

    def test_qwen_settings_has_userpromptsubmit(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_qwen import generate_settings_qwen

        target = tmp_path / ".qwen"
        target.mkdir()
        generate_settings_qwen(str(target), str(tmp_path), venv_python=sys.executable)
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "UserPromptSubmit" in hooks
