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

import glob
import json
import os
import sys
import time

#: The file fallback-sink for a supervision event whose DB write missed.
#: hook-bypass-telemetry-silent-miss (Decision #180). When the normal sink — the
#: project DB — is unreachable (no DB yet in the bootstrap→init window, or a
#: locked/corrupt DB under concurrent WAL access), the miss used to vanish and
#: the weakening it records became uncountable, breaking the release-1.8 thesis
#: that every weakening must leave a COUNTABLE trace. A plain append-only file
#: next to the DB is a DIFFERENT sink that does not share the DB's failure mode,
#: so it survives exactly the moments the DB does not. Reconciled into `events`
#: on the next successful write (see `_drain_pending`).
#:
#: Each miss is its OWN file, published atomically with `os.replace` from a temp
#: name (review s126): a shared append-only file let a concurrent drain rename
#: the file out from under an in-flight `write()`, and on POSIX that write lands
#: in an already-unlinked inode and is silently LOST — the one failure direction
#: the "never hide a weakening" invariant cannot tolerate. A per-miss file that
#: only becomes visible under its final name once fully written closes that
#: window: a drain sees a complete file or nothing, never a half-written one.
_PENDING_PREFIX = "supervision_pending"
_PUBLISHED_GLOB = f"{_PENDING_PREFIX}.*.jsonl"  # a complete, unclaimed miss
_CLAIM_GLOB = f"{_PENDING_PREFIX}.*.draining"  # a miss a drain is (or was) folding in

#: Unique-within-process suffix component, so two misses in one process never
#: collide on a filename even inside the same `time.time_ns()` tick.
_seq = 0


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _unique_token() -> str:
    global _seq
    _seq += 1
    return f"{os.getpid()}.{time.time_ns()}.{_seq}"


def _append_pending(project_dir: str, action: str, entity_id: str, details: str | None) -> bool:
    """Record a missed supervision event in the file fallback-sink.

    Best-effort and self-guarded: this runs on the failure path of a hook and
    must never raise. The record carries the ORIGINAL timestamp so a later
    reconciliation dates the event when it happened, not when it was folded in.
    Writes only when `.tausik/` exists (the emitter's jurisdiction); if even the
    file cannot be written, a last-resort stderr line keeps the weakening from
    being wholly invisible in the moment.

    Written to a temp name and `os.replace`d to its final `supervision_pending.
    <uniq>.jsonl` — the record is complete before it is ever visible to a drain.
    """
    tdir = os.path.join(project_dir, ".tausik")
    if not os.path.isdir(tdir):
        return False
    record = {
        "entity_id": entity_id,
        "action": action,
        "details": details,
        "created_at": _now_iso(),
    }
    try:
        token = _unique_token()
        blob = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
        # The temp name starts with a dot so it matches NEITHER drain glob — a
        # drain never sees a partially written record.
        tmp = os.path.join(tdir, f".{_PENDING_PREFIX}.tmp.{token}")
        final = os.path.join(tdir, f"{_PENDING_PREFIX}.{token}.jsonl")
        with open(tmp, "wb") as fh:
            fh.write(blob)
        os.replace(tmp, final)  # atomic publish of a complete file
        return True
    except OSError:
        try:
            # ASCII only: this is a helper module with no entry point, so it
            # cannot call `force_utf8_io` (that reconfigures global streams and
            # belongs at a hook's entry, not at import of a helper). A last-
            # resort line needs no typography — keep it locale-independent.
            print(
                f"[TAUSIK supervision] UNRECORDED {action} on {entity_id} -- "
                "both the DB and the file sink were unavailable.",
                file=sys.stderr,
            )
        except Exception:  # noqa: BLE001 — even stderr may be closed; never raise
            pass
        return False


def _drain_pending(project_dir: str, conn) -> None:
    """Fold any file-sink misses into `events`, reusing an already-open `conn`.

    Called after a SUCCESSFUL supervision write — the DB is reachable now, so
    the backlog can be reconciled on the same connection (a second connection
    would risk the 'transaction within a transaction' crash the l3 downgrade
    already learned to avoid). Fully self-guarded: never raises, so a drain
    problem cannot re-pend or fail the current event.

    Concurrency (WAL + simultaneous MCP/CLI/hooks): each pending file is claimed
    atomically with `os.replace` onto a unique name. The loser of a race gets an
    OSError and skips, so one file is never processed twice under normal
    operation. Orphaned claims from a drain that crashed mid-fold are recovered
    on a later pass (the `_CLAIM_GLOB`). A crash BETWEEN commit and unlink can
    replay a file (an overcount), which is the safe direction here — the whole
    point is to never HIDE a weakening; inflating the count never does that,
    unlike dropping it.
    """
    tdir = os.path.join(project_dir, ".tausik")
    try:
        candidates = sorted(
            set(
                glob.glob(os.path.join(tdir, _PUBLISHED_GLOB))
                + glob.glob(os.path.join(tdir, _CLAIM_GLOB))
            )
        )
    except OSError:
        return
    claimed: list[str] = []
    for src in candidates:
        # Claim to a fresh `.draining` name (the whole token is regenerated, so
        # re-claiming an orphan does not grow the name). It matches `_CLAIM_GLOB`
        # but NOT `_PUBLISHED_GLOB`, so a claimed file is never re-globbed as new.
        claim = os.path.join(tdir, f"{_PENDING_PREFIX}.{_unique_token()}.draining")
        try:
            os.replace(src, claim)  # atomic; the racing loser gets OSError
            claimed.append(claim)
        except OSError:
            continue
    for snap in claimed:
        try:
            with open(snap, encoding="utf-8") as fh:
                lines = fh.readlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue  # a torn append: skip that line, keep the rest
                conn.execute(
                    "INSERT INTO events(entity_type, entity_id, action, details, created_at) "
                    "VALUES ('supervision', ?, ?, ?, ?)",
                    (
                        str(rec.get("entity_id", "")),
                        str(rec.get("action", "")),
                        rec.get("details"),
                        rec.get("created_at") or _now_iso(),
                    ),
                )
            conn.commit()
        except Exception:  # noqa: BLE001 — leave the snapshot for a later retry
            continue
        try:
            os.remove(snap)
        except OSError:
            pass


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

    Ceiling, now raised (hook-bypass-telemetry-silent-miss, Decision #180): the
    DB sink is the DB that just failed, but a miss no longer vanishes — it is
    appended to a file fallback-sink (`.tausik/supervision_pending.jsonl`) and
    reconciled into `events` on the next successful write. The file does not
    share the DB's failure mode, so the weakening stays countable even when the
    DB is unreachable.

    Returns True iff the row was written to the DB, False when it fell back to
    the file sink (or, in the rare case even that failed, to a last-resort
    stderr line).
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

    Returns True iff the INSERT committed to the DB, False otherwise (no DB,
    locked, corrupt, permission). A False is no longer a swallowed miss: the
    event is written to the file fallback-sink first (hook-bypass-telemetry-
    silent-miss, Decision #180), so a fire-and-forget hook that ignores the bool
    still leaves a countable trace. The bool now tells a non-fire-and-forget
    caller only WHERE the record landed (DB vs pending file), not whether it
    exists at all.
    """
    import sqlite3

    db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(db):
        # Bootstrap→init window: `.tausik/` exists, the DB does not yet. The
        # miss is real and jurisdiction is real — record it in the file sink so
        # it is still countable, then reconcile once the DB appears.
        _append_pending(project_dir, action, entity_id, details)
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
            # The DB is reachable — fold any earlier misses in now, on this same
            # connection. Self-guarded: a drain problem cannot fail this write.
            _drain_pending(project_dir, conn)
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — best-effort telemetry, never blocks
        # A locked/corrupt DB under concurrent access: don't lose the miss.
        _append_pending(project_dir, action, entity_id, details)
        return False
    return True
