"""Verify cache helpers — gate-signature key build + freshness lookup.

Extracted from service_verification.py for filesize compliance
(v14b-filesize-debt-paydown). Public surface:

    resolve_gate_signature(trigger) -> str
    _build_cache_command(trigger, files) -> str
    has_fresh_verify_run(conn, slug, relevant_files, *, max_age_s) -> (bool, dict|None)

Behaviour is identical to the previous in-place implementation; service_verification
re-exports these names for backwards compatibility (no caller changes).
"""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from security_pattern import is_security_sensitive
from verify_files_hash import compute_files_hash
from verify_recent_lookup import lookup_recent_for_task


# Mirrors service_verification.DEFAULT_CACHE_TTL_S; kept local to avoid an
# import cycle (service_verification imports from this module).
DEFAULT_CACHE_TTL_S = 600


def is_cache_allowed(file_paths: list[str]) -> bool:
    """Permission gate for any cache write/read for this file set.

    Returns False for security-sensitive paths so we never trust a cached
    green for auth/payment/secrets etc. — verify always re-runs.
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


def _build_cache_command(trigger: str, files: list[str]) -> str:
    """Cache key includes trigger so verify-run cache and task-done-run cache
    are stored in distinct buckets — prevents the legacy task-done bucket
    from satisfying a Verify-First lookup, and vice versa.
    """
    sig = resolve_gate_signature(trigger)
    return f"trigger={trigger}|sig={sig}|files={','.join(sorted(files))}"


def has_fresh_verify_run(
    conn: sqlite3.Connection,
    slug: str,
    relevant_files: list[str] | None,
    *,
    max_age_s: int = DEFAULT_CACHE_TTL_S,
) -> tuple[bool, dict[str, Any] | None]:
    """Verify-First Contract: True iff a green `tausik verify` run exists for
    this task with matching files_hash and current verify gate signature,
    no older than `max_age_s` seconds.

    Used by `task_done` to enforce that heavy gates already passed without
    actually running them again. The returned dict (when present) is the
    `verification_runs` row so the caller can surface its age in messages.

    Security-sensitive file sets always return False — never trust a cached
    green for auth/payment paths even if it would otherwise match.
    """
    files = relevant_files or []
    if not is_cache_allowed(files):
        return False, None
    files_hash = compute_files_hash(files)
    cache_command = _build_cache_command("verify", files)
    hit = lookup_recent_for_task(
        conn,
        slug,
        files_hash=files_hash,
        command=cache_command,
        max_age_s=max_age_s,
    )
    return (hit is not None), hit
