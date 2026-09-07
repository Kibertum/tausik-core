"""The three things a presented verify handle must survive, one per function.

Split out of `verify_handle_check` while it still had four lines of headroom,
which is the whole point of the timing: a split made under the file-size gate
happens at the worst possible moment — the change is already written, the tests
are already green, and the only thing anyone wants is the lines back. That is
how a neighbouring module lost an explanation to fit, with the decision made on
the remainder rather than on the merits.

THE SEAM IS THE QUESTION EACH ONE ANSWERS, not an arbitrary cut:

  * `_check_receipt` reads the SIGNED DOCUMENT — does it parse, does the
    signature verify, does it belong to this task and this command.
  * `_check_coverage` re-derives coverage from LIVE state and compares it to
    what the document claims, because a handle that only checked the receipt
    against itself would certify a stale tree perfectly.
  * `_check_git_scope` asks git what actually changed and compares that to the
    coverage the receipt asserts.

`verify_handle_check` keeps what orchestrates them and what SPENDS the handle;
the ordering, the refusal policy and the redemption are its business, and the
rules are these. `_no` lives here because every refusal below is built with it.

Fail-closed, like the module it came from: every check refuses on doubt.
"""

from __future__ import annotations

from typing import Any

from verify_handle import HandleVerdict
from verify_recent_lookup import extract_gate_signature

def _no(
    reason: str,
    run: dict[str, Any] | None = None,
    files: list[str] | None = None,
) -> HandleVerdict:
    """A refusal. `files` is carried on the coverage refusals so a caller can
    report WHAT the receipt claimed to cover alongside why it was rejected."""
    return HandleVerdict(False, reason, run, files)


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
    from verify_own_export import coverage_files, declares_own_export, own_export_display

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

    # verify-handle-dies-on-a-tasks-own-export-file: the REDEMPTION half of the
    # subtraction, and it must mirror `verify_cached_run`'s write half exactly —
    # a receipt whose two sides hashed different sets would refuse for a reason
    # neither the tree nor the agent could act on.
    own_export_declared = declares_own_export(files, task_slug)
    own_export_path = own_export_display(task_slug) or f"{task_slug}.md"
    coverage = coverage_files(files, task_slug)
    if files and not coverage:
        return _no(
            f"verify-handle: run #{run_id} declared nothing but this task's own "
            f"export ({own_export_path}), which is subtracted from "
            "coverage because every verify run rewrites it — so the receipt "
            "covers no file at all and certifies nothing. Declare the files the "
            f"task actually changed: `tausik verify --task {task_slug} "
            "--relevant-files <paths...>`. If the task genuinely changed no "
            "source, close it with `--no-file-changes` instead of a handle.",
            run,
            files,
        )
    live_hash = compute_files_hash(coverage)
    if live_hash != run.get("files_hash"):
        return _no(
            f"verify-handle: the files this receipt covers have changed since "
            f"verify run #{run_id} (files_hash {str(run.get('files_hash'))[:12]} "
            f"-> {live_hash[:12]}). This is the substantive refusal, not a cache "
            f"miss: re-run `tausik verify --task {task_slug}`."
            + (
                # #409, closing clause: a mixed scope's refusal must name the
                # SOURCE and not the journal. The task's own export is already
                # out of the coverage, so saying so stops the reader re-running
                # verify against a file that could not have caused this.
                f" (This task's own export {own_export_path} is NOT part of the "
                "coverage and is not what moved — a declared source file "
                "changed.)"
                if own_export_declared
                else ""
            ),
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
    # `task_slug` for Decision #283: the run being redeemed wrote this task's
    # own export, and the redemption must subtract exactly what the recording
    # side subtracted or the two halves of one proof would disagree.
    scope_desc = describe_declared_scope(files, started, task_slug=task_slug)
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
