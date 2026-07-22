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
from verify_constants import DEFAULT_CACHE_TTL_S
from verify_files_hash import compute_files_hash
from verify_recent_lookup import lookup_recent_for_task


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

    l26-config-not-repo-state-audit — verdict: uses the EFFECTIVE `load_config`
    (merged tiers) deliberately, NOT the repo-only `load_project_config`. Its
    subject is *the gate set that actually ran*, and gates run from the merged
    config (`get_gates_for_trigger(..., load_config())`); a signature over the
    repo tier alone would stop reflecting a user/managed gate-command change and
    could reuse a stale green across it. Both the write side (recording a run)
    and the read side (`has_fresh_verify_run`) compute it from the same source,
    so within one machine's verify→done flow the config is static and the
    signatures match. The only divergence is an operator editing a trusted tier
    *between* the two calls — rare, and fail-SAFE (an extra run, never a false
    green). Pinning to the repo tier would trade that harmless miss for a real
    stale-green window, so it is intentionally left as-is.
    """
    try:
        from project_config import get_gates_for_trigger, load_config

        gates = get_gates_for_trigger(trigger, load_config())
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
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

    verify-cache-empty-scope-hit: the lookup is strict-only. It used to fall
    back to a relaxed branch that accepted any fresh green row whose recorded
    command named NO files ("manual scope", Sharp edge #2 / gotcha #111) as a
    certificate for an arbitrary explicit file set. That premise was wrong:
    when `relevant_files` is empty, `gate_runner` SKIPS the scoped gates ("No
    relevant_files passed; gate skipped"), so such a run proves nothing about
    any file. Worse, `compute_files_hash([])` is a stable empty-marker that no
    edit ever moves, so the row stayed valid for the whole TTL across
    arbitrary tree changes — the exact stale-green class this cache exists to
    prevent. An undeclared scope is "unknown", not "empty" (#226), and a check
    that could not compute its own coverage must not certify (#221).
    """
    files = relevant_files or []
    if not files:
        # Defence in depth, independent of the write side. `run_gates_with_cache`
        # now stamps empty-scope rows `noncacheable|` so this strict lookup can
        # no longer match them by command — but rows written before that change
        # (and any future writer that forgets the prefix) would still carry a
        # clean command plus the empty-marker hash, and would strict-match here.
        # An unknown scope must never certify, whichever side is asked.
        return False, None
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
    if hit is None:
        return False, None
    return True, hit
