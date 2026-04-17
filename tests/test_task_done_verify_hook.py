"""Test PostToolUse hook — task_done adversarial evidence audit.

Always exits 0. Warning goes to stderr when 2+ of 5 heuristics fail.
"""

from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from task_done_verify import _check_ac_checkmarks, evaluate_notes
from _common import extract_task_done_slug_from_bash, is_task_done_invocation

_HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "hooks", "task_done_verify.py"
)


class TestHeuristics:
    """Direct unit tests of the evaluate_notes() scorer."""

    def test_strong_evidence_passes_all_checks(self):
        notes = (
            "AC1: Refactored scripts/service_knowledge.py:120-180 ✓ — extracted helper. "
            "Test: 942 passed in 2m. ruff check: All checks passed. "
            "Function memory_block() now handles empty DB (line 140)."
        )
        failed, _ = evaluate_notes(notes)
        assert failed == 0

    def test_empty_notes_fails_multiple_checks(self):
        failed, _ = evaluate_notes("")
        assert failed >= 4

    def test_missing_file_paths_fails_that_check(self):
        notes = "All AC verified ✓ passed, 100 tests ran, ruff ok, def foo"
        failed, names = evaluate_notes(notes)
        joined = "\n".join(names)
        assert "file_paths" in joined

    def test_missing_test_numbers_fails_that_check(self):
        notes = "Fixed scripts/foo.py ✓ verified — ruff passed, see function bar."
        _, names = evaluate_notes(notes)
        assert any("test_numbers" in n for n in names)

    def test_missing_lint_fails_that_check(self):
        notes = "Fixed scripts/foo.py ✓ verified 200 passed def bar"
        _, names = evaluate_notes(notes)
        assert any("lint_status" in n for n in names)

    def test_oversize_notes_truncated_no_crash(self):
        notes = "x" * 50_000 + " scripts/foo.py ✓ 100 passed ruff def bar"
        failed, _ = evaluate_notes(notes)
        assert failed >= 0

    def test_ac_checkmarks_excludes_incomplete_and_completion(self):
        """H2 regression: 'complete' must NOT match 'incomplete' or 'completion'."""
        # Only "incomplete" and "completion" — no real checkmarks.
        assert _check_ac_checkmarks("This is incomplete. Completion pending.") is False
        # Two real markers: ✓ + passed — should pass.
        assert _check_ac_checkmarks("AC1 ✓ verified, tests passed") is True
        # "completed" past tense IS a valid marker.
        assert _check_ac_checkmarks("step 1 completed, step 2 completed") is True


class TestBashTaskDoneDetection:
    """H1 regression: Bash command detection must not match prose mentions of 'task done'."""

    def test_real_tausik_task_done_matches(self):
        cmd = ".tausik/tausik task done my-slug --ac-verified"
        assert extract_task_done_slug_from_bash(cmd) == "my-slug"
        assert is_task_done_invocation("Bash", {"command": cmd}) is True

    def test_echo_mentioning_task_done_does_not_match(self):
        cmd = 'echo "task done today, finally!"'
        assert extract_task_done_slug_from_bash(cmd) == ""
        assert is_task_done_invocation("Bash", {"command": cmd}) is False

    def test_grep_for_task_done_does_not_match(self):
        cmd = 'git log --grep="task done"'
        assert extract_task_done_slug_from_bash(cmd) == ""
        assert is_task_done_invocation("Bash", {"command": cmd}) is False

    def test_tausik_cmd_variant_matches(self):
        cmd = ".tausik/tausik.cmd task done my-slug"
        assert extract_task_done_slug_from_bash(cmd) == "my-slug"

    def test_mcp_tool_call_matches(self):
        assert (
            is_task_done_invocation(
                "mcp__tausik-project__tausik_task_done", {"slug": "x"}
            )
            is True
        )


class TestHookIntegration:
    def _run(self, tmp_path, payload, extra_env=None):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"}
        if extra_env:
            env.update(extra_env)
        import json as _json

        return subprocess.run(
            [sys.executable, _HOOK_PATH],
            input=_json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )

    def test_non_matching_tool_exits_silently(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        result = self._run(
            tmp_path, {"tool_name": "Read", "tool_input": {"file_path": "x"}}
        )
        assert result.returncode == 0
        assert result.stderr == ""

    def test_no_db_exits_silently(self, tmp_path):
        payload = {
            "tool_name": "mcp__tausik-project__tausik_task_done",
            "tool_input": {"slug": "whatever"},
        }
        result = self._run(tmp_path, payload)
        assert result.returncode == 0
        assert result.stderr == ""

    def test_skip_flag(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        payload = {
            "tool_name": "mcp__tausik-project__tausik_task_done",
            "tool_input": {"slug": "whatever"},
        }
        result = self._run(tmp_path, payload, {"TAUSIK_SKIP_HOOKS": "1"})
        assert result.returncode == 0
        assert result.stderr == ""

    def test_malformed_stdin(self, tmp_path):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"}
        result = subprocess.run(
            [sys.executable, _HOOK_PATH],
            input="not json",
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0

    def test_tool_errored_exits_silently(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        payload = {
            "tool_name": "mcp__tausik-project__tausik_task_done",
            "tool_input": {"slug": "test"},
            "tool_result": {"is_error": True},
        }
        result = self._run(tmp_path, payload)
        assert result.returncode == 0
        assert result.stderr == ""

    def test_thin_evidence_produces_warning(self, tmp_path):
        """Mock CLI returns thin notes; hook should warn."""
        tausik = tmp_path / ".tausik"
        tausik.mkdir()
        (tausik / "tausik.db").write_text("")
        wrapper = "tausik.cmd" if sys.platform == "win32" else "tausik"
        wrapper_path = tausik / wrapper
        if sys.platform == "win32":
            wrapper_path.write_text("@echo off\r\necho done\r\n")
        else:
            wrapper_path.write_text("#!/bin/sh\necho 'done'\n")
            os.chmod(wrapper_path, 0o755)

        payload = {
            "tool_name": "mcp__tausik-project__tausik_task_done",
            "tool_input": {"slug": "test-slug"},
        }
        result = self._run(tmp_path, payload)
        assert result.returncode == 0
        assert "TAUSIK verify-fix-loop" in result.stderr
        assert "test-slug" in result.stderr

    def test_bash_task_done_also_matched(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        wrapper = "tausik.cmd" if sys.platform == "win32" else "tausik"
        (tmp_path / ".tausik" / wrapper).write_text(
            "@echo off\r\necho done\r\n"
            if sys.platform == "win32"
            else "#!/bin/sh\necho done\n"
        )
        if sys.platform != "win32":
            os.chmod(tmp_path / ".tausik" / wrapper, 0o755)
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": ".tausik/tausik task done my-task --ac-verified"},
        }
        result = self._run(tmp_path, payload)
        assert result.returncode == 0


class TestSettingsGeneration:
    def test_claude_settings_has_verify_hook(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_generate import generate_settings_claude

        import json as _json

        target = tmp_path / ".claude"
        target.mkdir()
        generate_settings_claude(str(target), str(tmp_path))
        cfg = _json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        post = hooks.get("PostToolUse", [])
        cmds = [h["command"] for entry in post for h in entry.get("hooks", [])]
        assert any("task_done_verify.py" in c for c in cmds)

    def test_qwen_settings_has_verify_hook(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_qwen import generate_settings_qwen

        import json as _json

        target = tmp_path / ".qwen"
        target.mkdir()
        generate_settings_qwen(str(target), str(tmp_path), venv_python=sys.executable)
        cfg = _json.loads((target / "settings.json").read_text(encoding="utf-8"))
        post = cfg.get("hooks", {}).get("PostToolUse", [])
        cmds = [h["command"] for entry in post for h in entry.get("hooks", [])]
        assert any("task_done_verify.py" in c for c in cmds)
