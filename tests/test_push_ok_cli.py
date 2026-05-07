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
        # Init a real git repo so HEAD SHA is resolvable.
        subprocess.check_call(["git", "init", "-q", "-b", "main"], cwd=project)
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
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SCRIPTS_DIR) + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "project.py"), "push-ok", "--ttl", "10"],
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
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
