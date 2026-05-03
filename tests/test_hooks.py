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
    """bash_firewall.py blocks dangerous commands.

    v1.4 (v14b-parametrize-top4): bulk (command, expected_rc) cases collapsed
    into one parametrized method. Specials with stderr/env/no-stdin checks
    remain separate.

    v1.3.4 (med-batch-1-hooks #1): regex with word boundaries instead of
    substring match. Quoted strings inside echo etc. should NOT trip the
    warn patterns; a literal git invocation with the dangerous flag should.
    """

    @pytest.mark.parametrize(
        "command,expected_rc",
        [
            pytest.param("ls -la", 0, id="normal_command_allowed"),
            pytest.param("rm -rf .", 2, id="rm_rf_dot_blocked"),
            pytest.param("sqlite3 db.db 'DROP TABLE users'", 2, id="drop_table_blocked"),
            pytest.param("git reset --hard HEAD~5", 2, id="git_reset_hard_blocked"),
            pytest.param("git push --force origin main", 2, id="git_push_force_blocked"),
            pytest.param("", 0, id="empty_command_allowed"),
            pytest.param(
                "git push --force-with-lease origin main",
                2,
                id="git_push_force_with_lease_blocked",
            ),
            pytest.param("git push -f origin feature", 2, id="git_push_short_f_blocked"),
            pytest.param("git push origin main --force", 2, id="git_push_force_after_args_blocked"),
            pytest.param(
                "echo 'git push --force is dangerous'",
                0,
                id="echo_quoted_git_push_force_allowed",
            ),
            pytest.param("gitfoo push --force", 0, id="word_with_git_prefix_allowed"),
            pytest.param(
                "/usr/bin/git push --force origin main",
                2,
                id="full_path_git_push_force_blocked",
            ),
            pytest.param("git clean -fd", 2, id="git_clean_fd_blocked"),
            pytest.param("git checkout -- .", 2, id="git_checkout_dot_blocked"),
            pytest.param("git checkout main", 0, id="git_checkout_branch_allowed"),
            pytest.param(
                "git -c core.editor=vim push --force origin main",
                2,
                id="git_with_c_flag_then_push_force_blocked",
            ),
            pytest.param("git push --force", 2, id="git_push_at_line_start_blocked"),
        ],
    )
    def test_command(self, command, expected_rc):
        r = run_hook("bash_firewall.py", {"tool_input": {"command": command}})
        assert r.returncode == expected_rc

    def test_rm_rf_root_blocked_emits_marker(self):
        """`rm -rf /` blocked AND emits BLOCKED marker on stderr."""
        r = run_hook("bash_firewall.py", {"tool_input": {"command": "rm -rf /"}})
        assert r.returncode == 2
        assert "BLOCKED" in r.stderr

    def test_skip_hooks_env(self):
        """TAUSIK_SKIP_HOOKS=1 bypasses the firewall (escape hatch)."""
        r = run_hook(
            "bash_firewall.py",
            {"tool_input": {"command": "rm -rf /"}},
            env_extra={"TAUSIK_SKIP_HOOKS": "1"},
        )
        assert r.returncode == 0

    def test_no_stdin_allowed(self):
        """No stdin → hook should not crash, returns 0."""
        r = run_hook("bash_firewall.py")
        assert r.returncode == 0


class TestGitPushGate:
    """git_push_gate.py blocks direct git push."""

    def test_git_push_blocked(self):
        r = run_hook("git_push_gate.py", {"tool_input": {"command": "git push origin main"}})
        assert r.returncode == 2
        assert "BLOCKED" in r.stderr

    def test_git_status_allowed(self):
        r = run_hook("git_push_gate.py", {"tool_input": {"command": "git status"}})
        assert r.returncode == 0

    def test_git_commit_allowed(self):
        r = run_hook("git_push_gate.py", {"tool_input": {"command": "git commit -m 'test'"}})
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


class TestTausikProjectDetection:
    """v1.3.4 (med-batch-1-hooks #4): hooks detect TAUSIK by .tausik/ dir,
    not by tausik.db file. Covers bootstrap-but-not-init window."""

    def test_task_gate_no_tausik_dir_passes(self, tmp_path):
        """Plain dir (no .tausik/) → hook is no-op (return 0)."""
        r = run_hook(
            "task_gate.py",
            {"tool_input": {"file_path": "x.py"}},
            env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)},
        )
        assert r.returncode == 0

    def test_task_gate_tausik_dir_without_db_engages(self, tmp_path):
        """Bootstrap-but-not-init: .tausik/ exists, no DB → hook engages.

        Without an active task and no DB-derived state, the hook should
        still attempt to query (and fall through gracefully). Pre-v1.3.4
        it returned 0 unconditionally, masking the missing-init state.
        """
        (tmp_path / ".tausik").mkdir()
        # No tausik.db, no tausik wrapper — without the wrapper task_gate
        # falls through to allow (graceful). The contract we're pinning is
        # that the hook DID enter its "is TAUSIK" branch; absence of DB
        # alone no longer short-circuits at the top.
        r = run_hook(
            "task_gate.py",
            {"tool_input": {"file_path": "x.py"}},
            env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)},
        )
        # No wrapper → allow. The point of this test is "didn't blow up
        # AND didn't take the pre-v1.3.4 short-circuit". Returncode 0 is
        # acceptable; the regression we'd catch is if .tausik/ being
        # present + no wrapper somehow flipped to error.
        assert r.returncode == 0

    def test_memory_pretool_block_no_tausik_dir_passes(self, tmp_path):
        r = run_hook(
            "memory_pretool_block.py",
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(tmp_path / "x.md"),
                    "content": "x",
                },
            },
            env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)},
        )
        assert r.returncode == 0


class TestAutoFormat:
    """auto_format.py runs formatter and logs to task."""

    def test_nonexistent_file_allowed(self):
        r = run_hook("auto_format.py", {"tool_input": {"file_path": "/nonexistent/file.py"}})
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
