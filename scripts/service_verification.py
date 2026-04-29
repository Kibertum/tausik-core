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
from typing import Any, Callable

# v1.3.4 git-diff cross-check lives in its own module for filesize compliance;
# re-export so existing callers keep working with `service_verification.X`.
from verify_git_diff import (  # noqa: F401
    changed_files_since,
    is_declared_consistent_with_git_diff,
)

# Default freshness window for cached verify runs.
# After this many seconds since the recorded run, the cache is treated as stale
# regardless of files_hash agreement. Aligned with SENAR Rule 9.3 checkpoint
# cadence (30-50 tool calls ≈ 5-15 min) — cache covers a coherent work session.
DEFAULT_CACHE_TTL_S = 600

# Security path tokens — bare match anywhere, slashes match only as path.
_SECURITY_PATH_TOKENS = tuple(
    "scripts/hooks/ /auth/ /payment/ /payments/ /billing/ /oauth/ /sso/ "
    "/saml/ /crypto/ /secrets/ /keys/ /admin/ /iam/ /permissions/ "
    "password webhook oauth csrf xsrf rbac acl jwt mfa 2fa totp api_key "
    "apikey session signup login".split()
)
_SEC_BASE = (
    "auth payment billing secret secrets credentials jwt session login "
    "signup password webhook webhooks csrf xsrf totp permissions acl rbac iam"
).split()
_SEC_EXT = (".py", ".ts", ".tsx", ".js", ".go", ".rs", ".php")
_SECURITY_BASENAMES = frozenset(f"{b}{e}" for b in _SEC_BASE for e in _SEC_EXT)

_SECURITY_EXTENSIONS = frozenset(
    {".env", ".pem", ".key", ".p12", ".pfx", ".crt", ".asc", ".gpg"}
)


def _utcnow_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


# v1.3.4: compute_files_hash extracted to verify_files_hash.py for filesize
# compliance. Re-exported so existing callers don't need to change.
from verify_files_hash import (  # noqa: F401, E402
    _FILES_HASH_CONTENT_SAMPLE_BYTES,
    compute_files_hash,
)


def is_security_sensitive(file_paths: list[str]) -> bool:
    """True iff any path matches a security-sensitive segment, basename, or ext.

    Three signals (any one triggers): path-tokens (e.g. `/auth/`, `/oauth/`),
    root-level basenames (`auth.py`, `payment.py`), or sensitive extensions
    (`.env`, `.pem`, `.key`). Stale green for these is more expensive than
    redundant gates.
    """
    for raw in file_paths or []:
        if not raw or not isinstance(raw, str):
            continue
        norm = "/" + raw.replace("\\", "/").lstrip("/")
        if any(tok in norm for tok in _SECURITY_PATH_TOKENS):
            return True
        basename = os.path.basename(norm)
        if basename in _SECURITY_BASENAMES:
            return True
        # extension match — handles `.env`, `foo.pem`, etc.
        for ext in _SECURITY_EXTENSIONS:
            if basename.endswith(ext):
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

    NOTE: This pure check does not detect under-declaration — the bypass
    where an agent reports `relevant_files=[docs/x.md]` while editing
    `scripts/auth.py`. For that, callers should also gate on
    `is_declared_consistent_with_git_diff(...)` — `run_gates_with_cache`
    does this when `task_created_at` is provided.
    """
    return not is_security_sensitive(file_paths)


def resolve_gate_signature(trigger: str = "task-done") -> str:
    """Stable hash of the active gate commands for `trigger`.

    Used as part of the verify-cache key so changing a gate's command in
    `project_config.DEFAULT_GATES` (or via `[tausik.verify]` overrides)
    invalidates stale-green runs that were recorded against the previous
    command. On config-load failure returns a sentinel so verification is
    not blocked.
    """
    try:
        from project_config import get_gates_for_trigger, load_config

        gates = get_gates_for_trigger(trigger, load_config())
    except Exception:
        return "unavailable"
    if not gates:
        return "empty"
    parts = sorted(
        f"{g.get('name', '?')}={(g.get('command') or '')}|sev={g.get('severity', '')}"
        for g in gates
    )
    h = hashlib.sha256()
    h.update("\n".join(parts).encode("utf-8"))
    return h.hexdigest()[:16]


def run_gates_with_cache(
    conn: sqlite3.Connection,
    slug: str,
    relevant_files: list[str] | None,
    *,
    scope: str = "lightweight",
    append_notes_fn: Callable[[str, str], None] | None = None,
    task_created_at: str | None = None,
    progress_fn: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[bool, list[dict[str, Any]], str | None]:
    """SENAR Rule 5 cache-aware gate run.

    Returns (passed, results, cache_status) where:
      passed: bool — final gate verdict (True if cache hit OR fresh green)
      results: gate_runner result list (empty when cache hit)
      cache_status: "hit" / "miss" / "bypass" / "git-mismatch" / None

    On a cache miss this records the run on green so future calls can hit.
    Security-sensitive file sets bypass the cache (always re-verify).
    `append_notes_fn(slug, msg)` is called once with a one-line summary so
    the caller does not need to know cache details.

    `task_created_at` (v1.3.4): when provided, the cache lookup is also
    gated on `is_declared_consistent_with_git_diff` — if the agent declared
    a strict subset of files actually changed since task start (per
    `git log --since` + `git diff HEAD`), the cache is refused (status
    "git-mismatch") to prevent the bypass where a misreported file scope
    masks a security-sensitive change. None or empty falls back to the
    pre-v1.3.4 behavior (security-only bypass).

    Concurrency note: two simultaneous `task done` calls for the same slug
    both miss cache, both run gates, both `record_run`. SQLite WAL keeps this
    safe (no corruption); the cost is duplicate `verification_runs` rows and
    redundant gate work. Accepted: blocking with BEGIN IMMEDIATE for the
    full gate-run window would lock the DB for the entire pytest duration,
    which is worse than the duplicate-row cost.
    """
    import time as _time

    from gate_runner import run_gates

    files = relevant_files or []
    files_hash = compute_files_hash(files)
    gate_sig = resolve_gate_signature("task-done")
    cache_command = f"trigger=task-done|sig={gate_sig}|files={','.join(sorted(files))}"
    cache_ok = is_cache_allowed(files)

    git_diff_consistent = True
    if cache_ok and task_created_at and files:
        git_diff_consistent = is_declared_consistent_with_git_diff(
            files, task_created_at
        )
        if not git_diff_consistent and append_notes_fn is not None:
            append_notes_fn(
                slug,
                "WARN: declared relevant_files is a strict subset of files "
                "changed since task start (git diff). Cache refused — "
                "running fresh verify to prevent stale-green via misreported scope.",
            )

    if cache_ok and git_diff_consistent:
        try:
            from project_config import load_config

            ttl = load_config().get("verify_cache_ttl_seconds", DEFAULT_CACHE_TTL_S)
        except Exception:
            ttl = DEFAULT_CACHE_TTL_S
        hit = lookup_recent_for_task(
            conn, slug, files_hash=files_hash, command=cache_command, max_age_s=ttl
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
    passed, results = run_gates(
        "task-done", relevant_files, progress_callback=progress_fn
    )
    duration_ms = int((_time.monotonic() - t0) * 1000)
    if results and append_notes_fn is not None:
        summary = ", ".join(
            r["name"] + "=" + ("PASS" if r["passed"] else "FAIL") for r in results
        )
        append_notes_fn(slug, f"Gates: {summary}")
    if not files and any(r.get("skipped") for r in results):
        if append_notes_fn is not None:
            append_notes_fn(
                slug,
                "WARN: no relevant_files passed — scoped gates SKIPPED. "
                "v1.3 removed full-suite fallback. Pass --relevant-files for verification.",
            )
    # v1.3 blind-review pass: If relevant_files was supplied but EVERY gate was skipped (no
    # test mapped, source-without-test), don't pass as green. Report a synthetic
    # blocking failure so QG-2 surfaces the missing tests instead of silently
    # closing the task. This is the "auth/login.py exists, no tests/test_login.py"
    # bypass discovered by the v1.3 blind review.
    if files and results and all(r.get("skipped") for r in results):
        if append_notes_fn is not None:
            append_notes_fn(
                slug,
                f"FAIL: relevant_files {files} mapped to NO test files. "
                "Add tests/test_<basename>.py or pass --no-knowledge if intentional.",
            )
        synth = {
            "name": "scoped-pytest",
            "passed": False,
            "skipped": False,
            "severity": "block",
            "output": f"No tests mapped for {files}",
        }
        return False, [synth], "no-test-mapped"
    # Don't cache an "all-skipped" run as if it were verified — that would
    # let the next caller's gates be silently skipped via cache hit on the
    # same files_hash for 10 minutes. SCOPED-SKIP means "no test mapped" —
    # not "verified clean". Require at least one real (non-skipped) PASS.
    has_real_pass = any(r.get("passed") and not r.get("skipped") for r in results)
    if passed and cache_ok and has_real_pass:
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
    if not cache_ok:
        cache_status = "bypass"
    elif not git_diff_consistent:
        cache_status = "git-mismatch"
    else:
        cache_status = "miss"
    return passed, results, cache_status
