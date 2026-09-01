"""A relative write target belongs to the SHELL's cwd, not to the project dir.

write-gate-resolves-relative-paths-against-the-wrong-directory. Three hooks
turned a relative target into an absolute one by joining it to `project_dir`,
each with a comment asserting that the shell's cwd *is* the project dir. True
for ordinary work; false the moment the agent works in a second checkout.

Session #204 met it live: inside a `git worktree`, a command touching
`.tausik/tausik.db*` was refused as a write to the MAIN repository, which it
never touches.

A correction to that record, measured rather than repeated: the task's goal
quotes the command as `rm -f .tausik/tausik.db*`, and `rm` produces NO write
target at all here — `write_targets` returns `[]` for every `rm` form. So the
refusal cannot have come from that command through this gate, and the tests
below use a command that really is a writer. Repeating the quoted command would
have made this file pass vacuously: with no target, the gate returns 0 whether
or not the defect exists.

That matters beyond the nuisance — decision #299 makes "does this work from
someone else's clean clone" a release requirement, memory #501 says the honest
way to measure it is a `git worktree`, and the gate obstructed exactly that
check. The workaround was absolute paths, which had to be discovered by being
blocked.

WHAT WAS MEASURED FIRST, BEFORE ANY DESIGN. Whether the event carries the real
working directory, read off a live PreToolUse payload rather than assumed: it
does, as `cwd`, and it tracks a `cd` from an earlier call (after `cd d:/tmp` the
field read `D:\\tmp`, not the project root).

DIRECTION OF THE DEFECT. This was over-detection — a foreign tree mistaken for
this one — so the fix must not become under-detection. Two things hold that
line, and both are asserted below: the containment test still runs on the
RESOLVED absolute path, so a relative path that climbs back into the project is
still caught; and when the event cannot say where the shell stands, the
resolution falls back to `project_dir` and the write stays gated.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys

import pytest
from conftest import canonical_ddl

_TESTS = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_TESTS, "..", "scripts"))
_HOOKS = os.path.join(_SCRIPTS, "hooks")
for _p in (_SCRIPTS, _HOOKS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _common import shell_cwd  # noqa: E402

_BASH_GATE = os.path.join(_HOOKS, "bash_write_gate.py")
_TASK_GATE = os.path.join(_HOOKS, "task_gate.py")


def _make_project(tmp_path, name, scope_paths):
    """A project directory with a DB holding one active task and its ACL."""
    root = tmp_path / name
    (root / ".tausik").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(root / ".tausik" / "tausik.db"))
    conn.execute(canonical_ddl("tasks"))
    conn.execute(
        "INSERT INTO tasks (slug, title, status, scope_paths, created_at, updated_at) "
        "VALUES ('t', 't', 'active', ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
        (json.dumps(scope_paths),),
    )
    conn.commit()
    conn.close()
    return root


def _run(hook, project_dir, payload):
    env = os.environ.copy()
    env["TAUSIK_SKIP_HOOKS"] = ""
    env["TAUSIK_HOOK_FAIL_SECURE"] = ""
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        [sys.executable, hook],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=20,
    )


def _bash(project_dir, command, cwd=None):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    if cwd is not None:
        payload["cwd"] = str(cwd)
    return _run(_BASH_GATE, project_dir, payload)


class TestShellCwd:
    """The resolver on its own. Its fallback IS the security property."""

    def test_the_events_cwd_wins_when_it_is_a_real_directory(self, tmp_path):
        other = tmp_path / "other"
        other.mkdir()
        assert shell_cwd({"cwd": str(other)}, str(tmp_path)) == str(other)

    @pytest.mark.parametrize(
        "event",
        [
            {},  # no cwd at all — an older host, or another event shape
            {"cwd": ""},
            {"cwd": "   "},
            {"cwd": 17},  # not a string
            {"cwd": None},
            "not-a-dict",
        ],
        ids=["absent", "empty", "blank", "not-a-string", "null", "not-a-dict"],
    )
    def test_anything_unusable_falls_back_to_the_project(self, tmp_path, event):
        """Fail toward gating. A gate that cannot establish where the shell
        stands must keep judging relative paths as the project's, not stop."""
        assert shell_cwd(event, str(tmp_path)) == str(tmp_path)

    def test_a_cwd_that_does_not_exist_falls_back(self, tmp_path):
        missing = tmp_path / "gone"
        assert shell_cwd({"cwd": str(missing)}, str(tmp_path)) == str(tmp_path)


class TestTheFalseBlockIsGone:
    def test_a_write_in_another_checkout_is_not_this_projects_business(self, tmp_path):
        """The #204 command, reproduced. `.tausik/tausik.db` relative to a second
        worktree is a file in THAT tree — nothing in the main repository."""
        project = _make_project(tmp_path, "core", ["docs/**"])
        worktree = tmp_path / "bare-204"
        (worktree / ".tausik").mkdir(parents=True)
        result = _bash(project, "touch .tausik/tausik.db", cwd=worktree)
        assert result.returncode == 0, (
            "a command working inside another checkout was refused as a write to this "
            f"project — the block that obstructed the clean-clone check: {result.stderr}"
        )


class TestTheRealBlockRemains:
    """The fix must not turn over-detection into under-detection."""

    def test_the_same_relative_write_is_still_gated_at_home(self, tmp_path):
        project = _make_project(tmp_path, "core", ["docs/**"])
        result = _bash(project, "touch .tausik/tausik.db", cwd=project)
        assert result.returncode == 2, (
            "a relative write inside the project itself must still be judged against "
            f"the ACL: {result.stdout} {result.stderr}"
        )

    def test_a_relative_path_that_climbs_back_into_the_project_is_caught(self, tmp_path):
        """The containment test runs on the RESOLVED path, so standing outside
        and reaching back in is not an escape."""
        project = _make_project(tmp_path, "core", ["docs/**"])
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        result = _bash(project, "cp a.txt ../core/scripts/stolen.py", cwd=elsewhere)
        assert result.returncode == 2, (
            "a path resolved from a sibling directory back INTO the project escaped "
            f"the ACL: {result.stdout} {result.stderr}"
        )

    def test_without_a_cwd_the_write_is_still_gated(self, tmp_path):
        """An event that carries no cwd must behave as it always did."""
        project = _make_project(tmp_path, "core", ["docs/**"])
        result = _bash(project, "touch .tausik/tausik.db", cwd=None)
        assert result.returncode == 2, (
            f"a payload without cwd stopped gating relative writes: {result.stderr}"
        )

    def test_an_absolute_write_into_the_project_is_gated_from_anywhere(self, tmp_path):
        project = _make_project(tmp_path, "core", ["docs/**"])
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        target = os.path.join(str(project), "scripts", "stolen.py").replace("\\", "/")
        result = _bash(project, f"cp a.txt {target}", cwd=elsewhere)
        assert result.returncode == 2, f"absolute in-project write escaped: {result.stderr}"


class TestTheMemoryRouteGateAgrees:
    """The third hook that resolved relative targets. Its tree-scoped sinks —
    `.cursor/rules/**`, `.windsurf/rules/**`, `.github/copilot-instructions.md`
    — are PROJECT-RELATIVE, which is what makes the base directory observable
    here at all: a foreign checkout's `.cursor/rules/x.md` was being judged as
    this project's."""

    def _memory_gate(self, project_dir, command, cwd=None):
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        if cwd is not None:
            payload["cwd"] = str(cwd)
        return _run(os.path.join(_HOOKS, "memory_pretool_block.py"), project_dir, payload)

    def test_a_foreign_checkouts_rules_file_is_not_this_projects_sink(self, tmp_path):
        project = _make_project(tmp_path, "core", ["docs/**"])
        worktree = tmp_path / "bare-204"
        (worktree / ".cursor" / "rules").mkdir(parents=True)
        result = self._memory_gate(project, "cp notes.md .cursor/rules/x.md", cwd=worktree)
        assert result.returncode == 0, (
            "a rules file in ANOTHER checkout was judged as this project's memory "
            f"sink: {result.stderr}"
        )


class TestTheQG0GateAgrees:
    """task_gate decides the same jurisdiction question for Write/Edit, and it
    carried the same identification. The two gates must not disagree about what
    counts as this project."""

    def _task_gate(self, project_dir, file_path, cwd=None):
        payload = {"tool_name": "Write", "tool_input": {"file_path": file_path}}
        if cwd is not None:
            payload["cwd"] = str(cwd)
        return _run(_TASK_GATE, project_dir, payload)

    def test_a_relative_edit_in_another_checkout_is_out_of_jurisdiction(self, tmp_path):
        project = _make_project(tmp_path, "core", ["docs/**"])
        # No active task is required for the point: the gate must return 0
        # because the target is outside, not because a task exists.
        conn = sqlite3.connect(str(project / ".tausik" / "tausik.db"))
        conn.execute("UPDATE tasks SET status = 'done'")
        conn.commit()
        conn.close()
        worktree = tmp_path / "bare-204"
        worktree.mkdir()
        result = self._task_gate(project, "notes.md", cwd=worktree)
        assert result.returncode == 0, (
            f"an edit in another checkout was blocked for lacking a task here: {result.stderr}"
        )

    def test_a_relative_edit_at_home_still_needs_a_task(self, tmp_path):
        project = _make_project(tmp_path, "core", ["docs/**"])
        conn = sqlite3.connect(str(project / ".tausik" / "tausik.db"))
        conn.execute("UPDATE tasks SET status = 'done'")
        conn.commit()
        conn.close()
        result = self._task_gate(project, "notes.md", cwd=project)
        assert result.returncode == 2, (
            f"QG-0 stopped applying to a relative path in the project: {result.stderr}"
        )
