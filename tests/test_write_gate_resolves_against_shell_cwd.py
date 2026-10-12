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


class TestTheScriptPathResolvesThere:
    """The FOURTH site of the same identification, and the one an inventory
    missed. `_script_file_writes` opens the script a command names, to read the
    writes inside it — and resolved that path against `project_dir` too.

    It was missed because the inventory grepped for the VARIABLE NAMES the other
    three sites used (`expanded`, `path`); this one calls it `script`. Re-done by
    CALL SITE, `join(project_dir, …)` appears many times in the hooks, but every
    other one joins a CONSTANT internal path (`.tausik/tausik.db`, `.claude/…`)
    and is correctly project-relative. This was the only one joining a path that
    arrives from outside.

    Measured before the fix, with the same script name in two trees: the parser
    returned the MAIN tree's target while the shell stood in the other one, and
    kept returning it even after the script was deleted from the tree the command
    actually runs in — a phantom and a miss in one answer.
    """

    def _two_trees(self, tmp_path):
        project = tmp_path / "core"
        foreign = tmp_path / "worktree"
        project.mkdir()
        foreign.mkdir()
        (project / "helper.py").write_text("open('PROJECT_TARGET.txt', 'w')\n", encoding="utf-8")
        (foreign / "helper.py").write_text("open('FOREIGN_TARGET.txt', 'w')\n", encoding="utf-8")
        return project, foreign

    def test_the_script_is_read_from_the_directory_the_shell_stands_in(self, tmp_path, monkeypatch):
        from bash_write_parse import write_targets

        project, foreign = self._two_trees(tmp_path)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
        assert write_targets("python helper.py", str(foreign)) == ["FOREIGN_TARGET.txt"]

    def test_without_a_base_directory_it_still_reads_the_project(self, tmp_path, monkeypatch):
        """The fallback, pinned: a caller that supplies nothing gets exactly the
        behaviour that stood before, so this change cannot quietly stop gating."""
        from bash_write_parse import write_targets

        project, _foreign = self._two_trees(tmp_path)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
        assert write_targets("python helper.py") == ["PROJECT_TARGET.txt"]

    def test_a_script_only_the_project_has_is_not_attributed_to_a_foreign_shell(
        self, tmp_path, monkeypatch
    ):
        """The sharper half of the defect: the command runs a script that does
        not exist where it stands, and the gate still named the project's."""
        from bash_write_parse import write_targets

        project, foreign = self._two_trees(tmp_path)
        (foreign / "helper.py").unlink()
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
        assert write_targets("python helper.py", str(foreign)) == []

    def test_the_gate_passes_the_shells_directory_through(self, tmp_path):
        """End-to-end, through the real hook: a script run in another checkout
        must not be judged by a same-named script in this project."""
        project = _make_project(tmp_path, "core", ["docs/**"])
        # The project's script names an ABSOLUTE in-project path. That is what
        # separates the two readings: read the project's file and the gate sees
        # an in-tree write and blocks; read the foreign one and it sees a write
        # in another tree and stands down. With a relative target both readings
        # land outside and the test could not tell them apart — which is exactly
        # how the first version of it passed while the wiring was mutated away.
        stolen = str(project / "scripts" / "stolen.py").replace("\\", "/")
        (project / "helper.py").write_text(f"open({stolen!r}, 'w')\n", encoding="utf-8")
        foreign = tmp_path / "worktree"
        foreign.mkdir()
        (foreign / "helper.py").write_text("open('own.txt', 'w')\n", encoding="utf-8")
        result = _bash(project, "python helper.py", cwd=foreign)
        assert result.returncode == 0, (
            "a script run in another checkout was judged by this project's same-named "
            f"file: {result.stdout} {result.stderr}"
        )

    def test_the_same_script_at_home_is_still_judged(self, tmp_path):
        """The other side of it: standing in the project, the gate must still
        read the script and still refuse a write outside the declared scope."""
        project = _make_project(tmp_path, "core", ["docs/**"])
        stolen = str(project / "scripts" / "stolen.py").replace("\\", "/")
        (project / "helper.py").write_text(f"open({stolen!r}, 'w')\n", encoding="utf-8")
        result = _bash(project, "python helper.py", cwd=project)
        assert result.returncode == 2, (
            f"the gate stopped reading a script run in the project: {result.stderr}"
        )


class TestACommandThatMovesTheShellFailsClosed:
    """The regression the previous two fixes introduced, and its cure.

    The event's `cwd` is where the shell stood BEFORE the command ran. Resolving
    against it is right for `python helper.py`, and WRONG for
    `cd <project> && python helper.py` — by the time the script is named the
    shell is somewhere else. Measured on the live gate: that command went from
    exit 2 to exit 0, while the same command with no `cwd` field at all — the
    pre-fix resolution — still returned 2. For that shape the old root was
    accidentally correct and the fix made it wrong, which is precisely the
    under-detection both tasks' acceptance criteria forbade.

    The cure is not to guess where the shell ends up. When the command moves,
    both roots are judged and the union is kept: for a containment gate an extra
    candidate costs a task the write would have needed anyway, while choosing
    the wrong root loses the write in silence — `_script_file_writes` fails soft
    on a missing file, so there is not even an error to notice.
    """

    def _project_with_a_script(self, tmp_path):
        project = _make_project(tmp_path, "core", ["docs/**"])
        stolen = str(project / "scripts" / "stolen.py").replace("\\", "/")
        (project / "helper.py").write_text(f"open({stolen!r}, 'w')\n", encoding="utf-8")
        elsewhere = tmp_path / "scratch"
        elsewhere.mkdir()
        return project, elsewhere

    @pytest.mark.parametrize(
        "shape",
        [
            "cd {p} && python helper.py",
            "(cd {p}; python helper.py)",
            "pushd {p} && python helper.py",
        ],
        ids=["cd-and", "subshell", "pushd"],
    )
    def test_a_command_that_moves_into_the_project_is_still_gated(self, tmp_path, shape):
        project, elsewhere = self._project_with_a_script(tmp_path)
        command = shape.format(p=str(project).replace("\\", "/"))
        result = _bash(project, command, cwd=elsewhere)
        assert result.returncode == 2, (
            f"{command!r} run from outside was allowed. The shell moves into the project "
            "before the write, so trusting the pre-command cwd turns a block into an "
            f"allow: {result.stdout} {result.stderr}"
        )

    def test_a_plain_write_after_moving_into_the_project_is_still_gated(self, tmp_path):
        """The other write vector. The script case is caught inside the parser;
        this one is caught where the gate turns a raw target into a path, and
        the two are separate code — a mutation removing either survives the
        other's tests."""
        project = _make_project(tmp_path, "core", ["docs/**"])
        elsewhere = tmp_path / "scratch"
        elsewhere.mkdir()
        command = f"cd {str(project).replace(chr(92), '/')} && touch scripts/stolen.py"
        result = _bash(project, command, cwd=elsewhere)
        assert result.returncode == 2, (
            f"a redirect-style write after a `cd` into the project was allowed: {result.stderr}"
        )

    def test_a_command_that_does_not_move_keeps_the_fix(self, tmp_path):
        """The cure must not reinstate the false block it replaced: an ordinary
        command in another checkout still passes."""
        project = _make_project(tmp_path, "core", ["docs/**"])
        worktree = tmp_path / "bare-204"
        (worktree / ".tausik").mkdir(parents=True)
        result = _bash(project, "touch .tausik/tausik.db", cwd=worktree)
        assert result.returncode == 0, (
            f"the cd guard reinstated the false block it was meant to keep fixed: {result.stderr}"
        )


class TestTheDirectoryChangeDetector:
    """Asked of the token stream, so a word inside a path is not a command."""

    @pytest.mark.parametrize(
        "command",
        [
            "cd /tmp && touch x",
            "(cd /tmp; touch x)",
            "pushd /tmp && touch x",
            "env -C /tmp touch x",
        ],
        ids=["cd", "subshell", "pushd", "env-C"],
    )
    def test_a_real_directory_change_is_seen(self, command):
        from bash_write_parse import command_changes_directory

        assert command_changes_directory(command)

    @pytest.mark.parametrize(
        "command",
        ["cp cd.txt out.txt", "echo 'cd /tmp'", "touch pushd", "env FOO=1 touch x"],
        ids=["cd-in-a-filename", "cd-in-a-quoted-string", "pushd-as-a-filename", "env-without-C"],
    )
    def test_a_mere_mention_is_not_a_directory_change(self, command):
        """A false positive here costs nothing but a widened search; a false
        NEGATIVE is the regression. Still, mistaking every `cd` in prose for a
        move would drag the project root into every judgement and blunt the
        measurement the base directory exists to make."""
        from bash_write_parse import command_changes_directory

        assert not command_changes_directory(command)


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
