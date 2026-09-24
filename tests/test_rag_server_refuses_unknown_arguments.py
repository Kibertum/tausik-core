"""The codebase-rag server refuses an argument its tool never declared.

sibling-mcp-servers-still-drop-unknown-arguments: the project server has refused
undeclared arguments since mcp-server-drops-unknown-arguments-silently, while
the rag server passed them through — `search_code(qurey=...)` looked like a
call that simply found nothing. Driven here over real stdio JSON-RPC against
the real server process, because the guard sits in the server's `call_tool`
closure and nothing short of a call reaches it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SERVER = os.path.join(_ROOT, "harness", "claude", "mcp", "codebase-rag", "rag_server.py")
# Drives the server as a subprocess, so no import edge selects this test.
CROSSCUTTING_SCOPE = ["harness/claude/mcp/codebase-rag/", "scripts/mcp_arguments.py"]

pytest.importorskip("mcp")


def _call(tmp_path, arguments: dict) -> str:
    """initialize -> initialized -> tools/call search_code; return the reply text."""
    msgs = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "search_code", "arguments": arguments},
        },
    ]
    # stdin stays open until the reply is read: at EOF the server shuts down,
    # and a handler still running in its worker thread never answers.
    proc = subprocess.Popen(
        [sys.executable, _SERVER, "--project", str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        assert proc.stdin is not None and proc.stdout is not None
        proc.stdin.write("".join(json.dumps(m) + "\n" for m in msgs))
        proc.stdin.flush()
        for line in proc.stdout:
            reply = json.loads(line)
            if reply.get("id") == 2:
                return reply["result"]["content"][0]["text"]
    finally:
        proc.kill()
        proc.wait(timeout=30)
    raise AssertionError("the server closed stdout without answering tools/call")


def test_an_undeclared_argument_is_refused_by_name(tmp_path):
    # `query` is present: the SDK already refuses a missing REQUIRED property, but
    # the schemas do not forbid extra keys, so an extra one reached the handler.
    text = _call(tmp_path, {"query": "anything", "qurey": "anything"})
    assert text.startswith("Error: search_code does not declare 'qurey'")
    assert "did you mean 'query'?" in text
    assert "usage: search_code(" in text


def test_a_declared_call_still_reaches_the_handler(tmp_path):
    text = _call(tmp_path, {"query": "anything", "limit": 1})
    assert "does not declare" not in text
