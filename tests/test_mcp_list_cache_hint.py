"""tools/list must not be cached while it depends on the active task's scope.

mcp-tools-list-caching-conflicts-with-scope-hiding (1.10, github#91). MCP
2026-07-28 (SEP-2549) lets a client cache tools/list for `ttlMs`; scope hiding
(mcp-scope-tools-exposure) changes that list when a task's scope_tools
changes. The server therefore answers with ttlMs=0 and cacheScope=private.
Proven on the wire: a real server over stdio, the scope changed between two
calls in one session — the second list is narrower, and neither is cacheable.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys

import pytest

pytest.importorskip("mcp")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SERVER = os.path.join(_ROOT, "harness", "claude", "mcp", "project", "server.py")
if os.path.join(_ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "scripts"))


@pytest.fixture
def scoped_project(tmp_path):
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    tausik = tmp_path / ".tausik"
    tausik.mkdir()
    (tausik / "config.json").write_text(
        json.dumps({"mcp": {"scope_tools_exposure": True}}), encoding="utf-8"
    )
    be = SQLiteBackend(str(tausik / "tausik.db"))
    svc = ProjectService(be)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "t", "T", role="developer")
    be.close()
    return tmp_path


def _call(proc, req_id, method, params=None):
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        assert line, proc.stderr.read()
        reply = json.loads(line)
        if reply.get("id") == req_id:
            return reply["result"]


def test_a_scope_change_mid_session_is_never_served_from_a_cache(scoped_project, tmp_path):
    from mcp.types import LATEST_PROTOCOL_VERSION

    env = dict(os.environ, TAUSIK_USER_CONFIG=str(tmp_path / "no-user-tier.json"))
    proc = subprocess.Popen(
        [sys.executable, SERVER, "--project", str(scoped_project)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
    )
    try:
        _call(
            proc,
            1,
            "initialize",
            {
                "protocolVersion": LATEST_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        )
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        proc.stdin.write("\n")
        before = _call(proc, 2, "tools/list")

        db = sqlite3.connect(str(scoped_project / ".tausik" / "tausik.db"))
        db.execute(
            "UPDATE tasks SET status='active', scope_tools=? WHERE slug='t'",
            (json.dumps(["tausik_search"]),),
        )
        db.commit()
        db.close()
        after = _call(proc, 3, "tools/list")
    finally:
        proc.stdin.close()
        proc.kill()
        proc.communicate()

    for result in (before, after):
        assert result["ttlMs"] == 0
        assert result["cacheScope"] == "private"
    # The surface really did change inside one session — a cached copy would lie.
    assert len(after["tools"]) < len(before["tools"])
