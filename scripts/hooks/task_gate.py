#!/usr/bin/env python3
"""PreToolUse hook: block Write/Edit if no active task in TAUSIK.

v1.4: direct SQLite SELECT replaces the previous subprocess + 5s timeout
shape. Two reasons:

  1. **Speed.** A subprocess CLI call costs 100-300 ms per Write/Edit on
     Windows; pure SQLite query is sub-millisecond. Editor-heavy sessions
     used to feel sluggish.
  2. **Reliability.** A subprocess that fails (PowerShell quirk, locked
     venv, transient OSError) used to silently let edits through —
     fail-open. The new path keeps that fail-open as DEFAULT (so `tausik
     doctor` issues never brick a project) but adds an explicit
     `TAUSIK_HOOK_FAIL_SECURE=1` opt-in: under that flag, any DB error
     blocks the write instead of allowing it. Recommended for shared/CI
     contexts where silent bypass is unacceptable.

Exit codes: 0 = allow, 2 = block.
Receives JSON on stdin with tool_name, tool_input.
Skipped via TAUSIK_SKIP_HOOKS=1 env var.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import is_tausik_project  # noqa: E402


def _has_active_task(db_path: str) -> bool:
    """Direct SQLite SELECT — no subprocess.

    Returns True iff at least one row in `tasks` has status='active'.
    Raises sqlite3.Error on failure so the caller can apply the
    fail-secure policy.
    """
    conn = sqlite3.connect(db_path, timeout=2.0)
    try:
        row = conn.execute(
            "SELECT 1 FROM tasks WHERE status = 'active' LIMIT 1"
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    if not is_tausik_project(project_dir):
        return 0

    db_path = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(db_path):
        # Bootstrap-but-not-init: nothing to enforce yet.
        return 0

    fail_secure = bool(os.environ.get("TAUSIK_HOOK_FAIL_SECURE"))

    try:
        active = _has_active_task(db_path)
    except sqlite3.Error as e:
        if fail_secure:
            print(
                f"BLOCKED: TAUSIK_HOOK_FAIL_SECURE=1 set, but task gate could "
                f"not query .tausik/tausik.db: {e}. Fix the DB or unset the "
                "flag to allow edits.",
                file=sys.stderr,
            )
            return 2
        # Default: fail-open so a transient DB issue never bricks editing.
        return 0
    except Exception as e:  # defensive — never bring down the host.  # noqa: BLE001 — best-effort: a hook must never break the tool call it guards
        if fail_secure:
            print(
                f"BLOCKED: TAUSIK_HOOK_FAIL_SECURE=1 set, task gate crashed: {e}",
                file=sys.stderr,
            )
            return 2
        return 0

    if active:
        return 0

    print(
        "BLOCKED: No active task. Start a task first:\n"
        "  Say 'начинай работу' then describe your task, or use /go.\n"
        "  TAUSIK requires a task before code changes (SENAR Rule 1).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
