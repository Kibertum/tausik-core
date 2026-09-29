"""Test UserPromptSubmit hook: coding-intent detection + nudge injection.

The hook must never block (always exit 0). It should nudge only when
(a) prompt looks like a coding request, (b) there is no active task, (c) TAUSIK is set up.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

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
        encoding="utf-8",
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
        assert "[TAUSIK nudge]" not in result.stdout, "question should not trigger nudge"

    def test_explain_prompt_does_not_nudge(self, tmp_path):
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, "explain how this function works")
        assert result.returncode == 0
        assert "[TAUSIK nudge]" not in result.stdout

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
        assert "[TAUSIK nudge]" not in result.stdout, "active task should suppress nudge"


def _context(result) -> str:
    if not result.stdout.strip():
        return ""
    return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


class TestRagFirstNudgeIsGone:
    """Decision #390: the rag-first nudge is removed. A paired replay measured 0
    search_code calls in 62 with it and 0 in 76 without (rag-nudge-replay-protocol
    §7), so a code-discovery prompt now arms nothing, with or without a task."""

    @pytest.mark.parametrize(
        "prompt",
        [
            "where is parse_manifest defined in the codebase?",
            "find the function that handles login",
            "где определена функция auth?",
        ],
    )
    def test_a_code_discovery_prompt_injects_nothing(self, tmp_path, prompt):
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, prompt)
        assert result.returncode == 0
        # A prompt naming a function may still arm the TASK nudge (Rule 1);
        # what must be gone is any advice about how to search.
        assert "rag-first" not in result.stdout and "search_code" not in result.stdout

    def test_a_coding_prompt_gets_only_the_task_nudge(self, tmp_path):
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, "fix the bug — where is the auth handler defined?")
        assert result.returncode == 0
        ctx = _context(result)
        assert "TAUSIK nudge" in ctx
        assert "rag-first" not in ctx and "search_code" not in ctx

    def test_slash_command_body_does_not_trigger(self, tmp_path):
        """A slash-command expansion is machine text and arms no nudge."""
        _setup_empty_tausik(tmp_path)
        result = _run(tmp_path, "/start")
        assert result.returncode == 0
        assert result.stdout.strip() == ""


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
            encoding="utf-8",
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
        cmds = [h["command"] for entry in hooks["UserPromptSubmit"] for h in entry["hooks"]]
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


class TestAnswerBudget:
    """terse-answers-enforced-by-mechanism: the answer the human just read is scored."""

    def _transcript(self, tmp_path, answer):
        p = tmp_path / "t.jsonl"
        rec = {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": answer}]},
        }
        p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
        return str(p)

    def _run_with(self, tmp_path, transcript):
        return subprocess.run(
            [sys.executable, _HOOK_PATH],
            input=json.dumps({"prompt": "ok, what next?", "transcript_path": transcript}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"},
        )

    def test_a_long_answer_is_named_with_its_numbers(self, tmp_path):
        _setup_empty_tausik(tmp_path)
        long_answer = "Done: shipped.\n" + "word " * 400
        ctx = _context(self._run_with(tmp_path, self._transcript(tmp_path, long_answer)))
        assert "[TAUSIK answer budget]" in ctx and "budget 200" in ctx

    def test_an_answer_within_budget_injects_nothing(self, tmp_path):
        """NEGATIVE: a terse answer with a verdict adds no line."""
        _setup_empty_tausik(tmp_path)
        result = self._run_with(
            tmp_path, self._transcript(tmp_path, "Done: 3 tasks closed.\n- A: 2")
        )
        assert result.returncode == 0 and "answer budget" not in result.stdout

    def test_a_missing_transcript_injects_nothing(self, tmp_path):
        """NEGATIVE: never blocks, never guesses."""
        _setup_empty_tausik(tmp_path)
        result = self._run_with(tmp_path, str(tmp_path / "absent.jsonl"))
        assert result.returncode == 0 and "answer budget" not in result.stdout
