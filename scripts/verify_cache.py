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
import json
import sqlite3
from typing import Any

from security_pattern import is_security_sensitive
from verify_constants import DEFAULT_CACHE_TTL_S
from verify_files_hash import compute_files_hash
from verify_own_export import coverage_files
from verify_recent_lookup import lookup_recent_for_task
from verify_run_descriptor import VerificationRunDescriptor
from verify_zero_gate import rests_on_a_declaration


def is_cache_allowed(file_paths: list[str]) -> bool:
    """Permission gate for any cache write/read for this file set.

    Returns False for security-sensitive paths so we never trust a cached
    green for auth/payment/secrets etc. — verify always re-runs.
    """
    return not is_security_sensitive(file_paths)


_NON_EXECUTION_GATE_FIELDS = frozenset({"description", "prevents"})
_UNORDERED_GATE_LIST_FIELDS = frozenset(
    {
        "evidence_capabilities",
        "exempt_dirs",
        "exempt_files",
        "file_extensions",
        "file_patterns",
        "stacks",
        "trigger",
    }
)


def _canonical_gate_value(field: str, value: Any) -> Any:
    """Normalize fields whose consumers use membership rather than order."""
    if field not in _UNORDERED_GATE_LIST_FIELDS or not isinstance(value, list):
        return value
    by_json = {
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")): item
        for item in value
    }
    return [by_json[key] for key in sorted(by_json)]


def _semantic_gate_projection(trigger: str, gates: list[dict[str, Any]]) -> dict[str, Any]:
    """Canonical effective gate config, excluding prose-only annotations.

    The runner and built-in implementations may consume gate-specific fields,
    so an allow-list would become incomplete each time a new gate knob ships.
    Hash the full resolved mapping instead. Only human rationale is excluded;
    leading-underscore keys are config annotations such as `_timeout_reason`.
    """
    projected = []
    for gate in gates:
        projected.append(
            {
                key: _canonical_gate_value(key, value)
                for key, value in gate.items()
                if key not in _NON_EXECUTION_GATE_FIELDS and not key.startswith("_")
            }
        )
    projected.sort(
        key=lambda gate: (
            str(gate.get("name", "")),
            json.dumps(gate, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
    )
    result: dict[str, Any] = {"trigger": trigger, "gates": projected}
    referenced_stacks = {
        stack for gate in gates for stack in (gate.get("stacks") or []) if isinstance(stack, str)
    }
    if referenced_stacks:
        from gate_stack_dispatch import stack_dispatch_semantics

        result["stack_dispatch"] = stack_dispatch_semantics(referenced_stacks)
    return result


def resolve_gate_signature(trigger: str = "task-done") -> str:
    """Stable hash of every effective execution field for `trigger`.

    Used as part of the verify-cache key so changing applicability, command,
    timeout, severity or a built-in gate's own config invalidates stale-green
    runs. On config-load failure returns a sentinel so verification is not
    blocked.

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
    canonical = json.dumps(
        _semantic_gate_projection(trigger, gates),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    h = hashlib.sha256()
    h.update(canonical.encode("utf-8"))
    return h.hexdigest()[:16]


def _build_cache_command(
    trigger: str, files: list[str], *, gate_signature: str | None = None
) -> str:
    """Cache key includes trigger so verify-run cache and task-done-run cache
    are stored in distinct buckets — prevents the legacy task-done bucket
    from satisfying a Verify-First lookup, and vice versa.
    """
    sig = gate_signature or resolve_gate_signature(trigger)
    return f"trigger={trigger}|sig={sig}|files={','.join(sorted(files))}"


def has_fresh_verify_run(
    conn: sqlite3.Connection,
    slug: str,
    relevant_files: list[str] | None,
    *,
    max_age_s: int = DEFAULT_CACHE_TTL_S,
    zero_gate_ack: bool = False,
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
        # records empty-scope rows as non-replayable, so this strict lookup can
        # no longer match them. Legacy rows carry no structured policy and any
        # future incomplete writer therefore also fails closed.
        # An unknown scope must never certify, whichever side is asked.
        return False, None
    if not is_cache_allowed(files):
        return False, None
    # verify-handle-dies-on-a-tasks-own-export-file: coverage is the declared
    # list MINUS this task's own export, because the verify run rewrites that
    # file itself (declared scope, run number, receipt) and hashing it asks
    # whether measuring changed the measured. See `verify_own_export` for why
    # only the task's OWN export is subtracted and what that costs.
    coverage = coverage_files(files, slug)
    if not coverage:
        # The declared list was non-empty, so the `if not files` guard above did
        # not fire — but everything in it was this task's own bookkeeping, and
        # `compute_files_hash([])` is the same empty-marker that guard exists to
        # reject: no edit ever moves it, so a row keyed on it would stay valid
        # for the whole TTL across arbitrary tree changes. A scope that covers
        # nothing is "unknown", not "verified empty" (#226), and a check that
        # could not compute its own coverage must not certify (#221).
        return False, None
    files_hash = compute_files_hash(coverage)
    # Keyed on the DECLARED list, not the coverage: the descriptor records what
    # the agent claimed, and the write side builds it the same way. Narrowing
    # it here would make the identities disagree and turn every lookup into a
    # miss.
    descriptor = VerificationRunDescriptor.create(
        trigger="verify",
        files=files,
        gate_signature=resolve_gate_signature("verify"),
        replayable=True,
        presentable_once=False,
    )
    hit = lookup_recent_for_task(
        conn,
        slug,
        files_hash=files_hash,
        descriptor=descriptor,
        max_age_s=max_age_s,
    )
    if hit is None:
        return False, None
    if rests_on_a_declaration(hit) and not zero_gate_ack:
        # senar-14-fail-closed-when-no-gate-actually-ran. The handle path is not
        # the only door. A run in which no gate executed still needs the
        # closer's explicit acknowledgement even when its structured replay
        # policy permits lookup. The row is returned alongside the refusal so
        # the caller can name which run it rejected.
        #
        # `zero_gate_ack` opens the same door here as on the handle path. The
        # acknowledgement is an act of the CLOSER, not a property of how the
        # green was presented, so making it work on one route and not the other
        # would turn a rule into a trivia question about which flag was used.
        return False, hit
    return True, hit
