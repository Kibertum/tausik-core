"""The verify report, built ONCE for both surfaces.

`verify` was the last command implemented twice, and the two copies had drifted
in BOTH directions — which is why collapsing it is a union, not a move:

Only the CLI said: how long the run took; the §8.6(e) verdict note when no gate
was actually executed; that the declared scope was NARROWER than the change;
whether the run was recorded at all, including the case where the write failed
and the run therefore certifies nothing; and the receipt line, which tells a
configured-but-failing signing key apart from having no key.

Only the MCP handler said: that some gates SKIPPED — the historical defect this
guards, where the handler returned `gates=['hadolint', 'pytest']`, a list of
NAMES, so an agent read "pytest" and concluded the tests had run when pytest had
skipped; that no `relevant_files` were declared; and that a taskless run is a
full-suite run rather than an under-declared one.

And the cache hit reached only the CLI: the handler printed its header and an
empty gate list, so "this answer came from the cache" looked exactly like "this
run executed nothing" — the same confusion, one layer along.

What stays with each caller is what genuinely belongs to it: argparse and exit
codes in the CLI, the error envelope in the handler. Everything printed is here.

The remediation for the handle is spelled BOTH ways on purpose. An agent reading
CLI output may close through MCP and the other way round, and a renderer that
guessed the caller's transport would be branching on the surface again.
"""

from __future__ import annotations

import os
from typing import Any

from tausik_utils import cli_invocation

#: How to spell the CLI in a remediation the reader's shell will accept.
_CLI = cli_invocation()


def verify_lines(svc: Any, report: dict[str, Any], task_slug: str | None, scope: str) -> list[str]:
    """The whole verify report, one element per line."""
    hit = report.get("cache_hit")
    if hit is not None:
        if not task_slug:
            # The cache is keyed per task; a hit without one means the cache
            # layer changed shape under this caller. Say so instead of reporting
            # a hit for 'None' as though something had been verified.
            return ["internal error: verify cache hit with no --task; caches are per-task only."]
        return cache_hit_lines(svc, task_slug, hit)

    from gate_runner import format_results

    results = report.get("results") or []
    lines = [
        f"Verify (scope={scope}, task={task_slug or '-'}): "
        f"passed={report['passed']} status={report['status']} "
        f"trigger={report['trigger']}",
        format_results(results),
    ]
    duration_ms = report.get("duration_ms")
    if duration_ms is not None:
        lines.append(f"Duration: {duration_ms} ms")
    lines += _skipped_note(results)
    lines += _verdict_note(report, results)
    lines += _scope_notes(report, task_slug)
    lines += _recorded_lines(report, task_slug)
    if task_slug:
        lines += receipt_lines(svc, report.get("run_id"))
        lines += handle_lines(report, task_slug)
    return lines


def cache_hit_lines(svc: Any, task_slug: str, hit: dict[str, Any]) -> list[str]:
    """A hit is an ANSWER, and it says where the answer came from.

    Reaching this from the handler is new. It used to print a header over an
    empty gate list, so a cached green was indistinguishable from a run in which
    nothing executed — the very confusion the skip note exists to prevent.
    """
    try:
        svc.be.event_add(
            "task",
            task_slug,
            "verify_cache_hit",
            f"verify_run_id={hit['id']} scope={hit['scope']}",
        )
    except Exception:  # noqa: BLE001 — best-effort telemetry, never blocks the report
        import logging

        logging.getLogger("tausik.verify").warning(
            "event_add failed for verify_cache_hit", exc_info=True
        )
    return [
        f"Verify cache HIT for '{task_slug}' "
        f"(verify run #{hit['id']}, ran_at={hit['ran_at']}, "
        f"scope={hit['scope']}, exit={hit['exit_code']}). "
        "Skipping gate run."
    ]


def _skipped_note(results: list[dict[str, Any]]) -> list[str]:
    """A SKIP is not a verification, and it must never read as one.

    The handler this replaces once returned a list of gate NAMES, so a skipped
    pytest was indistinguishable from a passed one: on a task with no declared
    scope the only thing that actually executed was a Dockerfile linter, and the
    run was still recorded green and signed.
    """
    skipped = [r.get("name", "?") for r in results if r.get("skipped")]
    if not skipped:
        return []
    return [
        f"NOTE: {', '.join(skipped)} did NOT execute. A SKIP is not a "
        "verification — this run says nothing about what those gates cover."
    ]


def _verdict_note(report: dict[str, Any], results: list[dict[str, Any]]) -> list[str]:
    """SENAR 1.4 §8.6(e) is a property of the VERDICT, not of a sentence beside it."""
    if report.get("status") != "no-tests-declared":
        return []
    from verify_zero_gate import run_state, verdict_note

    return [verdict_note(run_state(results))]


def _scope_notes(report: dict[str, Any], task_slug: str | None) -> list[str]:
    """What the declared scope was, and whether it covered the change."""
    from service_verification import STATUS_UNDER_DECLARED

    lines: list[str] = []
    scope_desc = report.get("scope_description") or {}
    if scope_desc.get("status") == STATUS_UNDER_DECLARED:
        lines.append(
            f"NOTE: {scope_desc['undeclared_count']} file(s) changed since task "
            "start but not declared in relevant_files. The receipt records this "
            "— its coverage is narrower than the change."
        )
    if task_slug and not report.get("relevant_files"):
        lines.append(
            f"NOTE: no relevant_files declared for '{task_slug}', so every scoped "
            f"gate skipped. Declare them (`{_CLI} task update {task_slug} "
            "--relevant-files <paths>`) and re-run, or this green rests on nothing."
        )
    elif task_slug is None:
        # The scoped scolding makes no sense for the WIDEST verification the
        # tool offers: the service returns files=[] by design there, not because
        # a task under-declared, and the old unconditional note named no real task.
        lines.append(
            "NOTE: full-suite run (no task scope). Not recorded to the verify "
            "cache — pass a task slug to cache a scoped green for task_done."
        )
    return lines


def _recorded_lines(report: dict[str, Any], task_slug: str | None) -> list[str]:
    """Whether evidence exists, never the word PASSED beside its absence."""
    from service_verification import RECORD_FAILED_STATUS

    run_id = report.get("run_id")
    if run_id is not None:
        return [
            f"Recorded verification_run #{run_id} "
            f"(task_slug={task_slug or '-'}, exit={'0' if report['passed'] else '1'})."
        ]
    # verify-record-failure-swallowed: this used to be able to print "Verify
    # PASSED — NOT recorded", putting the word PASSED next to the admission that
    # no evidence exists. A failed write now blocks, so `passed` is False here
    # whenever the write was attempted and failed; the message names the loss.
    if report.get("status") == RECORD_FAILED_STATUS:
        return [
            "Verify NOT RECORDED — the gate results could not be written to the "
            "database, so this run certifies nothing. It is reported as FAILED "
            "for that reason, not because a gate failed. See .tausik/tausik.log "
            "for the database error."
        ]
    return [f"Verify {'PASSED' if report['passed'] else 'FAILED'} — NOT recorded."]


def _project_has_key(svc: Any) -> bool:
    """True when this project OPTED INTO signing — key present, loadable or not.

    Presence, not loadability, is the question. Asking `load_public` alone
    conflated two very different states: a project that never ran `key init`
    (benign opt-out) and one whose key file is truncated or corrupted (a real
    failure). Both raised, both read as "no key", so a corrupted key printed the
    reassuring "no project key" line and recorded nothing.
    """
    import crypto_keys
    from project_root import root_from_service

    project_dir = root_from_service(svc)
    if project_dir is None:
        return False  # no project handle → cannot claim a key exists
    keys = crypto_keys.keys_dir(project_dir)
    return os.path.exists(os.path.join(keys, crypto_keys.KEY_FILENAME)) or os.path.exists(
        os.path.join(keys, crypto_keys.PUB_FILENAME)
    )


def receipt_lines(svc: Any, run_id: int | None) -> list[str]:
    """Whether the run produced a signed receipt — and if not, which kind of not.

    A signing FAILURE (a project key exists but the receipt could not be signed)
    used to print the SAME "no project key" line as having no key at all, so a
    project whose signing silently breaks degrades to unsigned runs
    indistinguishably from one that never opted in.
    """
    from verify_receipt_emit import load_receipt

    if run_id is None:
        return ["Receipt: not emitted — the run was not recorded (see .tausik/tausik.log)."]
    stored = load_receipt(svc.be._conn, run_id=run_id)
    if stored is not None:
        signature = stored["envelope"].get("signature") or {}
        return [f"Receipt: signed (run #{run_id}, key {signature.get('key_fingerprint', '?')})."]
    if _project_has_key(svc):
        # Countable metric so the degradation is observable off the interactive
        # path too (best-effort — telemetry must never break the verify report).
        try:
            svc.be.event_add(
                "verify",
                str(run_id),
                "receipt_sign_failed",
                "project key present but receipt emission failed (STATUS_ERROR)",
            )
        except Exception:  # noqa: BLE001 — best-effort telemetry, never blocks
            pass
        return [
            f"Receipt: WARNING — a project key is configured but run #{run_id} was "
            "NOT signed (signing failed). Signed receipts are silently degrading "
            "to unsigned; see .tausik/tausik.log, then inspect `tausik key show`."
        ]
    return ["Receipt: not emitted — no project key (`tausik key init` to enable signed receipts)."]


def handle_lines(report: dict[str, Any], task_slug: str) -> list[str]:
    """The explicit state handle, given to whoever has to decide on it.

    Printing it is not cosmetic — it IS the feature. SEP-2567's point is that
    the identifier is returned to the caller and passed back as an argument; a
    handle minted into the database and never shown would be the same hidden
    server state under a new name. The durability policy travels WITH it: a
    policy that lives only in documentation is not visible to the model at the
    moment the decision is made.
    """
    handle = report.get("verify_handle")
    if not handle:
        # Silence here would read as "handles are off". The run that earns no
        # handle is exactly the run whose green certifies nothing.
        reason = report.get("no_handle_reason")
        if reason:
            from verify_receipt_emit import STATUS_NO_KEY

            # GitLab #15: the run WAS presentable; the receipt is what is
            # missing. Say that, and give the command that will work — never a
            # handle `task done` is bound to refuse.
            why = (
                "no project key, so no signed receipt (`tausik key init` enables them)"
                if reason == STATUS_NO_KEY
                else "the receipt could not be signed (see .tausik/tausik.log, `tausik key show`)"
            )
            return [
                f"Verify handle: none — {why}. Close without --verify-handle: "
                f"`{_CLI} task done {task_slug} --ac-verified` uses the freshness lookup."
            ]
        return [
            "Verify handle: none — this run is not presentable (no declared "
            "files, all gates skipped, or a security-sensitive scope). "
            f"`task done {task_slug}` will fall back to the freshness lookup."
        ]
    return [
        f"Verify handle: {handle}",
        f"  valid until {report.get('handle_expires_at')} (single use). Present it:",
        f"  {_CLI} task done {task_slug} --ac-verified --verify-handle {handle}",
        f"  or pass verify_handle={handle} to tausik_task_done.",
    ]
