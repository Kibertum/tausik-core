"""Insert a verification_run row and emit its signed receipt.

Extracted from service_verification.py for filesize-gate compliance when
l26-verify-git-diff-wire added the declared-scope columns. Follows the same
pattern as verify_cache.py / verify_files_hash.py: the logic lives here,
`service_verification` re-exports it, and every existing caller
(`service_verification.record_run`, `sv.record_run` in tests) keeps working
unchanged.

`_utcnow_iso` is defined locally rather than imported back from
service_verification — importing it would make the two modules circular, and
the same two-line helper is already defined independently in brain_status.py,
brain_metrics_log.py, model_routing_session.py and verify_endpoint.py.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    gate_results: list[dict[str, Any]] | None = None,
    project_dir: str | None = None,
    scope_description: dict[str, Any] | None = None,
    trigger: str | None = None,
    no_tests_declared: bool = False,
) -> int:
    """Insert a verify run. Returns the new row id.

    With `gate_results` and a `task_slug`, also emits a signed receipt into
    the row's receipt_json (v15-receipt-emit-on-verify). Emission is
    best-effort: no project key / signing failure never breaks the run
    record. `project_dir` defaults to the current working directory (the
    CLI/MCP convention for key lookup).

    `scope_description` (l26-verify-git-diff-wire) is the dict from
    `verify_scope_honesty.describe_declared_scope`. It is persisted on the row
    AND signed into the receipt, so the proof states whether its own scope was
    known to be complete. Omitting it records "unknown" — never "complete":
    a caller that did not measure must not be able to claim full coverage by
    saying nothing.

    `no_tests_declared` (verify-no-test-mapped-dead-end) marks a run that
    passed with NO gate executed because the caller declared none was expected.
    It is a column rather than a `scope` value: `scope` is CHECK-constrained to
    the SENAR tiers, so encoding it there raised IntegrityError against every
    real database while passing in tests whose DDL omits the constraint.
    """
    status = str((scope_description or {}).get("status") or "unknown")
    undeclared = list((scope_description or {}).get("undeclared") or [])
    undeclared_count = int((scope_description or {}).get("undeclared_count") or 0)
    cur = conn.execute(
        """
        INSERT INTO verification_runs
            (task_slug, scope, command, exit_code, summary, files_hash,
             ran_at, duration_ms, declared_scope_status, undeclared_files,
             no_tests_declared)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            status,
            json.dumps(undeclared, ensure_ascii=True, sort_keys=True) if undeclared else None,
            1 if no_tests_declared else 0,
        ),
    )
    run_id = int(cur.lastrowid or 0)
    # One transaction for the run and the gate rows that justify it: a run row
    # without its evidence would be a claim we could no longer check. Raises on
    # failure rather than degrading — see gate_run_record's module docstring.
    if gate_results:
        from gate_run_record import record_gate_runs

        record_gate_runs(
            conn,
            verification_run_id=run_id,
            task_slug=task_slug,
            trigger=trigger,
            gate_results=gate_results,
        )
    conn.commit()
    if task_slug and gate_results is not None:
        from verify_receipt_emit import emit_signed_receipt

        emit_signed_receipt(
            conn,
            run_id,
            task_slug=task_slug,
            scope=scope,
            gate_results=gate_results,
            passed=exit_code == 0,
            files_hash=files_hash,
            project_dir=project_dir or ".",
            declared_scope_status=status,
            undeclared_files=undeclared,
            undeclared_count=undeclared_count,
        )
    return run_id


class VerificationRecordError(RuntimeError):
    """The evidence for a verify run could not be written.

    Raised instead of being logged and swallowed (verify-record-failure-
    swallowed). A caller that catches this must not report the run as passed:
    a run whose evidence is missing is indistinguishable afterwards from a run
    that never happened, which is exactly the state `verification_runs` exists
    to make impossible (#221).
    """


# Status returned by `run_gates_with_cache` when the gates themselves were fine
# but their evidence could not be persisted. Distinct from "miss"/"bypass" on
# purpose: those describe cache *reuse*, this describes a missing proof.
RECORD_FAILED_STATUS = "record-failed"

# Name of the synthetic blocking gate result that carries the failure outward.
RECORD_GATE_NAME = "verify-record"

# Bounded retry for a *transient* lock only. `project_backend` already sets
# `PRAGMA busy_timeout=5000`, which covers contention inside SQLite's own lock
# wait — but not every connection in this project inherits it (MCP handlers,
# hooks and tests each open their own), so the policy is stated here rather
# than assumed from a pragma set elsewhere. Three attempts, then an honest
# failure: a lock that outlives the backoff is not the transient case.
RECORD_MAX_ATTEMPTS = 3
RECORD_RETRY_BACKOFF_S = 0.1

# sqlite3 reports contention through OperationalError, whose only
# distinguishing feature is its message. Matching on text is unpleasant, but it
# is the API: "database is locked" (write lock held) and "database table is
# locked" / "busy" (shared cache). Everything else — "no such table", "no such
# column" — is a broken schema, which no amount of retrying fixes.
_TRANSIENT_LOCK_MARKERS = ("locked", "busy")


def _is_transient_lock(exc: BaseException) -> bool:
    if not isinstance(exc, sqlite3.OperationalError):
        return False
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_LOCK_MARKERS)


def record_failure_result(exc: BaseException) -> dict[str, Any]:
    """The synthetic blocking gate result that makes a lost write visible.

    One spelling, because three call sites need it — and a verdict that differs
    by entry point is precisely the class of defect this area keeps producing.
    """
    return {
        "name": RECORD_GATE_NAME,
        "passed": False,
        "skipped": False,
        "severity": "block",
        "output": (
            f"Failed to record the verification run: {type(exc).__name__}: {exc}. "
            "The gates may well have passed, but their evidence was not "
            "persisted — so this run certifies nothing and cannot be reused. "
            "Fix the database error and re-run verify."
        ),
        "duration_ms": 0,
    }


def _record_verification(
    conn: sqlite3.Connection,
    *,
    slug: str,
    command: str,
    exit_code: int,
    summary: str,
    files_hash: str,
    gate_results: list[dict[str, Any]],
    scope_desc: dict[str, Any],
    trigger: str,
    scope: str,
    duration_ms: int | None = None,
    details: dict[str, Any] | None = None,
    no_tests_declared: bool = False,
) -> int:
    """The single write point into `verification_runs`.

    cli-verify-bypasses-cache-guards: there used to be a second one in
    `project_cli_verify.cmd_verify`, which called `record_run` directly and
    therefore carried none of this function's callers' guards. Rules that
    exist in two copies drift — that is what the defect was. Every write now
    funnels through here.

    Raises `VerificationRecordError` when the write cannot happen. It used to
    log a warning and return None while leaving the caller's `passed`
    untouched, so a run with no evidence behind it reached `task done` as an
    ordinary green (verify-record-failure-swallowed). That except caught
    precisely the exception `gate_run_record` raises to guarantee the opposite
    — the fail-closed contract stated in its docstring was being annulled one
    level up. Nothing here is best-effort any more.

    A transient lock is retried (see `RECORD_MAX_ATTEMPTS`); a permanent error
    is not, because retrying an IntegrityError only delays the same failure and
    buries its cause under a pause.
    """
    import time as _time

    for attempt in range(1, RECORD_MAX_ATTEMPTS + 1):
        try:
            run_id = record_run(
                conn,
                task_slug=slug or None,
                scope=scope,
                command=command,
                exit_code=exit_code,
                summary=summary,
                files_hash=files_hash,
                duration_ms=duration_ms,
                gate_results=gate_results,
                scope_description=scope_desc,
                trigger=trigger,
                no_tests_declared=no_tests_declared,
            )
        except Exception as exc:  # noqa: BLE001 — re-raised below, never swallowed
            # `record_run` inserts, writes the gate rows, then commits. A
            # failure anywhere in that sequence can leave the connection
            # mid-transaction; retrying on a dirty connection would fail for a
            # second, unrelated reason and report *that* one as the cause.
            try:
                conn.rollback()
            except sqlite3.Error:  # pragma: no cover — nothing useful to do here
                pass
            if attempt < RECORD_MAX_ATTEMPTS and _is_transient_lock(exc):
                _time.sleep(RECORD_RETRY_BACKOFF_S * attempt)
                continue
            import logging

            logging.getLogger("tausik.gates").warning(
                "Failed to record verification run for %s (attempt %d/%d)",
                slug,
                attempt,
                RECORD_MAX_ATTEMPTS,
                exc_info=True,
            )
            raise VerificationRecordError(
                f"could not record the verification run for {slug or '-'}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if details is not None:
            details["run_id"] = run_id
        return run_id
    raise AssertionError("unreachable")  # pragma: no cover — loop returns or raises
