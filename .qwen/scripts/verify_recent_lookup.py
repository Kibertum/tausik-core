"""Latest matching row in verification_runs (cache lookup).

Separate module for filesize compliance of service_verification.py.
Default TTL mirrors service_verification.DEFAULT_CACHE_TTL_S (600).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

# Keep in sync with service_verification.DEFAULT_CACHE_TTL_S.
_DEFAULT_VERIFY_CACHE_TTL_S = 600


def lookup_recent_for_task(
    conn: sqlite3.Connection,
    task_slug: str,
    *,
    files_hash: str,
    command: str,
    max_age_s: int = _DEFAULT_VERIFY_CACHE_TTL_S,
) -> dict[str, Any] | None:
    """Fresh green row for (slug, hash, command), most recent id; else None.

    Rows differ by `command` (e.g. trigger=verify vs task-done); we must not
    take ORDER BY id only for the slug — a newer task-done row would shadow verify.
    """
    if not task_slug:
        return None
    row = conn.execute(
        """
        SELECT id, task_slug, scope, command, exit_code, summary,
               files_hash, ran_at, duration_ms
        FROM verification_runs
        WHERE task_slug = ?
          AND exit_code = 0
          AND files_hash = ?
          AND command = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (task_slug, files_hash, command),
    ).fetchone()
    if row is None:
        return None
    run = dict(row) if not isinstance(row, dict) else row
    try:
        ran_at = datetime.fromisoformat(run["ran_at"].replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    age = (datetime.now(timezone.utc) - ran_at).total_seconds()
    if age > max_age_s:
        return None
    return run
