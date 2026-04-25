"""SENAR verification cache: record + lookup verify runs to skip redundant gates.

Per SENAR Rule 5 (Verification Checklist tiers), per-task verification should
be scoped — not a full-suite re-run. To avoid wasted cycles, every successful
gate run is recorded with a stable hash of the relevant files. On subsequent
`task done` calls within the freshness window, if the same files have not
changed, the cached result is reused.

Stack-agnostic: the cache layer doesn't know about pytest/cargo/etc. — it
records `(command, exit_code)` and trusts the caller to recompute the right
hash for the file set being verified.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

# Default freshness window for cached verify runs.
# After this many seconds since the recorded run, the cache is treated as stale
# regardless of files_hash agreement. Aligned with SENAR Rule 9.3 checkpoint
# cadence (30-50 tool calls ≈ 5-15 min) — cache covers a coherent work session.
DEFAULT_CACHE_TTL_S = 600

# File-tree segments that always force re-verification (security-sensitive).
_SECURITY_PATH_TOKENS = (
    "scripts/hooks/",
    "/auth/",
    "/payment/",
    "/payments/",
    "/billing/",
)


def _utcnow_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def compute_files_hash(file_paths: list[str], *, root: str | None = None) -> str:
    """SHA256 over (canonical_path, mtime_ns, size) tuples.

    Order-independent (sorted before hashing). Missing files contribute their
    canonical path with mtime/size sentinel `0` so the hash detects "file
    appeared / disappeared" changes.

    Empty list → stable empty-marker hash (so cache-by-hash still works for
    full-suite verifies that have no scoped files).
    """
    base = root or os.getcwd()
    canon: list[tuple[str, int, int]] = []
    for raw in file_paths or []:
        if not raw or not isinstance(raw, str):
            continue
        rel = raw.replace("\\", "/")
        abs_p = rel if os.path.isabs(rel) else os.path.join(base, rel)
        try:
            st = os.stat(abs_p)
            canon.append((rel, st.st_mtime_ns, st.st_size))
        except OSError:
            canon.append((rel, 0, 0))
    canon.sort()
    h = hashlib.sha256()
    h.update(b"verification_runs.v1\n")
    for path, mtime_ns, size in canon:
        h.update(f"{path}|{mtime_ns}|{size}\n".encode())
    return h.hexdigest()


def is_security_sensitive(file_paths: list[str]) -> bool:
    """True iff any path in `file_paths` matches a security-sensitive segment.

    These tasks always re-verify (cache disabled) — the cost of a stale green
    on auth/payment/hook code is higher than the cost of redundant gates.
    """
    for raw in file_paths or []:
        if not raw or not isinstance(raw, str):
            continue
        norm = "/" + raw.replace("\\", "/").lstrip("/")
        if any(tok in norm for tok in _SECURITY_PATH_TOKENS):
            return True
    return False


def record_run(
    conn: sqlite3.Connection,
    *,
    task_slug: str | None,
    scope: str,
    command: str,
    exit_code: int,
    summary: str | None,
    files_hash: str,
    duration_ms: int | None = None,
) -> int:
    """Insert a verify run. Returns the new row id."""
    cur = conn.execute(
        """
        INSERT INTO verification_runs
            (task_slug, scope, command, exit_code, summary, files_hash,
             ran_at, duration_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_slug,
            scope,
            command,
            exit_code,
            summary,
            files_hash,
            _utcnow_iso(),
            duration_ms,
        ),
    )
    conn.commit()
    return int(cur.lastrowid or 0)


def lookup_recent_for_task(
    conn: sqlite3.Connection,
    task_slug: str,
    *,
    files_hash: str,
    command: str,
    max_age_s: int = DEFAULT_CACHE_TTL_S,
) -> dict[str, Any] | None:
    """Return the most recent green verify run for `task_slug` if usable.

    Returns None when:
      - no run for this task
      - most recent run failed (exit_code != 0)
      - files_hash mismatch (files changed since)
      - command mismatch (gate config changed)
      - older than `max_age_s` seconds

    The caller treats `None` as "must run fresh verify".
    """
    if not task_slug:
        return None
    row = conn.execute(
        """
        SELECT id, task_slug, scope, command, exit_code, summary,
               files_hash, ran_at, duration_ms
        FROM verification_runs
        WHERE task_slug = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (task_slug,),
    ).fetchone()
    if row is None:
        return None
    run = dict(row) if not isinstance(row, dict) else row
    if run["exit_code"] != 0:
        return None
    if run["files_hash"] != files_hash:
        return None
    if run["command"] != command:
        return None
    try:
        ran_at = datetime.fromisoformat(run["ran_at"].replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    age = (datetime.now(timezone.utc) - ran_at).total_seconds()
    if age > max_age_s:
        return None
    return run


def is_cache_allowed(file_paths: list[str]) -> bool:
    """Cache is allowed unless the file set is security-sensitive.

    Security-sensitive tasks (hooks, auth, payment) always re-verify so a
    stale green never masks a regression in security-critical code.
    """
    return not is_security_sensitive(file_paths)
