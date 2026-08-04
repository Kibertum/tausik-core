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
from typing import Any

from verify_recent_lookup import extract_gate_signature
from verify_handle import (
    HandleVerdict,
    load_run_for_handle,
    parse_handle,
    parse_iso,
    redeem,
)

# Prefix stamped on rows that passed but may never be replayed (empty scope,
# all-skipped gates, security-sensitive set). `verify_cached_run` writes it; a
# handle must honour it or the prefix would guard one door and not the other.
_NONCACHEABLE_PREFIX = "noncacheable|"


def _no(
    reason: str,
    run: dict[str, Any] | None = None,
    files: list[str] | None = None,
) -> HandleVerdict:
    """A refusal. `files` is carried on the coverage refusals so a caller can
    report WHAT the receipt claimed to cover alongside why it was rejected."""
    return HandleVerdict(False, reason, run, files)


def check_handle(
    conn: sqlite3.Connection,
    handle: str | None,
    *,
    task_slug: str,
    project_dir: str = ".",
    now_iso: str | None = None,
) -> HandleVerdict:
    """Validate a presented handle WITHOUT spending it.

    Split from `redeem_handle` so the refusals are testable without a write and
    so the spend is the last thing that happens — a handle must not be consumed
    by a close that then refuses for an unrelated reason.
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

    command = str(run.get("command") or "")
    if command.startswith(_NONCACHEABLE_PREFIX):
        return _no(
            f"verify-handle: run #{run_id} is marked non-replayable "
            "(empty scope, all gates skipped, or a security-sensitive file set). "
            "It was recorded for the audit trail, not as a certificate. "
            f"Declare the scope and re-run `tausik verify --task {task_slug}`.",
            run,
        )

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

    return _check_receipt(run, task_slug=task_slug, project_dir=project_dir, command=command)


def _check_receipt(
    run: dict[str, Any],
    *,
    task_slug: str,
    project_dir: str,
    command: str,
) -> HandleVerdict:
    """The half of validation that reads the signed document itself."""
    import json

    import crypto_keys

    run_id = run["id"]
    raw = run.get("receipt_json")
    if not raw:
        return _no(
            f"verify-handle: verify run #{run_id} carries no receipt, so there "
            "is nothing to validate. Handles require a signed receipt; run "
            "`tausik key init` (or close without --verify-handle to use the "
            "freshness lookup).",
            run,
        )

    try:
        public = crypto_keys.load_public(project_dir)
    except (crypto_keys.KeyError_, OSError, ValueError, UnicodeDecodeError):
        # The tuple is wider than "no key" on purpose. `load_public` opens the
        # key file with encoding="ascii", so a PRESENT but corrupted key raises
        # UnicodeDecodeError — which is not KeyError_ and is caught nowhere up
        # the chain (`_enforce_handle` has no try/except, and the CLI dispatcher
        # only handles ServiceError/ValueError/KeyboardInterrupt). The close
        # would still fail, so the fail-closed property held, but it failed as a
        # raw traceback instead of the readable refusal this module promises.
        # An unreadable key and an absent one are the same fact here: nothing
        # can be validated.
        # The named mode, not a degradation. Deliberately NOT ok=True: a handle
        # whose receipt nobody can check proves nothing, and saying so is the
        # difference between "keyless project" and "validated".
        return _no(
            f"verify-handle: this project has no usable public key, so the "
            f"receipt on run #{run_id} cannot be validated — the handle path is "
            f"CLOSED here. "
            "Either `tausik key init` to enable receipts, or close without "
            "--verify-handle (gates run inline / freshness lookup applies). "
            "This is a keyless project, not a failed check.",
            run,
        )

    try:
        envelope = json.loads(raw)
    except (TypeError, ValueError):
        return _no(
            f"verify-handle: receipt_json on run #{run_id} is corrupt — the "
            "green it claims cannot be shown to be authentic.",
            run,
        )

    import crypto_sign

    if not crypto_sign.verify_receipt(envelope, public=public):
        return _no(
            f"verify-handle: INVALID ed25519 signature on run #{run_id} — the "
            "recorded verify result was modified after signing.",
            run,
        )

    receipt = envelope.get("receipt") or {}
    from crypto_receipt import missing_v3_fields

    missing = missing_v3_fields(receipt)
    if missing:
        return _no(
            f"verify-handle: receipt on run #{run_id} is schema "
            f"'{receipt.get('schema')}' and does not state {', '.join(missing)}. "
            "A presented receipt has to say what it covered and with which "
            "gates; a pre-v3 receipt cannot. Re-run `tausik verify --task "
            f"{task_slug}` to mint a v3 receipt.",
            run,
        )

    if receipt.get("task_slug") != task_slug or receipt.get("task_slug") != run.get("task_slug"):
        return _no(
            f"verify-handle: receipt is signed for task "
            f"'{receipt.get('task_slug')}' but run #{run_id} says "
            f"'{run.get('task_slug')}' and you are closing '{task_slug}' — "
            "substituted receipt.",
            run,
        )
    if receipt.get("ran_at") != run.get("ran_at"):
        return _no(
            f"verify-handle: receipt ran_at {receipt.get('ran_at')!r} does not "
            f"match run #{run_id} ({run.get('ran_at')!r}) — substituted receipt.",
            run,
        )

    return _check_coverage(run, receipt, task_slug=task_slug, command=command)


def _check_coverage(
    run: dict[str, Any],
    receipt: dict[str, Any],
    *,
    task_slug: str,
    command: str,
) -> HandleVerdict:
    """Re-derive coverage from LIVE state and compare it to the document."""
    from verify_cache import is_cache_allowed, resolve_gate_signature
    from verify_files_hash import compute_files_hash

    run_id = run["id"]
    files = [str(f) for f in (receipt.get("files") or [])]

    # (5) of the task plan: the security predicate is applied to the files the
    # RECEIPT names, not to whatever the caller passed to `task done`. Applying
    # it to the argument was the quiet failure mode — a caller could declare a
    # harmless scope at close time while presenting a receipt that covered
    # auth/. The receipt is the claim, so the receipt is what gets judged.
    if not is_cache_allowed(files):
        return _no(
            f"verify-handle: run #{run_id} covers security-sensitive paths, "
            "which are never certified by a stored result — they are re-verified "
            f"on every close. Run `tausik verify --task {task_slug}` immediately "
            "before `task done`, without --verify-handle.",
            run,
            files,
        )

    live_hash = compute_files_hash(files)
    if live_hash != run.get("files_hash"):
        return _no(
            f"verify-handle: the files this receipt covers have changed since "
            f"verify run #{run_id} (files_hash {str(run.get('files_hash'))[:12]} "
            f"-> {live_hash[:12]}). This is the substantive refusal, not a cache "
            f"miss: re-run `tausik verify --task {task_slug}`.",
            run,
            files,
        )
    if receipt.get("files_hash") != run.get("files_hash"):
        return _no(
            f"verify-handle: receipt files_hash disagrees with run #{run_id}'s "
            "row — the signed document and the recorded run describe different "
            "file sets.",
            run,
            files,
        )

    row_sig = extract_gate_signature(command)
    receipt_sig = str(receipt.get("gate_signature") or "")
    if not row_sig or receipt_sig != row_sig:
        return _no(
            f"verify-handle: receipt gate_signature {receipt_sig!r} does not "
            f"match verify run #{run_id}'s recorded gate set {row_sig!r}.",
            run,
            files,
        )
    live_sig = resolve_gate_signature("verify")
    if receipt_sig != live_sig:
        return _no(
            f"verify-handle: the gate set changed since run #{run_id} "
            f"(signature {receipt_sig} -> {live_sig}). The receipt attests gates "
            "that are no longer the ones configured — re-run "
            f"`tausik verify --task {task_slug}`.",
            run,
            files,
        )

    return _check_git_scope(run, files, task_slug=task_slug, live_sig=live_sig)


def _check_git_scope(
    run: dict[str, Any],
    files: list[str],
    *,
    task_slug: str,
    live_sig: str,
    task_created_at: str | None = None,
) -> HandleVerdict:
    """Compare the receipt's coverage against what git says changed.

    WHY THIS IS HERE AND NOT ONLY AT VERIFY TIME. `run_gates_with_cache` runs
    this comparison when the run is RECORDED, and `_run_quality_gates_report`
    runs it again on the task-done path — but only over the files the CALLER
    declared at close time. A handle carries its own scope, which is the point
    of it, and that opened a gap the freshness lookup did not have: a close
    that declares NO files reaches the handle branch (it is decided before the
    undeclared-scope block, so that the receipt can supply the scope), the
    task-done comparison then measures an empty declared set and reports
    "unknown", and nothing is left to notice that the tree moved past what the
    receipt covered. So the comparison is redone HERE, against the receipt's
    list, which is the set actually being presented as proof.

    The verdict follows Decision #138 exactly, no stricter and no looser:
    divergence alone does NOT block (it fires on nearly every honest close —
    CHANGELOG, docs, generated constants), but an undeclared file that is
    SECURITY-SENSITIVE does, because the scoped gates ran against the receipt's
    list and therefore examined that file with nothing. That is the same narrow
    rule `verify_scope_honesty.security_block_reason` applies on the write side;
    it is called rather than restated so the two cannot drift.
    """
    from verify_scope_honesty import describe_declared_scope, security_block_reason

    run_id = run["id"]
    started = task_created_at
    if started is None:
        started = _task_started_at(run)
    scope_desc = describe_declared_scope(files, started)
    blocked = security_block_reason(scope_desc)
    if blocked:
        return _no(
            f"verify-handle: run #{run_id} — {blocked} The receipt covers "
            f"{len(files)} file(s), but git shows a security-sensitive file "
            "changed that it does not name, so the gates examined that file "
            f"with nothing. Declare it and re-run `tausik verify --task "
            f"{task_slug}`.",
            run,
            files,
        )
    note = ""
    if scope_desc.get("status") == "under-declared":
        # Recorded, not blocked — and SAID, because a divergence the reader
        # never sees is the same as one that was not measured.
        note = (
            f", note: {scope_desc.get('undeclared_count')} file(s) changed "
            "outside this receipt's scope (non-blocking, Decision #138)"
        )
    return HandleVerdict(
        True,
        f"verify-handle: VALID (run #{run_id}, {len(files)} file(s), gates "
        f"{live_sig}, expires {run.get('handle_expires_at')}){note}",
        run,
        files,
    )


def _task_started_at(run: dict[str, Any]) -> str | None:
    """When the work being certified began — the git comparison's left edge.

    Falls back to the run's own `ran_at`, which is later than task start and so
    yields a NARROWER window: it can only miss changes made before the verify,
    never invent ones after it. `describe_declared_scope` returns "unknown"
    when handed None, and unknown does not block, so a missing value degrades
    to the pre-existing behaviour rather than to a false accusation.
    """
    return str(run.get("ran_at") or "") or None


def redeem_handle(
    conn: sqlite3.Connection,
    handle: str | None,
    *,
    task_slug: str,
    project_dir: str = ".",
) -> HandleVerdict:
    """Validate and, on success, spend the handle exactly once.

    The spend is last and its result is authoritative: `check_handle` reports
    an already-spent handle for a good message, but only the atomic UPDATE
    decides. A caller that saw ok=True here may treat QG-2 as satisfied.
    """
    verdict = check_handle(conn, handle, task_slug=task_slug, project_dir=project_dir)
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
