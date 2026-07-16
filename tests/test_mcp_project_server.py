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
# CURSOR_SERVER (harness/cursor/mcp/project/server.py) is gone: it was a byte-copy of the
# canonical claude tree and was deleted in v1.7.0. copy_mcp hands the canonical server to
# every IDE, so the parity tests that used to duplicate each check for the cursor copy are
# now covered by the single canonical checks below — plus tests/test_mcp_single_canonical_tree.py,
# which refuses to let a copy come back.


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


def test_project_server_chdir_is_in_main(tmp_path):
    """White-box check that chdir(--project) is in the launch path.

    Reading the source is faster and more deterministic than booting the
    server and inspecting cwd via JSON-RPC.
    """
    src = open(SERVER, encoding="utf-8").read()
    assert "os.chdir(args.project)" in src, (
        "Project MCP server must chdir to --project for parity with brain server"
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


def test_project_server_minimal_text_reply_on_exception():
    """Agent-facing text reply must NOT include the traceback (no frame-locals leak).

    This assertion used to pin an exact source string — `TextContent(type="text",
    text=f"Error: {e}")` — and went red the moment the reply grew a usage hint. It had
    been failing in main since before v1.7.0 and nobody saw it: the module is
    `pytest.mark.slow`, and `addopts = "-m 'not slow'"` deselects that lane by default.

    Assert the INTENT instead of the spelling: the reply is built from the exception
    message, and the traceback goes to stderr only.
    """
    src = open(SERVER, encoding="utf-8").read()
    assert 'reply = f"Error: {e}"' in src, (
        "agent reply must be built from the exception message, not the traceback"
    )
    # traceback.format_exc() may appear ONLY on the stderr path, never in a TextContent.
    for line in src.splitlines():
        if "format_exc()" in line:
            continue  # its own line: the print(...) call is checked below
        assert not ("TextContent" in line and "format_exc" in line), (
            "traceback must never reach the agent-facing TextContent reply"
        )
    assert "file=sys.stderr" in src
