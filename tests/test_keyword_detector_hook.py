"""Test Stop hook — keyword detector for drift announcements in agent output.

The hook must:
- Always exit 0 (non-blocking outcomes via JSON decision field)
- Block (emit {"decision":"block",...}) only when: drift keyword in last assistant message
  AND no active TAUSIK task AND stop_hook_active is not set
- Respect skip flag, missing DB, invalid transcripts
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

_HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "hooks", "keyword_detector.py"
)


def _run(project_dir, payload: dict, extra_env=None) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir), "PYTHONUTF8": "1"}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, _HOOK_PATH],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


def _make_transcript(tmp_path, assistant_text: str, user_text: str = "hi") -> str:
    """Create a minimal JSONL transcript with one user message and one assistant message."""
    path = tmp_path / "transcript.jsonl"
    lines = [
        json.dumps({"role": "user", "content": user_text}),
        json.dumps({"role": "assistant", "content": assistant_text}),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def _setup_tausik(tmp_path, active=False):
    tausik = tmp_path / ".tausik"
    tausik.mkdir()
    (tausik / "tausik.db").write_text("")
    wrapper = "tausik.cmd" if sys.platform == "win32" else "tausik"
    wrapper_path = tausik / wrapper
    if active:
        if sys.platform == "win32":
            wrapper_path.write_text(
                "@echo off\r\necho slug   title         status\r\necho t-1    Real task     active\r\n"
            )
        else:
            wrapper_path.write_text(
                "#!/bin/sh\nprintf 'slug   title         status\\nt-1    Real task     active\\n'\n"
            )
            os.chmod(wrapper_path, 0o755)
    else:
        if sys.platform == "win32":
            wrapper_path.write_text("@echo off\r\necho (none)\r\n")
        else:
            wrapper_path.write_text("#!/bin/sh\necho '(none)'\n")
            os.chmod(wrapper_path, 0o755)


class TestDriftDetection:
    def test_english_drift_with_no_task_blocks(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(tmp_path, "Sure! I'll implement the login endpoint now.")
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        assert result.stdout.strip(), "expected block response"
        parsed = json.loads(result.stdout)
        assert parsed["decision"] == "block"
        assert "TAUSIK" in parsed["reason"]
        assert "SENAR Rule 1" in parsed["reason"]

    def test_russian_drift_with_no_task_blocks(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(tmp_path, "Понял, сейчас напишу функцию для логина.")
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        assert result.stdout.strip(), "expected block response"
        parsed = json.loads(result.stdout)
        assert parsed["decision"] == "block"

    def test_drift_with_active_task_does_not_block(self, tmp_path):
        _setup_tausik(tmp_path, active=True)
        transcript = _make_transcript(tmp_path, "I'll implement this change now.")
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        assert result.stdout.strip() == "", "active task should suppress block"

    def test_no_drift_keyword_does_not_block(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(tmp_path, "Here is my analysis of the code.")
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestSearchIntentNudge:
    """RAG-first nudge — when the user asks 'where is X' / 'find Y' / 'how does Z work'
    and the agent's response did not mention search_code, suggest mcp__codebase-rag__search_code."""

    def test_english_where_is_triggers_recommendation(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(
            tmp_path,
            assistant_text="Let me check that file.",
            user_text="where is foo defined in the codebase?",
        )
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        assert result.stdout.strip(), "expected block with rag-first recommendation"
        parsed = json.loads(result.stdout)
        assert parsed["decision"] == "block"
        assert "search_code" in parsed["reason"]
        assert "rag-first" in parsed["reason"]

    def test_english_find_function_triggers_recommendation(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(
            tmp_path,
            assistant_text="Sure.",
            user_text="find the function that handles login",
        )
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        parsed = json.loads(result.stdout) if result.stdout.strip() else {}
        assert parsed.get("decision") == "block"
        assert "search_code" in parsed.get("reason", "")

    def test_russian_where_is_triggers_recommendation(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(
            tmp_path,
            assistant_text="Сейчас посмотрю.",
            user_text="где определена функция auth?",
        )
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        parsed = json.loads(result.stdout) if result.stdout.strip() else {}
        assert parsed.get("decision") == "block"
        assert "search_code" in parsed.get("reason", "")

    def test_assistant_already_used_search_code_suppresses_nudge(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(
            tmp_path,
            assistant_text="I called mcp__codebase-rag__search_code and found 3 chunks.",
            user_text="where is foo defined?",
        )
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        assert result.stdout.strip() == "", "search_code mention in assistant suppresses nudge"

    def test_active_task_does_not_suppress_search_nudge(self, tmp_path):
        """Search-intent nudge fires regardless of task state — it's about token economy, not task discipline."""
        _setup_tausik(tmp_path, active=True)
        transcript = _make_transcript(
            tmp_path,
            assistant_text="Looking now.",
            user_text="where is the bar handler?",
        )
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        parsed = json.loads(result.stdout) if result.stdout.strip() else {}
        assert parsed.get("decision") == "block"
        assert "search_code" in parsed.get("reason", "")

    def test_non_search_question_does_not_trigger(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(
            tmp_path,
            assistant_text="Here's a thought.",
            user_text="what time is it?",
        )
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_stop_hook_active_short_circuits_search_nudge(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(
            tmp_path,
            assistant_text="Looking.",
            user_text="where is foo defined?",
        )
        result = _run(
            tmp_path,
            {"transcript_path": transcript, "stop_hook_active": True},
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_drift_takes_precedence_over_search_nudge(self, tmp_path):
        """If both drift and search-intent fire, the drift block wins (more critical)."""
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(
            tmp_path,
            assistant_text="I'll implement the fix now.",
            user_text="where is foo defined?",
        )
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert parsed["decision"] == "block"
        assert "drift guard" in parsed["reason"]


class TestToolResultFalsePositiveGuard:
    """v14b-defect-keyword-detector-search-loop — tool_result-only messages
    are role=user in Claude transcripts. If their text matched search-intent
    regex, the hook fired the rag-first nudge on every Stop until the agent
    defensively echoed `search_code`. Filter them so only actual human
    prompts trigger the nudge.
    """

    def _write_jsonl(self, tmp_path, lines: list[dict]) -> str:
        path = tmp_path / "transcript.jsonl"
        path.write_text(
            "\n".join(json.dumps(line) for line in lines) + "\n",
            encoding="utf-8",
        )
        return str(path)

    def test_tool_result_with_search_intent_does_not_trigger(self, tmp_path):
        """Real bug: /review tool result contained 'where is X' style text;
        hook walked back and matched it as the user's last message."""
        _setup_tausik(tmp_path, active=False)
        transcript = self._write_jsonl(
            tmp_path,
            [
                {"role": "user", "content": "fix the defects"},
                {"role": "assistant", "content": "running review"},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "abc",
                            "content": "Findings: where is is_security_sensitive defined? It's at scripts/security_pattern.py",
                        }
                    ],
                },
                {"role": "assistant", "content": "Got it, applying fix."},
            ],
        )
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "", (
            "tool_result content with search-intent text MUST NOT trigger the nudge "
            f"(stdout: {result.stdout!r})"
        )

    def test_real_user_prompt_after_tool_result_still_triggers(self, tmp_path):
        """Regression guard: filtering tool_result-only must not break the
        legitimate path where the actual most-recent human prompt has search-intent.
        """
        _setup_tausik(tmp_path, active=False)
        transcript = self._write_jsonl(
            tmp_path,
            [
                {
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": "x", "content": "ok"}],
                },
                {"role": "user", "content": "where is bar handler defined?"},
                {"role": "assistant", "content": "I read scripts/bar.py."},
            ],
        )
        # Walking backwards: assistant (skip), then user "where is bar..." → triggers.
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        parsed = json.loads(result.stdout) if result.stdout.strip() else {}
        assert parsed.get("decision") == "block"
        assert "search_code" in parsed.get("reason", "")

    def test_mixed_tool_result_blocks_still_filtered(self, tmp_path):
        """Multiple tool_result blocks in one user message still skipped."""
        _setup_tausik(tmp_path, active=False)
        transcript = self._write_jsonl(
            tmp_path,
            [
                {"role": "user", "content": "do work"},
                {"role": "assistant", "content": "looking"},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "a",
                            "content": "find the function foo",
                        },
                        {"type": "tool_result", "tool_use_id": "b", "content": "where is X"},
                    ],
                },
                {"role": "assistant", "content": "Done."},
            ],
        )
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"all-tool_result content must be filtered (stdout: {result.stdout!r})"
        )

    def test_user_text_string_with_tool_result_keyword_unaffected(self, tmp_path):
        """Plain string content (not a list) is always treated as user prompt,
        even if the string mentions tool_result. We only filter when content
        is a list of tool_result blocks.
        """
        _setup_tausik(tmp_path, active=False)
        transcript = self._write_jsonl(
            tmp_path,
            [
                {"role": "user", "content": "where is the tool_result handler?"},
                {"role": "assistant", "content": "Looking now."},
            ],
        )
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        parsed = json.loads(result.stdout) if result.stdout.strip() else {}
        assert parsed.get("decision") == "block"


class TestLoopSafety:
    def test_stop_hook_active_short_circuits(self, tmp_path):
        """Must not block again when we already blocked on the previous turn."""
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(tmp_path, "I'll implement it now.")
        result = _run(tmp_path, {"transcript_path": transcript, "stop_hook_active": True})
        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestGracefulDegradation:
    def test_skip_flag(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(tmp_path, "I'll implement it now.")
        result = _run(tmp_path, {"transcript_path": transcript}, {"TAUSIK_SKIP_HOOKS": "1"})
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_no_db(self, tmp_path):
        transcript = _make_transcript(tmp_path, "I'll implement it now.")
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_missing_transcript(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        result = _run(tmp_path, {"transcript_path": str(tmp_path / "nonexistent.jsonl")})
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_malformed_stdin(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
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

    def test_transcript_without_assistant_does_not_block(self, tmp_path):
        """Transcript with only user messages (edge case) — no last-assistant to inspect."""
        _setup_tausik(tmp_path, active=False)
        path = tmp_path / "t.jsonl"
        path.write_text(
            json.dumps({"role": "user", "content": "hello"}) + "\n",
            encoding="utf-8",
        )
        result = _run(tmp_path, {"transcript_path": str(path)})
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_nested_message_format(self, tmp_path):
        """Claude transcripts sometimes wrap role inside {'message': {...}}."""
        _setup_tausik(tmp_path, active=False)
        path = tmp_path / "t.jsonl"
        path.write_text(
            json.dumps({"message": {"role": "assistant", "content": "I'll implement it."}}) + "\n",
            encoding="utf-8",
        )
        result = _run(tmp_path, {"transcript_path": str(path)})
        assert result.returncode == 0
        parsed = json.loads(result.stdout) if result.stdout.strip() else {}
        assert parsed.get("decision") == "block"


class TestSettingsGeneration:
    def test_claude_settings_has_stop_hook(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_generate import generate_settings_claude

        target = tmp_path / ".claude"
        target.mkdir()
        generate_settings_claude(str(target), str(tmp_path))
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "Stop" in hooks
        cmds = [h["command"] for entry in hooks["Stop"] for h in entry["hooks"]]
        assert any("keyword_detector.py" in c for c in cmds)

    def test_qwen_settings_has_stop_hook(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_qwen import generate_settings_qwen

        target = tmp_path / ".qwen"
        target.mkdir()
        generate_settings_qwen(str(target), str(tmp_path), venv_python=sys.executable)
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "Stop" in hooks
