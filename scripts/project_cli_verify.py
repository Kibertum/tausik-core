"""SENAR Rule 5 verify CLI handler.

Lives in its own file so project_cli_extra.py stays under the 400-line
filesize gate. The dispatch in project.py imports `cmd_verify` from here.

cli-verify-bypasses-cache-guards: this module used to run its own gate cycle
— `run_gates` + `record_run` called directly — and so carried none of
`run_gates_with_cache`'s guards (`has_real_pass`, the `no-test-mapped` block,
the refusal to cache an empty declared scope). A run in which every gate was
SKIPPED was therefore written as a fully cacheable green, and `task done`
would close on it. It is now a presentation layer over
`GatesMixin.run_verify_for_task`: it decides nothing about what gets recorded.
"""

from __future__ import annotations

import os
from typing import Any


def _emit_cache_hit(svc: Any, task_slug: str, hit: dict[str, Any]) -> None:
    """Print the cache-hit line and log the telemetry event (best-effort)."""
    print(
        f"Verify cache HIT for '{task_slug}' "
        f"(verify run #{hit['id']}, ran_at={hit['ran_at']}, "
        f"scope={hit['scope']}, exit={hit['exit_code']}). "
        "Skipping gate run."
    )
    try:
        svc.be.event_add(
            "task",
            task_slug,
            "verify_cache_hit",
            f"verify_run_id={hit['id']} scope={hit['scope']}",
        )
    except Exception:  # noqa: BLE001 — best-effort: telemetry, non-fatal to the main flow
        import logging

        logging.getLogger("tausik.verify").warning(
            "event_add failed for verify_cache_hit", exc_info=True
        )


def _project_has_key(svc: Any) -> bool:
    """True when this project OPTED INTO signing — key present, loadable or not.

    Presence, not loadability, is the question. Asking `load_public` alone
    conflated two very different states: a project that never ran `key init`
    (benign opt-out) and one whose key file is truncated or corrupted (a real
    failure). Both raised, both read as "no key", so a corrupted key printed
    the reassuring "no project key" line and recorded nothing — reintroducing,
    one layer down, the silent degradation l26-signing-key-boundary exists to
    end. A key file that exists means the project expects signed receipts; if
    it no longer loads, that IS the failure worth reporting.
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


def _emit_receipt(svc: Any, run_id: int | None) -> None:
    """Report whether the run produced a signed receipt.

    l26-signing-key-boundary: a signing FAILURE (a project key exists but the
    receipt could not be signed) previously printed the SAME "no project key"
    line as having no key at all — so a project whose signing silently breaks
    degrades to unsigned runs indistinguishably from one that never opted in.
    The two are now told apart: a present key with no stored receipt is a
    visible WARNING plus a countable `receipt_sign_failed` event, never the
    benign no-key notice.
    """
    from verify_receipt_emit import load_receipt

    if run_id is None:
        print("Receipt: not emitted — the run was not recorded (see .tausik/tausik.log).")
        return
    stored = load_receipt(svc.be._conn, run_id=run_id)
    if stored is not None:
        sig = stored["envelope"].get("signature") or {}
        print(f"Receipt: signed (run #{run_id}, key {sig.get('key_fingerprint', '?')}).")
        return
    # No stored receipt. A configured-but-failing key is silent degradation
    # (the defect this task closes); a genuinely absent key is benign opt-out.
    if _project_has_key(svc):
        print(
            f"Receipt: WARNING — a project key is configured but run #{run_id} was "
            f"NOT signed (signing failed). Signed receipts are silently degrading "
            f"to unsigned; see .tausik/tausik.log, then inspect `tausik key show`."
        )
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
        return
    print("Receipt: not emitted — no project key (`tausik key init` to enable signed receipts).")


def cmd_verify(svc: Any, args: Any) -> None:
    """Scoped per-task verification, recorded in DB.

    With --task: gates are scoped to the task's relevant_files. Without:
    file scope is empty (full suite for pytest) and nothing is cached.

    All gate-running, cache and recording decisions belong to
    `run_verify_for_task` → `run_gates_with_cache`. This function formats.
    """
    from gate_runner import format_results
    from project_service import ServiceError
    from service_verification import RECORD_FAILED_STATUS, STATUS_UNDER_DECLARED

    task_slug = getattr(args, "task", None)
    scope = getattr(args, "scope", "manual")

    try:
        report = svc.run_verify_for_task(
            task_slug,
            scope=scope,
            trigger="verify",
            no_tests_expected=bool(getattr(args, "no_tests_expected", False)),
        )
    except ServiceError as exc:
        print(str(exc))
        raise SystemExit(2) from exc

    hit = report.get("cache_hit")
    if hit is not None:
        _emit_cache_hit(svc, task_slug, hit)
        return

    print(f"Verify (scope={scope}, task={task_slug or '-'}):")
    print(format_results(report["results"]))
    duration_ms = report.get("duration_ms")
    if duration_ms is not None:
        print(f"Duration: {duration_ms} ms")

    if report.get("status") == "no-tests-declared":
        # Do not let this read as an ordinary green. The run passed because the
        # caller said no test was expected, not because one ran.
        print(
            "NOTE: no gate actually executed — you declared --no-tests-expected. "
            "Recorded with no_tests_declared=1; this closure rests on a "
            "declaration, not on a verification."
        )

    scope_desc = report.get("scope_description") or {}
    if scope_desc.get("status") == STATUS_UNDER_DECLARED:
        print(
            f"NOTE: {scope_desc['undeclared_count']} file(s) changed since task "
            f"start but not declared in relevant_files. The receipt records this "
            f"— its coverage is narrower than the change."
        )

    passed = report["passed"]
    run_id = report.get("run_id")
    if run_id is None:
        # verify-record-failure-swallowed: this used to be able to print
        # "Verify PASSED — NOT recorded", putting the word PASSED next to the
        # admission that no evidence exists. A failed write now blocks, so
        # `passed` is False here whenever the write was attempted and failed;
        # the message names the loss instead of reporting a verdict.
        if report.get("status") == RECORD_FAILED_STATUS:
            print(
                "Verify NOT RECORDED — the gate results could not be written to "
                "the database, so this run certifies nothing. It is reported as "
                "FAILED for that reason, not because a gate failed. "
                "See .tausik/tausik.log for the database error."
            )
        else:
            print(f"Verify {'PASSED' if passed else 'FAILED'} — NOT recorded.")
    else:
        print(
            f"Recorded verification_run #{run_id} "
            f"(task_slug={task_slug or '-'}, exit={'0' if passed else '1'})."
        )
    if task_slug:
        _emit_receipt(svc, run_id)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
