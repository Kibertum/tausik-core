"""Test Stop hook — session hygiene (open exploration, review tasks, session timeout)."""

from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from session_cleanup_check import (
    _has_open_exploration,
    _review_task_count,
    _session_overrun_minutes,
)

_HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "hooks", "session_cleanup_check.py"
)


class TestPureHelpers:
    def test_no_active_exploration_returns_false(self):
        assert _has_open_exploration("No active exploration.") is False

    def test_active_exploration_returns_true(self):
        assert _has_open_exploration(
            "Exploration #3 started (60 min limit): research topic"
        )

    def test_empty_explore_output_returns_false(self):
        assert _has_open_exploration("") is False

    def test_review_count_header_only(self):
        assert _review_task_count("slug   title\n---") == 0

    def test_review_count_three_rows(self):
        out = "slug     title      status\n---\nt-1    A\nt-2    B\nt-3    C\n"
        assert _review_task_count(out) == 3

    def test_review_count_none(self):
        assert _review_task_count("(none)") == 0

    def test_session_overrun_below_threshold(self):
        assert _session_overrun_minutes("Session running for 100 min") == 0

    def test_session_overrun_at_threshold(self):
        assert _session_overrun_minutes("Session has been running for 160 min") == 160

    def test_session_overrun_no_match(self):
        assert _session_overrun_minutes("status: all good") == 0


class TestHookIntegration:
    def _run(self, tmp_path, payload, extra_env=None):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"}
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

    def test_no_db_exits_silently(self, tmp_path):
        r = self._run(tmp_path, {})
        assert r.returncode == 0
        assert r.stderr == ""

    def test_skip_flag(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        r = self._run(tmp_path, {}, {"TAUSIK_SKIP_HOOKS": "1"})
        assert r.returncode == 0
        assert r.stderr == ""

    def test_stop_hook_active_short_circuits(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        r = self._run(tmp_path, {"stop_hook_active": True})
        assert r.returncode == 0
        assert r.stderr == ""

    def test_db_present_but_no_cli(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        r = self._run(tmp_path, {})
        assert r.returncode == 0
        assert r.stderr == ""

    def test_malformed_stdin(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"}
        r = subprocess.run(
            [sys.executable, _HOOK_PATH],
            input="not-json",
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert r.returncode == 0
        assert r.stderr == ""

    def test_warnings_emitted_when_stale_explore_via_mock(self, tmp_path):
        """Mock CLI emits exploration output; hook must surface a warning."""
        tausik = tmp_path / ".tausik"
        tausik.mkdir()
        (tausik / "tausik.db").write_text("")
        wrapper = "tausik.cmd" if sys.platform == "win32" else "tausik"
        wrapper_path = tausik / wrapper
        # Mock always returns exploration record regardless of subcommand; ok for smoke
        if sys.platform == "win32":
            wrapper_path.write_text(
                "@echo off\r\necho Exploration #1 started: mock\r\n"
            )
        else:
            wrapper_path.write_text("#!/bin/sh\necho 'Exploration #1 started: mock'\n")
            os.chmod(wrapper_path, 0o755)
        r = self._run(tmp_path, {})
        assert r.returncode == 0
        assert "TAUSIK session hygiene" in r.stderr


class TestSettingsGeneration:
    def test_claude_settings_has_cleanup_hook(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_generate import generate_settings_claude

        target = tmp_path / ".claude"
        target.mkdir()
        generate_settings_claude(str(target), str(tmp_path))
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        stop = cfg.get("hooks", {}).get("Stop", [])
        cmds = [h["command"] for entry in stop for h in entry.get("hooks", [])]
        assert any("session_cleanup_check.py" in c for c in cmds)
        # Sanity: keyword_detector should still be there
        assert any("keyword_detector.py" in c for c in cmds)

    def test_qwen_settings_has_cleanup_hook(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_qwen import generate_settings_qwen

        target = tmp_path / ".qwen"
        target.mkdir()
        generate_settings_qwen(str(target), str(tmp_path), venv_python=sys.executable)
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        stop = cfg.get("hooks", {}).get("Stop", [])
        cmds = [h["command"] for entry in stop for h in entry.get("hooks", [])]
        assert any("session_cleanup_check.py" in c for c in cmds)
