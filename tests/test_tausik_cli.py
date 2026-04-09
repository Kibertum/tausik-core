"""Tests for TAUSIK CLI — smoke tests via subprocess."""

import os
import subprocess
import sys

import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
PROJECT_PY = os.path.join(SCRIPTS_DIR, "project.py")


@pytest.fixture
def tausik_env(tmp_path):
    """Set up a temporary TAUSIK project with .tausik/ dir and DB."""
    import json

    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    # Disable all gates in test env to prevent pytest-in-pytest recursion
    (tausik_dir / "config.json").write_text(
        json.dumps(
            {
                "gates": {
                    "pytest": {"enabled": False},
                    "ruff": {"enabled": False},
                    "filesize": {"enabled": False},
                }
            }
        )
    )
    env = os.environ.copy()
    env["TAUSIK_DIR"] = str(tausik_dir)
    return tmp_path, env


def run_cli(
    args: list[str], env: dict, cwd: str | None = None
) -> subprocess.CompletedProcess:
    """Run project.py with args, return completed process."""
    cmd = [sys.executable, PROJECT_PY] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=cwd,
        timeout=30,
    )


@pytest.fixture
def project_env(tausik_env):
    """Initialized project with epic/story hierarchy ready for tests."""
    cwd, env = tausik_env
    run_cli(["init", "--name", "test"], env, str(cwd))
    run_cli(["epic", "add", "e1", "Epic"], env, str(cwd))
    run_cli(["story", "add", "e1", "s1", "Story"], env, str(cwd))
    return cwd, env


class TestInit:
    def test_init(self, tausik_env):
        cwd, env = tausik_env
        r = run_cli(["init", "--name", "test-project"], env, str(cwd))
        assert r.returncode == 0
        assert "initialized" in r.stdout.lower()

    def test_init_idempotent(self, tausik_env):
        cwd, env = tausik_env
        run_cli(["init", "--name", "test-project"], env, str(cwd))
        r = run_cli(["init", "--name", "test-project"], env, str(cwd))
        assert r.returncode == 0
        assert "already exists" in r.stdout.lower()


class TestEpicCLI:
    def test_epic_lifecycle(self, tausik_env):
        cwd, env = tausik_env
        run_cli(["init", "--name", "test"], env, str(cwd))

        r = run_cli(["epic", "add", "v1", "Version 1"], env, str(cwd))
        assert r.returncode == 0
        assert "created" in r.stdout.lower()

        r = run_cli(["epic", "list"], env, str(cwd))
        assert r.returncode == 0
        assert "v1" in r.stdout

        r = run_cli(["epic", "done", "v1"], env, str(cwd))
        assert r.returncode == 0

        r = run_cli(["epic", "delete", "v1"], env, str(cwd))
        assert r.returncode == 0


class TestTaskCLI:
    def _setup(self, env, cwd):
        run_cli(["init", "--name", "test"], env, cwd)
        run_cli(["epic", "add", "v1", "V1"], env, cwd)
        run_cli(["story", "add", "v1", "s1", "Story 1"], env, cwd)

    def test_full_lifecycle(self, tausik_env):
        cwd, env = tausik_env
        self._setup(env, str(cwd))

        # Add task with goal + AC (QG-0 requires both)
        r = run_cli(
            [
                "task",
                "add",
                "Create README",
                "--group",
                "s1",
                "--slug",
                "create-readme",
                "--goal",
                "Write README file",
            ],
            env,
            str(cwd),
        )
        assert r.returncode == 0
        r = run_cli(
            [
                "task",
                "update",
                "create-readme",
                "--acceptance-criteria",
                "1. README exists. 2. Error if file already exists.",
            ],
            env,
            str(cwd),
        )
        assert r.returncode == 0

        # Start (QG-0: goal + AC set, should pass)
        r = run_cli(["task", "start", "create-readme"], env, str(cwd))
        assert r.returncode == 0
        assert "started" in r.stdout.lower()

        # Log AC verification + Done
        r = run_cli(
            ["task", "log", "create-readme", "AC verified: 1. README exists"],
            env,
            str(cwd),
        )
        assert r.returncode == 0
        r = run_cli(["task", "done", "create-readme", "--ac-verified"], env, str(cwd))
        assert r.returncode == 0
        assert "completed" in r.stdout.lower()

    def test_task_list(self, tausik_env):
        cwd, env = tausik_env
        self._setup(env, str(cwd))
        run_cli(["task", "add", "T1", "--group", "s1", "--slug", "t1"], env, str(cwd))
        run_cli(["task", "add", "T2", "--group", "s1", "--slug", "t2"], env, str(cwd))

        r = run_cli(["task", "list"], env, str(cwd))
        assert r.returncode == 0
        assert "t1" in r.stdout
        assert "t2" in r.stdout

    def test_task_show(self, tausik_env):
        cwd, env = tausik_env
        self._setup(env, str(cwd))
        run_cli(
            [
                "task",
                "add",
                "My Task",
                "--group",
                "s1",
                "--slug",
                "my-task",
                "--goal",
                "Test it",
            ],
            env,
            str(cwd),
        )

        r = run_cli(["task", "show", "my-task"], env, str(cwd))
        assert r.returncode == 0
        assert "my-task" in r.stdout
        assert "Test it" in r.stdout

    def test_task_block_unblock(self, tausik_env):
        cwd, env = tausik_env
        self._setup(env, str(cwd))
        run_cli(
            ["task", "add", "T1", "--group", "s1", "--slug", "t1", "--goal", "Test"],
            env,
            str(cwd),
        )
        run_cli(
            ["task", "update", "t1", "--acceptance-criteria", "1. Works"], env, str(cwd)
        )
        run_cli(["task", "start", "t1"], env, str(cwd))

        r = run_cli(["task", "block", "t1", "--reason", "Waiting"], env, str(cwd))
        assert r.returncode == 0

        r = run_cli(["task", "unblock", "t1"], env, str(cwd))
        assert r.returncode == 0

    def test_task_plan_steps(self, tausik_env):
        cwd, env = tausik_env
        self._setup(env, str(cwd))
        run_cli(["task", "add", "T1", "--group", "s1", "--slug", "t1"], env, str(cwd))

        r = run_cli(["task", "plan", "t1", "Step A", "Step B"], env, str(cwd))
        assert r.returncode == 0
        assert "2 steps" in r.stdout

        r = run_cli(["task", "step", "t1", "1"], env, str(cwd))
        assert r.returncode == 0
        assert "1/2" in r.stdout


class TestSessionCLI:
    def test_session_lifecycle(self, tausik_env):
        cwd, env = tausik_env
        run_cli(["init", "--name", "test"], env, str(cwd))

        r = run_cli(["session", "start"], env, str(cwd))
        assert r.returncode == 0
        assert "started" in r.stdout.lower()

        r = run_cli(["session", "current"], env, str(cwd))
        assert r.returncode == 0
        assert "session #" in r.stdout.lower()

        r = run_cli(["session", "end", "--summary", "All done"], env, str(cwd))
        assert r.returncode == 0
        assert "ended" in r.stdout.lower()

        r = run_cli(["session", "list"], env, str(cwd))
        assert r.returncode == 0


class TestMemoryCLI:
    def test_memory_lifecycle(self, tausik_env):
        cwd, env = tausik_env
        run_cli(["init", "--name", "test"], env, str(cwd))

        r = run_cli(
            ["memory", "add", "pattern", "Singleton", "Use singleton pattern"],
            env,
            str(cwd),
        )
        assert r.returncode == 0
        assert "saved" in r.stdout.lower()

        r = run_cli(["memory", "list"], env, str(cwd))
        assert r.returncode == 0
        assert "Singleton" in r.stdout

        r = run_cli(["memory", "search", "singleton"], env, str(cwd))
        assert r.returncode == 0

    def test_memory_list_empty(self, project_env):
        cwd, env = project_env
        r = run_cli(["memory", "list"], env, str(cwd))
        assert r.returncode == 0
        assert "no memories" in r.stdout.lower()

    def test_memory_show_delete(self, project_env):
        cwd, env = project_env
        run_cli(["memory", "add", "pattern", "ToDelete", "Content"], env, str(cwd))
        r = run_cli(["memory", "show", "1"], env, str(cwd))
        assert r.returncode == 0
        r = run_cli(["memory", "delete", "1"], env, str(cwd))
        assert r.returncode == 0


class TestSearchCLI:
    def test_search(self, tausik_env):
        cwd, env = tausik_env
        run_cli(["init", "--name", "test"], env, str(cwd))
        run_cli(["epic", "add", "v1", "V1"], env, str(cwd))
        run_cli(["story", "add", "v1", "s1", "S1"], env, str(cwd))
        run_cli(
            [
                "task",
                "add",
                "Fix authentication bug",
                "--group",
                "s1",
                "--slug",
                "fix-auth",
            ],
            env,
            str(cwd),
        )

        r = run_cli(["search", "authentication"], env, str(cwd))
        assert r.returncode == 0
        assert "fix-auth" in r.stdout


class TestStatusCLI:
    def test_status(self, tausik_env):
        cwd, env = tausik_env
        run_cli(["init", "--name", "test"], env, str(cwd))

        r = run_cli(["status"], env, str(cwd))
        assert r.returncode == 0
        assert "tasks:" in r.stdout.lower()


class TestDecisionsCLI:
    def test_decide_and_list(self, tausik_env):
        cwd, env = tausik_env
        run_cli(["init", "--name", "test"], env, str(cwd))

        r = run_cli(["decide", "Use SQLite", "--rationale", "Simple"], env, str(cwd))
        assert r.returncode == 0
        assert "recorded" in r.stdout.lower()

        r = run_cli(["decisions"], env, str(cwd))
        assert r.returncode == 0
        assert "SQLite" in r.stdout


class TestTeam:
    def test_team(self, project_env):
        cwd, env = project_env
        r = run_cli(["team"], env, str(cwd))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert (
            "active" in out
            or "no active" in out
            or "no claimed" in out
            or "tasks" in out
        )


class TestRoadmap:
    def test_roadmap(self, project_env):
        cwd, env = project_env
        r = run_cli(["roadmap"], env, str(cwd))
        assert r.returncode == 0
        assert (
            "e1" in r.stdout.lower()
            or "epic" in r.stdout.lower()
            or "no epic" in r.stdout.lower()
        )

    def test_roadmap_include_done(self, project_env):
        cwd, env = project_env
        r = run_cli(["roadmap", "--include-done"], env, str(cwd))
        assert r.returncode == 0


class TestMetrics:
    def test_metrics(self, project_env):
        cwd, env = project_env
        r = run_cli(["metrics"], env, str(cwd))
        assert r.returncode == 0
        out = r.stdout
        assert (
            "Tasks:" in out
            or "tasks:" in out.lower()
            or "Throughput" in out
            or "FPSR" in out
        )


class TestDeadEnd:
    def test_dead_end(self, project_env):
        cwd, env = project_env
        r = run_cli(["dead-end", "test approach", "test reason"], env, str(cwd))
        assert r.returncode == 0
        assert "documented" in r.stdout.lower() or "dead" in r.stdout.lower()

    def test_dead_end_with_task(self, project_env):
        cwd, env = project_env
        r = run_cli(
            [
                "task",
                "add",
                "T1",
                "--group",
                "s1",
                "--slug",
                "t1",
                "--goal",
                "G",
            ],
            env,
            str(cwd),
        )
        assert r.returncode == 0
        r = run_cli(["dead-end", "approach2", "reason2", "--task", "t1"], env, str(cwd))
        assert r.returncode == 0


class TestExplore:
    def test_explore_start(self, project_env):
        cwd, env = project_env
        r = run_cli(["explore", "start", "test exploration"], env, str(cwd))
        assert r.returncode == 0
        assert "started" in r.stdout.lower() or "exploration" in r.stdout.lower()

    def test_explore_current(self, project_env):
        cwd, env = project_env
        r = run_cli(["explore", "current"], env, str(cwd))
        assert r.returncode == 0

    def test_explore_end_no_active(self, project_env):
        cwd, env = project_env
        r = run_cli(["explore", "end"], env, str(cwd))
        # May return 0 or 1 depending on whether there's an active exploration
        assert r.returncode in (0, 1)

    def test_explore_lifecycle(self, project_env):
        cwd, env = project_env
        r = run_cli(["explore", "start", "lifecycle test"], env, str(cwd))
        assert r.returncode == 0

        r = run_cli(["explore", "current"], env, str(cwd))
        assert r.returncode == 0
        assert "lifecycle" in r.stdout.lower()

        r = run_cli(["explore", "end"], env, str(cwd))
        assert r.returncode == 0


class TestAudit:
    def test_audit_check(self, project_env):
        cwd, env = project_env
        r = run_cli(["audit", "check"], env, str(cwd))
        assert r.returncode == 0
        assert "audit" in r.stdout.lower() or "senar" in r.stdout.lower()


class TestGates:
    def test_gates_status(self, project_env):
        cwd, env = project_env
        r = run_cli(["gates", "status"], env, str(cwd))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "gate" in out or "no gate" in out or "pytest" in out


class TestEventsCLI:
    def test_events_empty(self, project_env):
        cwd, env = project_env
        r = run_cli(["events"], env, str(cwd))
        assert r.returncode == 0


class TestErrorHandling:
    def test_invalid_slug(self, tausik_env):
        cwd, env = tausik_env
        run_cli(["init", "--name", "test"], env, str(cwd))

        r = run_cli(["epic", "add", "Bad Slug!", "Title"], env, str(cwd))
        assert r.returncode == 1
        assert "error" in r.stderr.lower() or "validation" in r.stderr.lower()

    def test_nonexistent_task(self, tausik_env):
        cwd, env = tausik_env
        run_cli(["init", "--name", "test"], env, str(cwd))

        r = run_cli(["task", "start", "nope"], env, str(cwd))
        assert r.returncode == 1

    def test_no_command(self, tausik_env):
        cwd, env = tausik_env
        r = run_cli([], env, str(cwd))
        assert r.returncode == 1
