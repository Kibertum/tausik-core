"""Test SessionStart hook: auto-injection of TAUSIK state into new sessions.

The hook must: exit 0 always (graceful degradation), skip cleanly when DB absent,
respect TAUSIK_SKIP_HOOKS flag, and emit Claude Code hookSpecificOutput JSON when
it has context to share.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

_HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "hooks", "session_start.py"
)


def _run_hook(
    project_dir: str, extra_env: dict | None = None
) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir), "PYTHONUTF8": "1"}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, _HOOK_PATH],
        input="{}",
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


class TestSessionStartHook:
    def test_exits_zero_when_no_db(self, tmp_path):
        """No .tausik/tausik.db → graceful skip, exit 0, no output."""
        result = _run_hook(tmp_path)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert result.stdout.strip() == ""

    def test_skip_flag_bypasses(self, tmp_path):
        """TAUSIK_SKIP_HOOKS=1 short-circuits before any work."""
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        result = _run_hook(tmp_path, {"TAUSIK_SKIP_HOOKS": "1"})
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_db_present_but_no_cli(self, tmp_path):
        """DB exists but CLI wrapper missing → exit 0, no output (graceful)."""
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        result = _run_hook(tmp_path)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_empty_stdin(self, tmp_path):
        """Hook must not crash on malformed/empty stdin (Claude Code sometimes sends nothing)."""
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"}
        result = subprocess.run(
            [sys.executable, _HOOK_PATH],
            input="",
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0

    def test_output_is_valid_json_when_present(self, tmp_path):
        """When the hook produces context, output must be parseable hookSpecificOutput JSON."""
        tausik_dir = tmp_path / ".tausik"
        tausik_dir.mkdir()
        (tausik_dir / "tausik.db").write_text("")
        # Mock tausik CLI that always succeeds with dummy status
        wrapper = "tausik.cmd" if sys.platform == "win32" else "tausik"
        wrapper_path = tausik_dir / wrapper
        if sys.platform == "win32":
            wrapper_path.write_text(
                "@echo off\r\necho Mock status: Tasks 1/1, Session #99\r\n"
            )
        else:
            wrapper_path.write_text(
                "#!/bin/sh\necho 'Mock status: Tasks 1/1, Session #99'\n"
            )
            os.chmod(wrapper_path, 0o755)

        result = _run_hook(tmp_path)
        assert result.returncode == 0
        if result.stdout.strip():
            parsed = json.loads(result.stdout)
            assert parsed["hookSpecificOutput"]["hookEventName"] == "SessionStart"
            assert "additionalContext" in parsed["hookSpecificOutput"]
            ctx = parsed["hookSpecificOutput"]["additionalContext"]
            assert "TAUSIK" in ctx
            assert "SENAR Rule 9.1" in ctx

    def test_invalid_project_dir_env(self, tmp_path, monkeypatch):
        """Unset CLAUDE_PROJECT_DIR → falls back to cwd, still exits cleanly."""
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        env["PYTHONUTF8"] = "1"
        result = subprocess.run(
            [sys.executable, _HOOK_PATH],
            input="{}",
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0


class TestSettingsGeneration:
    """Generated settings.json must include SessionStart hook referencing session_start.py."""

    def test_claude_settings_has_sessionstart(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_generate import generate_settings_claude

        target = tmp_path / ".claude"
        target.mkdir()
        generate_settings_claude(str(target), str(tmp_path))
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "SessionStart" in hooks, "SessionStart hook not registered"
        cmds = [h["command"] for entry in hooks["SessionStart"] for h in entry["hooks"]]
        assert any("session_start.py" in c for c in cmds)

    def test_qwen_settings_has_sessionstart(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_qwen import generate_settings_qwen

        target = tmp_path / ".qwen"
        target.mkdir()
        generate_settings_qwen(str(target), str(tmp_path), venv_python=sys.executable)
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "SessionStart" in hooks, "SessionStart hook not registered for Qwen"
        cmds = [h["command"] for entry in hooks["SessionStart"] for h in entry["hooks"]]
        assert any("session_start.py" in c for c in cmds)
