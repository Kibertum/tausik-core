#!/usr/bin/env python3
"""PostToolUse hook: increment per-task tool-call counter.

Records actual agent tool-use into TAUSIK's meta table so that on
task_done the recorded budget can be compared with the observed
call count (SENAR agent-native sizing).

Behaviour (HIGH-4 review fix):
  * Increments meta['tool_calls:<slug>'] for EVERY active task. Multi-agent
    setups may have several active tasks at once; previously the hook
    became a no-op when >1 active task was found, silently dropping
    measurements. Now we count toward each.
  * Increment runs under BEGIN IMMEDIATE so concurrent task_done
    transactions serialise (HIGH-3 review fix). Best-effort property:
    a tool call that fires DURING a task_done commit may be lost
    (single increment), but counters cannot be left partially updated.
  * On any error (DB locked, missing project, etc.) exits 0 silently —
    counting is best-effort and must never block a tool call.

Restricted to Write/Edit/MultiEdit/Bash matchers in bootstrap config so
that read-only tools (Read/Grep/Glob) don't pollute the calibration
drift metric (HIGH-5 review fix).

Skipped via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys


def _db_path(project_dir: str) -> str | None:
    path = os.path.join(project_dir, ".tausik", "tausik.db")
    return path if os.path.exists(path) else None


def _active_slugs(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute("SELECT slug FROM tasks WHERE status='active'")
    return [row[0] for row in cur.fetchall()]


def _increment_all(conn: sqlite3.Connection, slugs: list[str]) -> None:
    if not slugs:
        return
    # BEGIN IMMEDIATE acquires the reserved lock up-front so that
    # concurrent task_done transactions serialise; SQLite's busy timeout
    # (set on connect) makes us wait rather than fail outright.
    conn.execute("BEGIN IMMEDIATE")
    try:
        for slug in slugs:
            conn.execute(
                "INSERT INTO meta(key,value) VALUES(?, '1') "
                "ON CONFLICT(key) DO UPDATE SET value = CAST(value AS INTEGER) + 1",
                (f"tool_calls:{slug}",),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


#: The rule says every 30-50 tool calls. The reminder fires at the FAR end: at
#: 30 it would speak five times in a session where the agent was already
#: checkpointing, and a reminder that arrives when the work is already done is
#: one the reader learns to skip.
_CHECKPOINT_EVERY = 50


def _checkpoint_due(conn, slug: str) -> int | None:
    """Calls so far for `slug` if this call crosses a multiple of the interval.

    Read AFTER the increment, so the number in the message is the number the
    reader would get from `task show` — a reminder quoting a different count
    than the record teaches the reader to distrust both.
    """
    try:
        row = conn.execute(
            "SELECT CAST(value AS INTEGER) FROM meta WHERE key = ?", (f"tool_calls:{slug}",)
        ).fetchone()
    except Exception:  # noqa: BLE001 — a reminder is never worth a failure
        return None
    if not row or not row[0]:
        return None
    count = int(row[0])
    return count if count % _CHECKPOINT_EVERY == 0 else None


def main() -> int:
    # The checkpoint reminder carries non-ASCII. Written through an interpreter
    # not started in UTF-8 mode it leaves in the machine's locale encoding, and a
    # reminder that arrives as mojibake is one nobody acts on.
    try:
        from _common import force_utf8_io

        force_utf8_io()
    except Exception:  # noqa: BLE001 - the guard is a courtesy, not a dependency
        pass

    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0
    try:
        json.load(sys.stdin)  # consume payload; we don't inspect it
    except (json.JSONDecodeError, EOFError, ValueError):
        pass

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    db = _db_path(project_dir)
    if not db:
        return 0

    try:
        conn = sqlite3.connect(db, timeout=5, isolation_level=None)
        try:
            slugs = _active_slugs(conn)
            _increment_all(conn, slugs)
            for slug in slugs:
                due = _checkpoint_due(conn, slug)
                if due is None:
                    continue
                print(
                    f"[TAUSIK checkpoint] {due} tool calls on '{slug}'. SENAR Rule 9.3 "
                    "asks for a checkpoint every 30-50: write down where the work "
                    "stands before the context that holds it is summarised away — "
                    f'`.tausik/tausik task log {slug} "<where this stands>"`, or '
                    "`/checkpoint`.",
                    file=sys.stderr,
                )
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001 — best-effort hook
        print(f"task_call_counter: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
