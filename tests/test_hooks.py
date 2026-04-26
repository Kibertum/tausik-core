"""Tests for Claude Code hooks: task_gate, bash_firewall, git_push_gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import pytest

HOOKS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks")


def run_hook(
    script: str, stdin_data: dict | None = None, env_extra: dict | None = None
) -> subprocess.CompletedProcess:
    """Run a hook script with optional stdin JSON and env vars."""
    env = os.environ.copy()
    env["TAUSIK_SKIP_HOOKS"] = ""  # Don't skip in tests
    if env_extra:
        env.update(env_extra)
    input_str = json.dumps(stdin_data) if stdin_data else ""
    return subprocess.run(
        [sys.executable, os.path.join(HOOKS_DIR, script)],
        input=input_str,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=10,
    )


class TestBashFirewall:
    """bash_firewall.py blocks dangerous commands."""

    def test_normal_command_allowed(self):
        r = run_hook("bash_firewall.py", {"tool_input": {"command": "ls -la"}})
        assert r.returncode == 0

    def test_rm_rf_root_blocked(self):
        r = run_hook("bash_firewall.py", {"tool_input": {"command": "rm -rf /"}})
        assert r.returncode == 2
        assert "BLOCKED" in r.stderr

    def test_rm_rf_dot_blocked(self):
        r = run_hook("bash_firewall.py", {"tool_input": {"command": "rm -rf ."}})
        assert r.returncode == 2

    def test_drop_table_blocked(self):
        r = run_hook(
            "bash_firewall.py",
            {"tool_input": {"command": "sqlite3 db.db 'DROP TABLE users'"}},
        )
        assert r.returncode == 2

    def test_git_reset_hard_blocked(self):
        r = run_hook(
            "bash_firewall.py", {"tool_input": {"command": "git reset --hard HEAD~5"}}
        )
        assert r.returncode == 2

    def test_git_push_force_blocked(self):
        r = run_hook(
            "bash_firewall.py",
            {"tool_input": {"command": "git push --force origin main"}},
        )
        assert r.returncode == 2

    def test_skip_hooks_env(self):
        r = run_hook(
            "bash_firewall.py",
            {"tool_input": {"command": "rm -rf /"}},
            env_extra={"TAUSIK_SKIP_HOOKS": "1"},
        )
        assert r.returncode == 0

    def test_empty_command_allowed(self):
        r = run_hook("bash_firewall.py", {"tool_input": {"command": ""}})
        assert r.returncode == 0

    def test_no_stdin_allowed(self):
        r = run_hook("bash_firewall.py")
        assert r.returncode == 0


class TestGitPushGate:
    """git_push_gate.py blocks direct git push."""

    def test_git_push_blocked(self):
        r = run_hook(
            "git_push_gate.py", {"tool_input": {"command": "git push origin main"}}
        )
        assert r.returncode == 2
        assert "BLOCKED" in r.stderr

    def test_git_status_allowed(self):
        r = run_hook("git_push_gate.py", {"tool_input": {"command": "git status"}})
        assert r.returncode == 0

    def test_git_commit_allowed(self):
        r = run_hook(
            "git_push_gate.py", {"tool_input": {"command": "git commit -m 'test'"}}
        )
        assert r.returncode == 0

    def test_skip_push_hook_env(self):
        r = run_hook(
            "git_push_gate.py",
            {"tool_input": {"command": "git push origin main"}},
            env_extra={"TAUSIK_SKIP_PUSH_HOOK": "1"},
        )
        assert r.returncode == 0

    def test_skip_hooks_no_longer_bypasses_push(self):
        r = run_hook(
            "git_push_gate.py",
            {"tool_input": {"command": "git push origin main"}},
            env_extra={"TAUSIK_SKIP_HOOKS": "1"},
        )
        assert r.returncode == 2

    def test_chained_command_blocked(self):
        r = run_hook(
            "git_push_gate.py",
            {"tool_input": {"command": "cd . && git push origin main"}},
        )
        assert r.returncode == 2

    def test_absolute_path_git_blocked(self):
        r = run_hook(
            "git_push_gate.py",
            {"tool_input": {"command": "/usr/bin/git push origin main"}},
        )
        assert r.returncode == 2


class TestAutoFormat:
    """auto_format.py runs formatter and logs to task."""

    def test_nonexistent_file_allowed(self):
        r = run_hook(
            "auto_format.py", {"tool_input": {"file_path": "/nonexistent/file.py"}}
        )
        assert r.returncode == 0

    def test_no_stdin_allowed(self):
        r = run_hook("auto_format.py")
        assert r.returncode == 0

    def test_skip_hooks_env(self):
        r = run_hook(
            "auto_format.py",
            {"tool_input": {"file_path": "test.py"}},
            env_extra={"TAUSIK_SKIP_HOOKS": "1"},
        )
        assert r.returncode == 0

    def test_empty_file_path_allowed(self):
        r = run_hook("auto_format.py", {"tool_input": {"file_path": ""}})
        assert r.returncode == 0


class TestTaskGate:
    """task_gate.py blocks Write/Edit without active task."""

    def test_no_tausik_db_allows(self):
        """If no .tausik/tausik.db — not a TAUSIK project, allow."""
        r = run_hook("task_gate.py", env_extra={"CLAUDE_PROJECT_DIR": "/nonexistent"})
        assert r.returncode == 0

    def test_skip_hooks_env(self):
        r = run_hook("task_gate.py", env_extra={"TAUSIK_SKIP_HOOKS": "1"})
        assert r.returncode == 0
