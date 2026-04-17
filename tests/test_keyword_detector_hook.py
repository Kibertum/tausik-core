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


def _make_transcript(tmp_path, assistant_text: str) -> str:
    """Create a minimal JSONL transcript with one user message and one assistant message."""
    path = tmp_path / "transcript.jsonl"
    lines = [
        json.dumps({"role": "user", "content": "hi"}),
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
        transcript = _make_transcript(
            tmp_path, "Sure! I'll implement the login endpoint now."
        )
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        assert result.stdout.strip(), "expected block response"
        parsed = json.loads(result.stdout)
        assert parsed["decision"] == "block"
        assert "TAUSIK" in parsed["reason"]
        assert "SENAR Rule 1" in parsed["reason"]

    def test_russian_drift_with_no_task_blocks(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(
            tmp_path, "Понял, сейчас напишу функцию для логина."
        )
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


class TestLoopSafety:
    def test_stop_hook_active_short_circuits(self, tmp_path):
        """Must not block again when we already blocked on the previous turn."""
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(tmp_path, "I'll implement it now.")
        result = _run(
            tmp_path, {"transcript_path": transcript, "stop_hook_active": True}
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestGracefulDegradation:
    def test_skip_flag(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        transcript = _make_transcript(tmp_path, "I'll implement it now.")
        result = _run(
            tmp_path, {"transcript_path": transcript}, {"TAUSIK_SKIP_HOOKS": "1"}
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_no_db(self, tmp_path):
        transcript = _make_transcript(tmp_path, "I'll implement it now.")
        result = _run(tmp_path, {"transcript_path": transcript})
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_missing_transcript(self, tmp_path):
        _setup_tausik(tmp_path, active=False)
        result = _run(
            tmp_path, {"transcript_path": str(tmp_path / "nonexistent.jsonl")}
        )
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
            json.dumps(
                {"message": {"role": "assistant", "content": "I'll implement it."}}
            )
            + "\n",
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
