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


def _extract_files_from_cache_command(command: str) -> list[str]:
    """Parse files list from a `_build_cache_command` value.

    Format: `trigger=...|sig=...|files=foo.py,bar.py`. Returns [] if absent
    or empty (e.g. `files=` with no payload).
    """
    if not command or "|files=" not in command:
        return []
    files_part = command.split("|files=", 1)[1]
    if not files_part:
        return []
    return [f for f in files_part.split(",") if f]


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


def lookup_any_fresh_run_for_task(
    conn: sqlite3.Connection,
    task_slug: str,
    *,
    max_age_s: int = _DEFAULT_VERIFY_CACHE_TTL_S,
) -> dict[str, Any] | None:
    """Latest fresh green row for `task_slug` regardless of files_hash/command.

    The strict cache lookup (`lookup_recent_for_task`) requires an exact match
    on `(slug, files_hash, command)` — which misses Sharp edge #2: verify run
    recorded with files=[] (manual scope, no CLI args), task_done arriving with
    explicit relevant_files. This relaxed variant returns *any* fresh exit-zero
    row for the slug; callers MUST gate on `is_security_sensitive(files)` so
    auth/payment paths never accept a session-level pass without an exact
    file-hash match.
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
        ORDER BY id DESC
        LIMIT 1
        """,
        (task_slug,),
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


def lookup_relevant_files_from_recent_verify(
    conn: sqlite3.Connection,
    task_slug: str,
    *,
    max_age_s: int = _DEFAULT_VERIFY_CACHE_TTL_S,
) -> list[str] | None:
    """Recover relevant_files from the most recent fresh green verify-row.

    Used by `task_done` as a fallback when neither the caller nor the task
    row supplied `relevant_files` — so that a fresh `tausik verify --task X`
    can satisfy a follow-up `task done X` without an exact CLI match.

    Returns the parsed file list (possibly empty) when a fresh exit-zero row
    exists for `task_slug`; `None` when no row, the row is stale, or the row
    has no `|files=` payload (manual scope etc.).
    """
    if not task_slug:
        return None
    row = conn.execute(
        """
        SELECT command, ran_at
        FROM verification_runs
        WHERE task_slug = ?
          AND exit_code = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (task_slug,),
    ).fetchone()
    if row is None:
        return None
    record = dict(row) if not isinstance(row, dict) else row
    try:
        ran_at = datetime.fromisoformat(record["ran_at"].replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    age = (datetime.now(timezone.utc) - ran_at).total_seconds()
    if age > max_age_s:
        return None
    files = _extract_files_from_cache_command(record.get("command") or "")
    return files if files else None
