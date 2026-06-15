"""Behavior tests for tausik-project MCP server entrypoint.

Covers:
- chdir to --project on launch (parity with tausik-brain server)
- explicit error and exit code 2 when --project is not a directory
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

# v14b-pytest-fast-lane: spawns the tausik-project MCP server.
pytestmark = pytest.mark.slow

SERVER = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "harness",
        "claude",
        "mcp",
        "project",
        "server.py",
    )
)
CURSOR_SERVER = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "harness",
        "cursor",
        "mcp",
        "project",
        "server.py",
    )
)


def _run(server_path: str, project_arg: str, timeout: float = 5.0):
    """Spawn server with --project and EOF stdin so it exits without blocking."""
    return subprocess.run(
        [sys.executable, server_path, "--project", project_arg],
        input="",
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_project_server_rejects_missing_dir(tmp_path):
    """Negative scenario from QG-0: --project must be an existing directory."""
    bogus = str(tmp_path / "does-not-exist")
    res = _run(SERVER, bogus)
    assert res.returncode == 2, (
        f"expected exit 2 for missing --project, got {res.returncode}\n"
        f"stdout: {res.stdout!r}\nstderr: {res.stderr!r}"
    )
    assert "is not a directory" in res.stderr.lower() or "not a directory" in (
        res.stderr.lower()
    ), f"expected explicit stderr message, got: {res.stderr!r}"


@pytest.mark.skipif(not os.path.exists(CURSOR_SERVER), reason="cursor server.py not present")
def test_cursor_project_server_rejects_missing_dir(tmp_path):
    """Same negative scenario for the cursor MCP server (parity)."""
    bogus = str(tmp_path / "does-not-exist-2")
    res = _run(CURSOR_SERVER, bogus)
    assert res.returncode == 2
    assert "not a directory" in res.stderr.lower()


def test_project_server_chdir_is_in_main(tmp_path):
    """White-box check that chdir(--project) is in the launch path.

    Reading the source is faster and more deterministic than booting the
    server and inspecting cwd via JSON-RPC.
    """
    src = open(SERVER, encoding="utf-8").read()
    assert "os.chdir(args.project)" in src, (
        "Project MCP server must chdir to --project for parity with brain server"
    )


def test_cursor_project_server_chdir_is_in_main():
    """Same as above for the cursor copy — bootstrap copies this file."""
    src = open(CURSOR_SERVER, encoding="utf-8").read()
    assert "os.chdir(args.project)" in src, (
        "Cursor project MCP server must chdir to --project (kept in sync with claude)"
    )


def test_project_server_logs_traceback_on_exception():
    """Project server must log full traceback to stderr (parity with brain).

    White-box: source contains traceback.format_exc() inside call_tool except
    block. We assert the marker is present in the file alongside the import.
    """
    src = open(SERVER, encoding="utf-8").read()
    assert "import traceback" in src
    assert "traceback.format_exc()" in src, (
        "Project MCP server must print traceback on call_tool exceptions"
    )
    assert "print(" in src and "file=sys.stderr" in src


def test_cursor_project_server_logs_traceback_on_exception():
    """Same parity check for the cursor MCP server copy."""
    src = open(CURSOR_SERVER, encoding="utf-8").read()
    assert "import traceback" in src
    assert "traceback.format_exc()" in src
    assert "file=sys.stderr" in src


def test_project_server_minimal_text_reply_on_exception():
    """Agent-facing text reply must NOT include traceback (no secret leak)."""
    src = open(SERVER, encoding="utf-8").read()
    # The TextContent path stays minimal: f"Error: {e}". If someone later
    # changes it to include format_exc() we want a regression alert.
    assert 'TextContent(type="text", text=f"Error: {e}")' in src, (
        "Agent reply must stay minimal to avoid leaking stack frames into model context"
    )
