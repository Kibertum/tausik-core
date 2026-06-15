#!/usr/bin/env python3
"""PostToolUse hook: write an activity event for every tool call.

Without this, `backend_session_metrics.compute_active_minutes` undercounts
because only a handful of code paths (verify, session_extend, task_done)
write to the `events` table. The 180-min SENAR Rule 9.2 active-time gate
would never trip on a session of pure Edit/Bash/Read work.

Single row per tool call (`entity_type='session'`, `action='tool_use'`).
No active task required — activity is per-session. Best-effort: silent on
any error so a tool call is never blocked.

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


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        pass

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    db = _db_path(project_dir)
    if not db:
        return 0

    try:
        conn = sqlite3.connect(db, timeout=2)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                "INSERT INTO events(entity_type, entity_id, action) "
                "VALUES ('session', 'agent', 'tool_use')"
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — best-effort hook
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
