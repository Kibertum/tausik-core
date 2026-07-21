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
            # v1.7 (l26-bash-firewall-substring): BLOCKED patterns were matched
            # as lowercased substrings of the raw line, so a dangerous phrase
            # carried as DATA tripped the firewall. Filing this very fix was
            # blocked twice. The split is by whether the invoked program
            # executes its arguments.
            pytest.param(
                '.tausik/tausik task log t1 "note: never DROP TABLE events"',
                0,
                id="journal_carrying_sql_phrase_allowed",
            ),
            pytest.param(
                'sqlite3 db.db "DROP TABLE users"',
                2,
                id="sqlite3_double_quoted_sql_blocked",
            ),
            pytest.param('echo "rm -rf /"', 0, id="echo_quoted_rm_rf_allowed"),
            pytest.param('bash -c "rm -rf /"', 2, id="bash_c_quoted_rm_rf_blocked"),
            pytest.param(
                'git commit -m "do not git push --force here"',
                0,
                id="commit_message_mentioning_force_push_allowed",
            ),
            # l26-firewall-quote-regression: the first version of the fix above
            # blanked quoted spans, treating quoting as proof the text was inert
            # data. It is not — a quoted argument is still an argument, and bash
            # expands inside double quotes. Adversarial review found three
            # bypasses; all three were confirmed allowed before this pin.
            pytest.param('rm -rf "/"', 2, id="quoted_slash_arg_still_blocked"),
            pytest.param('rm -rf "."', 2, id="quoted_dot_arg_still_blocked"),
            pytest.param('git push "--force"', 2, id="quoted_force_flag_still_blocked"),
            pytest.param(
                'git push origin main "--force"',
                2,
                id="quoted_force_flag_after_args_blocked",
            ),
            pytest.param(
                'timeout 10 bash -c "rm -rf /"',
                2,
                id="wrapper_timeout_hiding_shell_blocked",
            ),
            pytest.param('exec bash -c "rm -rf /"', 2, id="wrapper_exec_hiding_shell_blocked"),
            pytest.param('nice -n 10 sh -c "rm -rf /"', 2, id="wrapper_nice_hiding_shell_blocked"),
            pytest.param(
                'powershell -Command "rm -rf /"',
                2,
                id="windows_shell_payload_blocked",
            ),
            pytest.param(
                'sqlite3 db.db "DROP TABLE users"',
                2,
                id="interpreter_double_quoted_sql_blocked",
            ),
            # Each sub-command is judged on its own. One interpreter anywhere on
            # the line used to force a raw scan of the whole line, so a journal
            # entry sharing a line with a python invocation was blocked again
            # for a phrase it merely quoted.
            pytest.param(
                'tausik task log t1 "never DROP TABLE events"; python -m pytest tests/',
                0,
                id="journal_beside_interpreter_on_same_line_allowed",
            ),
            pytest.param(
                'echo "safe" && rm -rf "/"',
                2,
                id="dangerous_subcommand_after_separator_still_blocked",
            ),
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
    """git_push_gate.py blocks direct git push without a valid push ticket.

    v1.4 contract: bypass via single-use ticket file at .tausik/.push_ticket.json
    (written by `tausik push-ok`). Hook validates schema, expiry, and
    HEAD-SHA match; consumes (deletes) on success. Old TAUSIK_ALLOW_PUSH
    env path was removed (it never worked — Bash inline env doesn't reach
    PreToolUse hooks running in harness env).
    """

    @staticmethod
    def _head_sha() -> str:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], encoding="utf-8").strip()

    @staticmethod
    def _write_ticket(path, *, sha, expires_iso, schema_version=1, branch="main"):
        from datetime import datetime, timezone

        payload = {
            "schema_version": schema_version,
            "commit_sha": sha,
            "branch": branch,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_iso,
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _push_with_ticket(self, ticket_path):
        return run_hook(
            "git_push_gate.py",
            {"tool_input": {"command": "git push origin main"}},
            env_extra={"TAUSIK_PUSH_TICKET_PATH": str(ticket_path)},
        )

    def test_git_push_blocked_without_ticket(self, tmp_path):
        ticket = tmp_path / ".push_ticket.json"  # does not exist
        r = self._push_with_ticket(ticket)
        assert r.returncode == 2
        assert "BLOCKED" in r.stderr
        assert "no push ticket" in r.stderr

    def test_git_status_allowed(self):
        r = run_hook("git_push_gate.py", {"tool_input": {"command": "git status"}})
        assert r.returncode == 0

    def test_git_commit_allowed(self):
        r = run_hook("git_push_gate.py", {"tool_input": {"command": "git commit -m 'test'"}})
        assert r.returncode == 0

    def test_chained_command_blocked_without_ticket(self, tmp_path):
        ticket = tmp_path / ".push_ticket.json"
        r = run_hook(
            "git_push_gate.py",
            {"tool_input": {"command": "cd . && git push origin main"}},
            env_extra={"TAUSIK_PUSH_TICKET_PATH": str(ticket)},
        )
        assert r.returncode == 2

    def test_absolute_path_git_blocked_without_ticket(self, tmp_path):
        ticket = tmp_path / ".push_ticket.json"
        r = run_hook(
            "git_push_gate.py",
            {"tool_input": {"command": "/usr/bin/git push origin main"}},
            env_extra={"TAUSIK_PUSH_TICKET_PATH": str(ticket)},
        )
        assert r.returncode == 2

    def test_quoted_push_mention_not_treated_as_push(self, tmp_path):
        """Substring false-positive: 'git push' inside a QUOTED argument (e.g.
        `tausik memory add "...git push..."` when journaling a mirror recipe)
        must not be treated as a push. Token-based detection keeps a quoted
        string as one token, so it is allowed even with no ticket present."""
        ticket = tmp_path / ".push_ticket.json"  # absent — a real push would block
        r = run_hook(
            "git_push_gate.py",
            {
                "tool_input": {
                    "command": '.tausik/tausik memory add pattern t "recipe: git push tmp:main"'
                }
            },
            env_extra={"TAUSIK_PUSH_TICKET_PATH": str(ticket)},
        )
        assert r.returncode == 0, r.stderr

    def test_commit_with_push_word_in_message_allowed(self):
        r = run_hook(
            "git_push_gate.py",
            {"tool_input": {"command": 'git commit -m "wire up the push flow"'}},
        )
        assert r.returncode == 0

    def test_dash_c_flag_before_push_blocked_without_ticket(self, tmp_path):
        """A real push behind a `-c` global flag must still be caught."""
        ticket = tmp_path / ".push_ticket.json"
        r = run_hook(
            "git_push_gate.py",
            {"tool_input": {"command": "git -c protocol.version=2 push origin main"}},
            env_extra={"TAUSIK_PUSH_TICKET_PATH": str(ticket)},
        )
        assert r.returncode == 2

    def test_valid_ticket_allows_push_and_consumes_it(self, tmp_path):
        from datetime import datetime, timedelta, timezone

        ticket = tmp_path / ".push_ticket.json"
        future = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        self._write_ticket(ticket, sha=self._head_sha(), expires_iso=future)
        r = self._push_with_ticket(ticket)
        assert r.returncode == 0, r.stderr
        assert not ticket.exists(), "ticket must be consumed (deleted) on allow"

    def test_expired_ticket_blocks_and_deletes(self, tmp_path):
        from datetime import datetime, timedelta, timezone

        ticket = tmp_path / ".push_ticket.json"
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        self._write_ticket(ticket, sha=self._head_sha(), expires_iso=past)
        r = self._push_with_ticket(ticket)
        assert r.returncode == 2
        assert "expired" in r.stderr
        assert not ticket.exists(), "expired ticket should be cleaned up"

    def test_sha_mismatch_blocks_and_keeps_ticket(self, tmp_path):
        from datetime import datetime, timedelta, timezone

        ticket = tmp_path / ".push_ticket.json"
        future = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        self._write_ticket(ticket, sha="0" * 40, expires_iso=future)
        r = self._push_with_ticket(ticket)
        assert r.returncode == 2
        assert "SHA mismatch" in r.stderr
        assert ticket.exists(), "SHA-mismatched ticket must NOT be consumed"

    def test_malformed_ticket_blocks(self, tmp_path):
        ticket = tmp_path / ".push_ticket.json"
        ticket.write_text("not-json{", encoding="utf-8")
        r = self._push_with_ticket(ticket)
        assert r.returncode == 2
        assert "malformed" in r.stderr

    def test_wrong_schema_version_blocks(self, tmp_path):
        from datetime import datetime, timedelta, timezone

        ticket = tmp_path / ".push_ticket.json"
        future = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        self._write_ticket(ticket, sha=self._head_sha(), expires_iso=future, schema_version=99)
        r = self._push_with_ticket(ticket)
        assert r.returncode == 2
        assert "schema_version" in r.stderr

    def test_one_shot_second_push_blocked(self, tmp_path):
        """Ticket is single-use: second push after consume must block."""
        from datetime import datetime, timedelta, timezone

        ticket = tmp_path / ".push_ticket.json"
        future = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        self._write_ticket(ticket, sha=self._head_sha(), expires_iso=future)
        r1 = self._push_with_ticket(ticket)
        assert r1.returncode == 0, r1.stderr
        r2 = self._push_with_ticket(ticket)
        assert r2.returncode == 2
        assert "no push ticket" in r2.stderr

    def test_skip_push_hook_env_still_bypasses(self, tmp_path):
        """TAUSIK_SKIP_PUSH_HOOK=1 remains as debug-only bypass."""
        ticket = tmp_path / ".push_ticket.json"  # does not exist
        r = run_hook(
            "git_push_gate.py",
            {"tool_input": {"command": "git push origin main"}},
            env_extra={
                "TAUSIK_PUSH_TICKET_PATH": str(ticket),
                "TAUSIK_SKIP_PUSH_HOOK": "1",
            },
        )
        assert r.returncode == 0

    def test_old_allow_push_env_no_longer_bypasses(self, tmp_path):
        """The historical TAUSIK_ALLOW_PUSH=1 path was broken-by-design and
        is now removed. Setting it must NOT bypass the gate."""
        ticket = tmp_path / ".push_ticket.json"  # does not exist
        r = run_hook(
            "git_push_gate.py",
            {"tool_input": {"command": "git push origin main"}},
            env_extra={
                "TAUSIK_PUSH_TICKET_PATH": str(ticket),
                "TAUSIK_ALLOW_PUSH": "1",
            },
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


# Module-level: G54 — env-based skip/no-skip behavior across git_push_gate and auto_format
@pytest.mark.parametrize(
    "script,command_or_path,env_extra,expected_returncode",
    [
        pytest.param(
            "auto_format.py",
            {"file_path": "test.py"},
            {"TAUSIK_SKIP_HOOKS": "1"},
            0,
            id="auto_format_skip_hooks_env",
        ),
    ],
)
def test_hook_skip_env_returncode(script, command_or_path, env_extra, expected_returncode):
    """git_push_gate skip-env coverage moved into TestGitPushGate, where the
    ticket path can be isolated via TAUSIK_PUSH_TICKET_PATH per-test."""
    r = run_hook(script, {"tool_input": command_or_path}, env_extra=env_extra)
    assert r.returncode == expected_returncode


class TestTaskGateJurisdiction:
    """The gate governs THIS project's files — not every file on the machine.

    Found by dogfooding in session #125: with TAUSIK open as the session project
    and an edit landing in a sibling repository (which had its own coordinator
    and its own active task), the gate refused. Its warrant is "no code without a
    task IN THIS PROJECT"; it has no standing over another repository. The cost
    of getting this wrong is not friction — it is that the only ways forward are
    abandoning legitimate work or opening a FICTITIOUS task here, and a gate that
    is profitable to fake stops protecting this project too.

    Direction matters in every case below: the loosening must apply ONLY to a
    target proven to be outside, never to one merely not proven inside.
    """

    @staticmethod
    def _project(tmp_path):
        """A directory that looks like a real TAUSIK project with no active task."""
        proj = tmp_path / "core"
        (proj / ".tausik").mkdir(parents=True)
        import sqlite3

        conn = sqlite3.connect(str(proj / ".tausik" / "tausik.db"))
        conn.execute("CREATE TABLE tasks (slug TEXT, status TEXT)")
        conn.execute("INSERT INTO tasks VALUES ('idle-task', 'planning')")
        conn.commit()
        conn.close()
        return proj

    def test_outside_file_is_allowed_without_a_task(self, tmp_path):
        """The reported defect, closed: a sibling repo's file edits freely."""
        proj = self._project(tmp_path)
        other = tmp_path / "other-repo" / "app.py"
        other.parent.mkdir(parents=True)
        other.write_text("x = 1", encoding="utf-8")
        r = run_hook(
            "task_gate.py",
            {"tool_input": {"file_path": str(other)}},
            env_extra={"CLAUDE_PROJECT_DIR": str(proj)},
        )
        assert r.returncode == 0, r.stderr

    def test_inside_file_is_still_blocked(self, tmp_path):
        """Protection of this project is NOT weakened — the whole point."""
        proj = self._project(tmp_path)
        inside = proj / "scripts" / "thing.py"
        inside.parent.mkdir(parents=True)
        inside.write_text("x = 1", encoding="utf-8")
        r = run_hook(
            "task_gate.py",
            {"tool_input": {"file_path": str(inside)}},
            env_extra={"CLAUDE_PROJECT_DIR": str(proj)},
        )
        assert r.returncode == 2, "an in-project edit without a task must be refused"

    def test_prefix_sibling_is_outside_not_inside(self, tmp_path):
        """`…/core-old` next to `…/core` is a DIFFERENT project.

        A startswith test calls it inside and gates it — wrong, and wrong in the
        direction that blocks legitimate work. commonpath answers correctly.
        """
        proj = self._project(tmp_path)
        sibling = tmp_path / "core-old" / "app.py"
        sibling.parent.mkdir(parents=True)
        sibling.write_text("x = 1", encoding="utf-8")
        r = run_hook(
            "task_gate.py",
            {"tool_input": {"file_path": str(sibling)}},
            env_extra={"CLAUDE_PROJECT_DIR": str(proj)},
        )
        assert r.returncode == 0, r.stderr

    def test_relative_path_resolves_into_the_project_and_is_blocked(self, tmp_path):
        proj = self._project(tmp_path)
        r = run_hook(
            "task_gate.py",
            {"tool_input": {"file_path": "scripts/thing.py"}},
            env_extra={"CLAUDE_PROJECT_DIR": str(proj)},
        )
        assert r.returncode == 2, "a relative path belongs to the project and stays gated"

    def test_dotdot_escape_from_inside_is_outside(self, tmp_path):
        """`…/core/../other/app.py` really is outside once normalised."""
        proj = self._project(tmp_path)
        (tmp_path / "other").mkdir()
        r = run_hook(
            "task_gate.py",
            {"tool_input": {"file_path": str(proj / ".." / "other" / "app.py")}},
            env_extra={"CLAUDE_PROJECT_DIR": str(proj)},
        )
        assert r.returncode == 0, r.stderr

    @pytest.mark.parametrize(
        "payload,label",
        [
            ({}, "no tool_input at all"),
            ({"tool_input": {}}, "tool_input without a path"),
            ({"tool_input": {"file_path": ""}}, "empty path"),
            ({"tool_input": {"file_path": None}}, "null path"),
            ({"tool_input": {"file_path": 42}}, "non-string path"),
            ({"tool_input": "not-a-dict"}, "tool_input of the wrong type"),
        ],
    )
    def test_unclassifiable_input_stays_gated(self, tmp_path, payload, label):
        """FAIL-CLOSED: what cannot be proven outside is treated as inside.

        This is the half that makes the loosening safe. Without it, any payload
        the parser trips over becomes a free bypass of the task requirement —
        which would be a strictly worse defect than the one being fixed.
        """
        proj = self._project(tmp_path)
        r = run_hook("task_gate.py", payload, env_extra={"CLAUDE_PROJECT_DIR": str(proj)})
        assert r.returncode == 2, f"{label} must keep the gate ON"

    def test_malformed_stdin_stays_gated(self, tmp_path):
        """Not valid JSON at all — still gated."""
        proj = self._project(tmp_path)
        env = os.environ.copy()
        env["TAUSIK_SKIP_HOOKS"] = ""
        env["CLAUDE_PROJECT_DIR"] = str(proj)
        r = subprocess.run(
            [sys.executable, os.path.join(HOOKS_DIR, "task_gate.py")],
            input="{not json at all",
            capture_output=True,
            text=True,
            encoding="utf-8",  # never inherit the parent's — the hook prints non-ASCII
            env=env,
        )
        assert r.returncode == 2

    def test_active_task_allows_an_inside_edit(self, tmp_path):
        """Sanity: the gate still opens the normal way, so the tests above are
        measuring jurisdiction rather than a gate that blocks unconditionally."""
        proj = self._project(tmp_path)
        import sqlite3

        conn = sqlite3.connect(str(proj / ".tausik" / "tausik.db"))
        conn.execute("UPDATE tasks SET status = 'active'")
        conn.commit()
        conn.close()
        r = run_hook(
            "task_gate.py",
            {"tool_input": {"file_path": str(proj / "scripts" / "thing.py")}},
            env_extra={"CLAUDE_PROJECT_DIR": str(proj)},
        )
        assert r.returncode == 0, r.stderr
