#!/usr/bin/env python3
"""Supervision audit telemetry — the countable trace every weakening leaves.

Extracted from `_common` when the degradation helper
(hook-fail-open-db-error-telemetry) pushed that file past the 400-line filesize
gate. Splitting was the honest fix — the alternative, an exemption entry, would
have silenced the gate rather than answered it (convention: a gate must judge,
not be switched off).

`_common` re-exports these names, so every existing `from _common import
emit_supervision_bypass` keeps working; this module is the canonical home.

Three event shapes, one writer, three metric buckets (see
`backend_queries_metrics._supervision_by_action`):
  - bypass_<vector>     an INTENTIONAL weakening (skip_hooks, auto_verify, ...)
  - fail_open_<reason>  a SILENT degradation (a guard could not read the DB)
  - <other>             a DETECTION — supervision that WORKED
"""

from __future__ import annotations

import os


def emit_supervision_bypass(
    project_dir: str, vector: str, entity_id: str, details: str | None = None
) -> bool:
    """Record an audit event when a supervision mechanism is bypassed/weakened.

    l26-bypass-telemetry: every way to weaken enforcement — TAUSIK_SKIP_HOOKS,
    TAUSIK_SKIP_PUSH_HOOK, auto_verify, l3_block_on_high, scope_hard_gate,
    gates_disable — must leave a trace. Otherwise the system cannot say how
    many times it was switched off, and any claim of enforcement is
    unfalsifiable (release-1.8 thesis: guard the sincere agent, not the liar).

    Writes ONE row to `events`: entity_type='supervision',
    entity_id=<the specific hook/task/gate>, action='bypass_<vector>'.
    Metrics aggregate by `action` over entity_type='supervision'.

    Deliberately does NOT read TAUSIK_SKIP_HOOKS: the whole point is to record
    the skip, not to be silenced by the very flag it audits.

    Returns True iff the row was written, False on any best-effort failure —
    so a caller that CAN report the miss (a CLI, a script) may, without ever
    forcing the row: a fire-and-forget hook still just ignores the bool.
    """
    return _emit_supervision(project_dir, f"bypass_{vector}", entity_id, details)


def emit_supervision_degradation(
    project_dir: str, reason: str, entity_id: str, details: str | None = None
) -> bool:
    """Record an audit event when supervision is SILENTLY weakened — not by an
    explicit switch, but because a guard could not do its job and failed open.

    hook-fail-open-db-error-telemetry: task_gate/scope_write_gate fail OPEN on a
    sqlite error (a locked/corrupt DB lets the edit through unless
    TAUSIK_HOOK_FAIL_SECURE is set). Without a trace this is indistinguishable
    from "nothing to block" — a transient DB fault silently drops enforcement
    and no one can count it. This is a DEGRADATION, categorically distinct from
    an intentional `bypass_*`: the agent did not switch anything off. It is also
    distinct from a DETECTION (supervision that worked). The metric keeps all
    three apart; see `_supervision_by_action`.

    Writes ONE row: action='fail_open_<reason>'. Same chain-safe, best-effort
    machinery as `emit_supervision_bypass`.

    Inherent ceiling: the sink IS the DB that just failed to read. A read that
    errored on a lock may let a subsequent write through, or may not — if it
    doesn't, best-effort swallows it. A degradation this records is a floor on
    the true count, never an overcount, and that is the honest best we can do
    without an external sink (out of scope).

    Returns True iff the row was written, False on any best-effort failure.
    """
    return _emit_supervision(project_dir, f"fail_open_{reason}", entity_id, details)


def _emit_supervision(
    project_dir: str, action: str, entity_id: str, details: str | None = None
) -> bool:
    """Shared writer for supervision audit rows (bypass / degradation).

    Writes ONE row to `events`: entity_type='supervision', with the caller's
    fully-qualified `action`. A raw INSERT leaves prev_hash/entry_hash NULL and
    is sealed lazily by events_seal on the next verify/anchor pass. Best-effort:
    MUST NOT block or raise — telemetry that crashes the supervisor it audits is
    worse than a missing row.

    Returns True iff the INSERT committed, False otherwise (no DB, locked,
    corrupt, permission). The bool lets a non-fire-and-forget caller distinguish
    a landed row from a swallowed miss so it does not CLAIM a record it never
    made — while a hook that does not care simply ignores it.
    """
    import sqlite3

    db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(db):
        return False
    try:
        conn = sqlite3.connect(db, timeout=2)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                "INSERT INTO events(entity_type, entity_id, action, details) "
                "VALUES ('supervision', ?, ?, ?)",
                (entity_id, action, details),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — best-effort telemetry, never blocks
        return False
    return True
