"""Redemption of a presented verify handle — the fail-closed validator.

v2-verify-receipt-as-argument. `verify_handle` owns the storage mechanics
(mint, parse, atomic spend); this module owns the POLICY: what must be true
before a presented handle is allowed to satisfy QG-2, and what each refusal
says. They are separate because the mechanics are two SQL statements that will
not change, while every line below is a rule that will be argued with.

FAIL-CLOSED, AND WHAT THAT COSTS. Every check here refuses on doubt. A receipt
that will not parse, a signature that will not verify, a timestamp that will
not read, an absent public key — all of these are REFUSALS, not warnings. That
is a deliberate inversion of `verify_receipt_check`, which returns ok=True on
any internal error because there the receipt was a second opinion on top of a
row the caller had already found. Here the receipt IS the finding, so a
receipt we cannot read is a proof we do not have.

The one refusal that is not a suspicion is the keyless project: with no public
key nothing can be validated, so the handle path is closed and the caller is
told to run the gates inline (the pre-existing `auto_verify` route). That is a
NAMED mode, not a degradation — the distinction AC7 asks for.

WHAT IS RE-COMPUTED RATHER THAN READ. files_hash is recomputed from the files
the receipt names, off disk, at redemption time. The gate signature is
recomputed from the live config. Both are then compared against BOTH the
receipt and the row. SEP-2322: "Servers using plaintext state MUST treat the
decoded values as untrusted input". A handle that only checked the receipt
against itself would certify a stale tree perfectly.
"""

from __future__ import annotations

import hmac
import sqlite3

from verify_zero_gate import (
    is_non_replayable,
    non_replayable_refusal,
    rests_on_a_declaration,
)
from verify_zero_gate import refusal as zero_gate_refusal
from verify_handle import (
    HandleVerdict,
    load_run_for_handle,
    parse_handle,
    parse_iso,
    redeem,
)

# The three rules live next door; this module keeps the ORDER they run in, the
# refusal policy and the spend. See verify_handle_rules for why the seam is
# there rather than anywhere else.
from verify_handle_rules import _check_receipt, _no


def check_handle(
    conn: sqlite3.Connection,
    handle: str | None,
    *,
    task_slug: str,
    project_dir: str = ".",
    now_iso: str | None = None,
    zero_gate_ack: bool = False,
) -> HandleVerdict:
    """Validate a presented handle WITHOUT spending it.

    Split from `redeem_handle` so the refusals are testable without a write and
    so the spend is the last thing that happens — a handle must not be consumed
    by a close that then refuses for an unrelated reason.

    `zero_gate_ack` is the closer saying, in a separate act, that a run which
    executed NO gate is nonetheless the right basis for this closure. It
    defaults to False because §8.6(e) is about the verdict: a run with no
    evidence behind it certifies nothing until someone knowingly accepts it.
    See `verify_zero_gate`.
    """
    parsed = parse_handle(handle)
    if parsed is None:
        return _no(
            f"verify-handle: {handle!r} is not a handle. Expected "
            "'<run_id>.<32-hex-nonce>' exactly as `tausik verify --task "
            f"{task_slug}` printed it."
        )
    run_id, nonce = parsed

    run = load_run_for_handle(conn, run_id)
    if run is None:
        return _no(
            f"verify-handle: no verify run #{run_id} in this project's database. "
            "The handle was minted against a different project or the row is gone "
            f"— re-run `tausik verify --task {task_slug}`."
        )

    stored = run.get("handle_nonce")
    if not stored or not hmac.compare_digest(str(stored), nonce):
        # Constant-time comparison, because the nonce is the secret half. The
        # run id is NOT secret — it is a small sequential integer printed in
        # every verify output — so this refusal being distinguishable from the
        # "no such run" one above leaks nothing an attacker could not already
        # enumerate. Constant time is about the 128-bit value, not about making
        # the two messages identical.
        return _no(
            f"verify-handle: nonce does not match verify run #{run_id}. "
            "Handles are single-use and are replaced by each new verify — "
            f"present the one the LAST `tausik verify --task {task_slug}` printed.",
            run,
        )

    # `run.get("exit_code") or 1` would be the bug this line exists to avoid:
    # 0 is falsy, so the green case would take the default and every passing run
    # would be reported as red. Compare the value, do not coalesce it.
    exit_code = run.get("exit_code")
    if exit_code is None or int(exit_code) != 0:
        return _no(
            f"verify-handle: verify run #{run_id} did NOT pass (exit_code="
            f"{exit_code}). A red run has no standing to close a task.",
            run,
        )

    if str(run.get("task_slug") or "") != task_slug:
        return _no(
            f"verify-handle: run #{run_id} verified task "
            f"'{run.get('task_slug')}', but you are closing '{task_slug}'. "
            "A handle certifies the task it was minted for and no other.",
            run,
        )

    if is_non_replayable(run):
        return _no(non_replayable_refusal(run_id, task_slug), run)

    # Asked BEFORE the spend, like every other refusal here: a handle must not
    # be consumed by a close that then refuses. Asked AFTER the non-replayable
    # check because that one covers a wider class and gives the better message.
    if rests_on_a_declaration(run) and not zero_gate_ack:
        return _no(zero_gate_refusal(run_id, task_slug), run)

    if run.get("handle_redeemed_at"):
        # Reported before the atomic spend so the common case gets the specific
        # message. The spend still re-checks it — this branch is the diagnosis,
        # the UPDATE predicate is the guarantee (SEP-2322 replay).
        return _no(
            f"verify-handle: this handle was already spent at "
            f"{run['handle_redeemed_at']} (run #{run_id}). Handles are "
            f"single-use. Re-run `tausik verify --task {task_slug}`.",
            run,
        )

    expiry = parse_iso(run.get("handle_expires_at"))
    if expiry is None:
        return _no(
            f"verify-handle: run #{run_id} carries no readable expiry "
            f"({run.get('handle_expires_at')!r}). An expiry that cannot be read "
            "is not treated as absent — re-run verify to mint a fresh handle.",
            run,
        )
    now = parse_iso(now_iso) if now_iso else None
    if now is None:
        from verify_handle import _utcnow

        now = _utcnow()
    if now > expiry:
        return _no(
            f"verify-handle: expired at {run['handle_expires_at']} "
            f"(run #{run_id}). Re-run `tausik verify --task {task_slug}`.",
            run,
        )

    return _check_receipt(
        run,
        task_slug=task_slug,
        project_dir=project_dir,
        command=str(run.get("command") or ""),
    )


def redeem_handle(
    conn: sqlite3.Connection,
    handle: str | None,
    *,
    task_slug: str,
    project_dir: str = ".",
    zero_gate_ack: bool = False,
) -> HandleVerdict:
    """Validate and, on success, spend the handle exactly once.

    The spend is last and its result is authoritative: `check_handle` reports
    an already-spent handle for a good message, but only the atomic UPDATE
    decides. A caller that saw ok=True here may treat QG-2 as satisfied.
    """
    verdict = check_handle(
        conn,
        handle,
        task_slug=task_slug,
        project_dir=project_dir,
        zero_gate_ack=zero_gate_ack,
    )
    if not verdict.ok:
        return verdict
    parsed = parse_handle(handle)
    if parsed is None:  # pragma: no cover — check_handle already refused these
        return _no("verify-handle: malformed handle")
    run_id, nonce = parsed
    if not redeem(conn, run_id, nonce):
        return _no(
            f"verify-handle: run #{run_id} was spent by another close between "
            "validation and redemption. Handles are single-use — re-run "
            f"`tausik verify --task {task_slug}`.",
            verdict.run,
        )
    return verdict
