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


def run_gates_with_cache(
    conn: sqlite3.Connection,
    slug: str,
    relevant_files: list[str] | None,
    *,
    scope: str = "lightweight",
    append_notes_fn: Any = None,
) -> tuple[bool, list[dict[str, Any]], str | None]:
    """SENAR Rule 5 cache-aware gate run.

    Returns (passed, results, cache_status) where:
      passed: bool — final gate verdict (True if cache hit OR fresh green)
      results: gate_runner result list (empty when cache hit)
      cache_status: "hit" / "miss" / "bypass" / None (no caching done)

    On a cache miss this records the run on green so future calls can hit.
    Security-sensitive file sets bypass the cache (always re-verify).
    `append_notes_fn(slug, msg)` is called once with a one-line summary so
    the caller does not need to know cache details.
    """
    import time as _time

    from gate_runner import run_gates

    files = relevant_files or []
    files_hash = compute_files_hash(files)
    cache_command = f"trigger=task-done|files={','.join(sorted(files))}"
    cache_ok = is_cache_allowed(files)

    if cache_ok:
        hit = lookup_recent_for_task(
            conn, slug, files_hash=files_hash, command=cache_command
        )
        if hit is not None:
            if append_notes_fn is not None:
                append_notes_fn(
                    slug,
                    f"Gates: cache hit (verify run #{hit['id']}, "
                    f"ran_at={hit['ran_at']}, scope={hit['scope']})",
                )
            return True, [], "hit"

    t0 = _time.monotonic()
    passed, results = run_gates("task-done", relevant_files)
    duration_ms = int((_time.monotonic() - t0) * 1000)
    if results and append_notes_fn is not None:
        summary = ", ".join(
            r["name"] + "=" + ("PASS" if r["passed"] else "FAIL") for r in results
        )
        append_notes_fn(slug, f"Gates: {summary}")
    if passed and cache_ok:
        try:
            summary = (
                ", ".join(
                    r["name"] + "=" + ("PASS" if r["passed"] else "FAIL")
                    for r in results
                )
                or "ok"
            )
            record_run(
                conn,
                task_slug=slug,
                scope=scope,
                command=cache_command,
                exit_code=0,
                summary=summary,
                files_hash=files_hash,
                duration_ms=duration_ms,
            )
        except Exception:
            import logging

            logging.getLogger("tausik.gates").warning(
                "Failed to record verification run for %s", slug, exc_info=True
            )
    cache_status = "miss" if cache_ok else "bypass"
    return passed, results, cache_status
