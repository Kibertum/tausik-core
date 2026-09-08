"""Is the route the rules prescribe actually the route being taken?

the-route-an-agent-must-take-is-enforced-not-described. The rules call MCP-first
a hard constraint. Measured over this project's own transcripts in session #233,
before anything was built: 1,216 of 1,530 CLI invocations had an MCP twin and
went through the shell anyway — 79.5% — and MCP's share of all framework calls
was 29.1%. Nothing anywhere reported that.

A rule nobody counts is followed when the agent happens to remember, and this is
what "happens to remember" measures to. So the number is printed.

WHAT THIS CHECK REFUSES TO DO is turn a share into a verdict. There is no
threshold here, and deliberately: 20.5% of CLI invocations have no MCP twin,
chaining (`verify && task done`) cannot be expressed on the MCP surface at all,
and a long multi-line argument is genuinely easier through `"$(cat file)"`. A
warning that fired on those would be a warning trained to be ignored, and an
ignored warning costs the attention the next real one needs (convention #291).
It reports; the reader judges.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from typing import Any

_LABEL = "Agent route"

#: Tool names recorded by the PostToolUse telemetry for the framework's own MCP.
_MCP_PREFIX = "mcp__tausik-project__"


def _counts(project_dir: str) -> tuple[int, int]:
    """(mcp calls, shell calls) in the current session, from the events table.

    Read-only and best-effort. A doctor line is not worth a lock on the database
    a session is actively writing.
    """
    db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.isfile(db):
        return 0, 0
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error:
        return 0, 0
    try:
        row = conn.execute(
            "SELECT "
            " SUM(CASE WHEN tool_name LIKE ? THEN 1 ELSE 0 END), "
            " SUM(CASE WHEN tool_name IN ('Bash','PowerShell') THEN 1 ELSE 0 END) "
            "FROM usage_events WHERE session_id = ("
            " SELECT id FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1)",
            (_MCP_PREFIX + "%",),
        ).fetchone()
    except sqlite3.Error:
        return 0, 0
    finally:
        conn.close()
    return int((row or [0, 0])[0] or 0), int((row or [0, 0])[1] or 0)


def check_agent_route(svc: Any) -> Iterator[tuple[str, str, str]]:
    """One line: how the framework was reached this session, MCP versus shell."""
    project_dir = os.getcwd()
    mcp, shell = _counts(project_dir)
    if mcp + shell == 0:
        return  # nothing recorded yet: silence beats a percentage of nothing

    share = 100 * mcp / (mcp + shell)
    yield (
        "ok",
        _LABEL,
        f"this session reached the framework {mcp} time(s) through MCP and made "
        f"{shell} shell call(s) — MCP share {share:.0f}%. Measured baseline before "
        "the nudge existed: 29%. No threshold is applied: chaining and long "
        "file-fed arguments are legitimate shell reasons, and a warning that "
        "fired on them would be one you learn to skip",
    )
