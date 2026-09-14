"""Tests for `tausik push-ok` CLI handler (scripts/cli_push_ok.py).

Covers the ticket writer + cmd_push_ok argparse handler. The pair with
git_push_gate hook tests in tests/test_hooks.py::TestGitPushGate exercises
the consumer side; this file pins the producer side.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from cli_push_ok import (  # noqa: E402
    DEFAULT_TTL_SECONDS,
    SCHEMA_VERSION,
    TICKET_FILENAME,
    cmd_push_ok,
    write_push_ticket,
)


def _make_args(ttl: int | None = None):
    class A:
        pass

    a = A()
    if ttl is not None:
        a.ttl = ttl
    return a


class TestWritePushTicket:
    def test_writes_with_explicit_sha_and_branch(self, tmp_path):
        path = write_push_ticket(
            tmp_path,
            ttl_seconds=30,
            commit_sha="a" * 40,
            branch="feature/x",
        )
        assert path == tmp_path / TICKET_FILENAME
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == SCHEMA_VERSION
        assert data["commit_sha"] == "a" * 40
        assert data["branch"] == "feature/x"
        created = datetime.fromisoformat(data["created_at"])
        expires = datetime.fromisoformat(data["expires_at"])
        assert (expires - created) == timedelta(seconds=30)

    def test_default_ttl_60_seconds(self, tmp_path):
        path = write_push_ticket(tmp_path, commit_sha="b" * 40, branch="main")
        data = json.loads(path.read_text(encoding="utf-8"))
        created = datetime.fromisoformat(data["created_at"])
        expires = datetime.fromisoformat(data["expires_at"])
        assert (expires - created) == timedelta(seconds=DEFAULT_TTL_SECONDS)

    def test_atomic_replace_no_temp_leftover(self, tmp_path):
        write_push_ticket(tmp_path, commit_sha="c" * 40, branch="main")
        # Temp file from atomic write must not linger.
        leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
        assert leftovers == []

    def test_overwrites_existing_ticket(self, tmp_path):
        write_push_ticket(tmp_path, commit_sha="d" * 40, branch="main")
        write_push_ticket(tmp_path, commit_sha="e" * 40, branch="other")
        data = json.loads((tmp_path / TICKET_FILENAME).read_text(encoding="utf-8"))
        assert data["commit_sha"] == "e" * 40
        assert data["branch"] == "other"

    def test_creates_parent_directory(self, tmp_path):
        nested = tmp_path / "deep" / "tausik"
        write_push_ticket(nested, commit_sha="f" * 40, branch="main")
        assert (nested / TICKET_FILENAME).exists()

    def test_detached_head_branch_normalized_to_empty(self, tmp_path):
        path = write_push_ticket(tmp_path, commit_sha="0" * 40, branch="HEAD")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["branch"] == ""

    def test_expires_at_parseable_back(self, tmp_path):
        write_push_ticket(tmp_path, commit_sha="9" * 40, branch="main", ttl_seconds=10)
        data = json.loads((tmp_path / TICKET_FILENAME).read_text(encoding="utf-8"))
        # Round-trip: every field written stays parseable.
        datetime.fromisoformat(data["created_at"])
        datetime.fromisoformat(data["expires_at"])


class TestCmdPushOkValidation:
    def test_negative_ttl_exits_1(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            cmd_push_ok(None, _make_args(ttl=-5))
        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "ttl" in err.lower()

    def test_zero_ttl_exits_1(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            cmd_push_ok(None, _make_args(ttl=0))
        assert excinfo.value.code == 1


def _hermetic_env(tmp_path) -> dict:
    """The environment every git in this module runs under.

    NO inherited `GIT_*`, a private HOME, and an empty global AND system config.
    The subprocess under test used to inherit the whole environment, and so did
    the fixture that builds the repository for it — so a `GIT_DIR` from a shell,
    a CI job or a neighbouring test could point either of them at another
    repository. That reproduces the single observed failure exactly, and closing
    it by construction is what the task asks for instead of a retry.
    """
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    empty_config = home / ".gitconfig-empty"
    empty_config.write_text("", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["GIT_CONFIG_GLOBAL"] = str(empty_config)
    env["GIT_CONFIG_SYSTEM"] = str(empty_config)
    return env


class TestCmdPushOkE2E:
    """E2E via subprocess against the real wrapper. Validates dispatch wiring
    + argparse + ticket file written into the discovered .tausik/ dir."""

    def test_push_ok_writes_ticket_via_wrapper(self, tmp_path, monkeypatch):
        # Create a fake project root with .tausik/ + the script under test
        # invoked with explicit cwd. We use the canonical scripts dir (same
        # entry point as `.claude/scripts/project.py`).
        project = tmp_path / "proj"
        project.mkdir()
        tausik_dir = project / ".tausik"
        tausik_dir.mkdir()
        env = _hermetic_env(tmp_path)
        # Init a real git repo so HEAD SHA is resolvable. WITH THE SANITISED
        # ENVIRONMENT: these two calls used to inherit the parent's, so a stray
        # `GIT_DIR` created the repository somewhere else entirely and the
        # subprocess below then found no HEAD — the observed failure, exactly.
        subprocess.check_call(["git", "init", "-q", "-b", "main"], cwd=project, env=env)
        subprocess.check_call(
            [
                "git",
                "-c",
                "user.email=t@t",
                "-c",
                "user.name=t",
                "commit",
                "--allow-empty",
                "-q",
                "-m",
                "init",
            ],
            cwd=project,
            env=env,
        )
        env["PYTHONPATH"] = str(SCRIPTS_DIR) + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "project.py"), "push-ok", "--ttl", "10"],
            cwd=project,
            env=env,
            capture_output=True,
            text=True, encoding="utf-8",
            timeout=15,
        )
        assert result.returncode == 0, result.stderr
        ticket_path = tausik_dir / TICKET_FILENAME
        assert ticket_path.exists()
        data = json.loads(ticket_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == SCHEMA_VERSION
        assert data["branch"] == "main"
        # SHA from the just-created empty commit is 40 hex chars.
        assert len(data["commit_sha"]) == 40
        created = datetime.fromisoformat(data["created_at"])
        expires = datetime.fromisoformat(data["expires_at"])
        assert (expires - created) == timedelta(seconds=10)


class TestTheE2EIsHermetic:
    """AC3. Proven by making the environment hostile, not by reading the code.

    The subprocess used to inherit the whole environment. A `GIT_DIR` in the
    parent — from a shell, a CI job, a neighbouring test — points git at another
    repository, and the e2e test would then ask for HEAD in a place that has
    none. That produces exactly the observed message, only in a full run, only
    sometimes, and never in isolation.
    """

    def test_a_hostile_GIT_DIR_in_the_parent_does_not_reach_the_subprocess(
        self, tmp_path, monkeypatch
    ):
        elsewhere = tmp_path / "not-a-repo"
        elsewhere.mkdir()
        monkeypatch.setenv("GIT_DIR", str(elsewhere))
        monkeypatch.setenv("GIT_WORK_TREE", str(elsewhere))
        # The very test above, run with the environment poisoned. If it inherits
        # GIT_DIR it asks for HEAD in an empty directory and fails the way the
        # single observed failure did.
        TestCmdPushOkE2E().test_push_ok_writes_ticket_via_wrapper(tmp_path, monkeypatch)


class TestTheRefusalNamesWhatHappened:
    """Four outcomes, four messages.

    The one observed failure of the e2e test above printed "no git repo or no
    commits yet". That sentence was reachable from four different events —
    missing repository, no commits, git exiting non-zero for its own reason, and
    git not answering in time — so the message asserted a state of the world
    nobody had checked, and the failure could not be diagnosed from the log at
    all. The timeout hypothesis it invited had to be measured and refuted
    separately (session #232: 60 calls under full-suite load, median 37 ms, max
    232 ms against a 3 s ceiling, none over).
    """

    def test_a_timeout_says_timeout_and_not_missing_repository(self, monkeypatch):
        """AC5. The message that sent a reader looking for a broken repo when
        the repo was fine."""
        import subprocess as sp

        import cli_push_ok

        def _boom(args, **kwargs):
            raise sp.TimeoutExpired(cmd=["git", *args], timeout=3)

        monkeypatch.setattr(cli_push_ok.git_exec, "run", _boom)
        value, why = cli_push_ok._git_detail(["rev-parse", "HEAD"])
        assert value is None
        assert "TIMEOUT" in why
        assert "repository may be perfectly fine" in why
        assert "no git repo" not in why

    def test_git_s_own_words_reach_the_reader(self, monkeypatch):
        """AC2. Discarding git's stderr and substituting our guess is what made
        the single observation undiagnosable."""
        import cli_push_ok

        class _Result:
            returncode = 128
            stdout = ""
            stderr = "fatal: detected dubious ownership in repository at '/x'\n"

        monkeypatch.setattr(cli_push_ok.git_exec, "run", lambda args, **kw: _Result())
        value, why = cli_push_ok._git_detail(["rev-parse", "HEAD"])
        assert value is None
        assert "dubious ownership" in why
        assert "exited 128" in why

    def test_an_unrunnable_git_says_so(self, monkeypatch):
        import cli_push_ok

        def _boom(args, **kwargs):
            raise OSError("No such file or directory: 'git'")

        monkeypatch.setattr(cli_push_ok.git_exec, "run", _boom)
        value, why = cli_push_ok._git_detail(["rev-parse", "HEAD"])
        assert value is None and "could not be executed" in why

    def test_success_carries_no_reason(self, monkeypatch):
        import cli_push_ok

        class _Result:
            returncode = 0
            stdout = "  deadbeef\n"
            stderr = ""

        monkeypatch.setattr(cli_push_ok.git_exec, "run", lambda args, **kw: _Result())
        assert cli_push_ok._git_detail(["rev-parse", "HEAD"]) == ("deadbeef", "")

    def test_git_is_asked_exactly_once(self, monkeypatch):
        """AC4, the task's own prohibition. A retry would hide the cause and
        turn the test into a sensor that measures nothing."""
        import subprocess as sp

        import cli_push_ok

        calls = []

        def _count(args, **kwargs):
            calls.append(args)
            raise sp.TimeoutExpired(cmd=["git", *args], timeout=3)

        monkeypatch.setattr(cli_push_ok.git_exec, "run", _count)
        cli_push_ok._git_detail(["rev-parse", "HEAD"])
        assert len(calls) == 1, f"git was called {len(calls)} times — that is a retry"

    def test_the_ceiling_was_not_quietly_raised(self):
        """AC7. The measurement said thirteenfold headroom; raising it would be a
        change made on a guess, and the next reader deserves to see that it was
        considered and refused."""
        import cli_push_ok

        assert cli_push_ok._GIT_TIMEOUT_SECONDS == 3
