"""Latest matching row in verification_runs (cache lookup).

Separate module for filesize compliance of service_verification.py.
Default TTL comes from the single source verify_constants.DEFAULT_CACHE_TTL_S.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from verify_constants import DEFAULT_CACHE_TTL_S as _DEFAULT_VERIFY_CACHE_TTL_S
from verify_run_descriptor import REPLAYABLE, VerificationRunDescriptor, descriptor_from_row


def _extract_files_from_cache_command(command: str) -> list[str]:
    """Parse files from legacy command text for audit display only.

    Format: `trigger=...|sig=...|files=foo.py,bar.py`. Returns [] if absent
    or empty (e.g. `files=` with no payload).
    """
    if not command or "|files=" not in command:
        return []
    files_part = command.split("|files=", 1)[1]
    if not files_part:
        return []
    return [f for f in files_part.split(",") if f]


def extract_gate_signature(command: str | None) -> str | None:
    """Parse a legacy gate signature for audit display only.

    Format: `trigger=...|sig=<16hex>|files=...`. Returns None when absent.

    Lives beside `_extract_files_from_cache_command` because they read the two
    halves of ONE string. The first cut put this in `verify_handle_check` and had
    `verify_run_record` import it from there — a write path reaching into a
    policy module for a parser, which is the wrong direction and would have left
    the command format described in two places the moment either changed.
    """
    if not command or "|sig=" not in command:
        return None
    tail = command.split("|sig=", 1)[1]
    return tail.split("|", 1)[0] or None


def lookup_recent_for_task(
    conn: sqlite3.Connection,
    task_slug: str,
    *,
    files_hash: str,
    descriptor: VerificationRunDescriptor,
    max_age_s: int = _DEFAULT_VERIFY_CACHE_TTL_S,
) -> dict[str, Any] | None:
    """Fresh replayable row for the exact structured identity; else None.

    Rows differ by structured trigger; we must not take ORDER BY id only for
    the slug — a newer task-done row would shadow verify.
    """
    if not task_slug:
        return None
    row = conn.execute(
        """
        SELECT id, task_slug, scope, command, exit_code, summary,
               files_hash, ran_at, duration_ms, no_tests_declared,
               run_trigger, run_files_json, gate_signature, replay_policy,
               presentation_policy
        FROM verification_runs
        WHERE task_slug = ?
          AND exit_code = 0
          AND files_hash = ?
          AND run_trigger = ?
          AND run_files_json = ?
          AND gate_signature = ?
          AND replay_policy = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            task_slug,
            files_hash,
            descriptor.trigger,
            descriptor.files_json(),
            descriptor.gate_signature,
            REPLAYABLE,
        ),
    ).fetchone()
    if row is None:
        return None
    run = dict(row) if not isinstance(row, dict) else row
    if descriptor_from_row(run) is None:
        # The SQL predicate proves only the replay-side fields it compares.
        # A NULL/corrupt presentation field still makes the shared descriptor
        # incomplete, and an incomplete proof grants neither right.
        return None
    try:
        ran_at = datetime.fromisoformat(run["ran_at"].replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    age = (datetime.now(timezone.utc) - ran_at).total_seconds()
    if age > max_age_s:
        return None
    return run


# verify-cache-empty-scope-hit removed `lookup_any_fresh_run_for_task`.
# It returned the latest fresh green row for a slug regardless of
# files_hash/descriptor, to serve the relaxed "manual-scope verify certifies an
# explicit file set" fallback in `verify_cache` and `service_verification`.
# Both callers are gone: with no declared files the scoped gates are skipped,
# so such a run never had standing to certify anything. Nothing else read it,
# and a lookup that deliberately ignores the file hash is not worth keeping
# around for a future caller to rediscover.


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

    Returns the structured file list when a fresh exit-zero row exists for
    `task_slug`; `None` when no row, the row is stale, or its descriptor is
    absent, corrupt, or empty.

    v14b-defect-recover-files-from-task-done-row: filter to trigger=verify
    rows only. A fresh task-done filesize PASS row also has exit_code=0 and
    carries a file identity from the caller's --relevant-files; if
    we recovered from it, the resulting files_hash would NOT match what
    `tausik verify` recorded with empty files (manual scope), and the next
    `task done` would miss the cache and fail with "no fresh verify run".
    """
    if not task_slug:
        return None
    row = conn.execute(
        """
        SELECT run_trigger, run_files_json, gate_signature, replay_policy,
               presentation_policy, ran_at
        FROM verification_runs
        WHERE task_slug = ?
          AND exit_code = 0
          AND run_trigger = 'verify'
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
    descriptor = descriptor_from_row(record)
    return list(descriptor.files) if descriptor and descriptor.files else None
