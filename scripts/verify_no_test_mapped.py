"""Вердикт «объявленные файлы не мапятся ни на один тест».

verify-no-test-mapped-dead-end. Живёт отдельным модулем, потому что здесь
сошлись три решения, и в теле run_gates_with_cache они тонули:

  * прогон, где НЕ выполнился ни один гейт, блокирует — он ничего не доказывает
    (v1.3 blind review, «auth/login.py есть, tests/test_login.py нет»);
  * блокировка ЗАПИСЫВАЕТСЯ, как и разрешающий прогон, иначе вердикт, который
    останавливает закрытие, не оставляет следа (решение #146, конвенция #242);
  * у документации и конфигов есть ЯВНЫЙ выход, и его использование помечается
    в строке — no_tests_declared=1, аудит одним запросом.

Модуль ничего не импортирует из verify_cached_run: зависимость односторонняя.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Callable

from gate_runner import summarize_results

from verify_zero_gate import ACK_FLAG, APPLICABLE_DID_NOT_RUN, run_state, verdict_note
from verify_run_record import (
    RECORD_FAILED_STATUS,
    VerificationRecordError,
    _record_verification,
    record_failure_result,
)


def handle_no_test_mapped(
    conn: sqlite3.Connection,
    *,
    slug: str,
    files: list[str],
    results: list[dict[str, Any]],
    scope: str,
    cache_command: str,
    files_hash: str,
    duration_ms: int,
    scope_desc: dict[str, Any],
    trigger: str,
    details: dict[str, Any] | None,
    no_tests_expected: bool,
    append_notes_fn: Callable[[str, str], None] | None,
    after_zero_gate_reset: bool = False,
) -> tuple[bool, list[dict[str, Any]], str]:
    """Вернуть вердикт для прогона, в котором все гейты пропущены.

    Вызывается ТОЛЬКО когда files непусты, results непусты и каждый результат
    помечен skipped — проверку этого условия делает вызывающий.
    """
    # verify-no-test-mapped-dead-end: closing the CLI's bypass turned this
    # branch into a dead end for a whole class of work — a documentation or
    # config task maps to no test, so it blocked with no way out. The way
    # out is DECLARED, never inferred: no extension allowlist, because that
    # would restore exactly the invisibility the parent task removed. The
    # run is recorded with no_tests_declared=1 so "every closure that passed
    # without a single gate executing" is one SQL query.
    # AC6: a gate that was APPLICABLE and still did not execute is not the same
    # event as a gate that had nothing to look at, and `--no-tests-expected`
    # must not launder the first into the second. `GateOutcome` already spells
    # the difference; collapsing them here would put back the very
    # indistinguishability `gate_outcome` was extracted to end.
    state = run_state(results)
    if no_tests_expected and state == APPLICABLE_DID_NOT_RUN:
        if append_notes_fn is not None:
            append_notes_fn(
                slug,
                "FAIL: a gate APPLIED and produced no evidence (COULD_NOT_RUN). "
                "--no-tests-expected declares that no test was expected; it "
                "cannot declare away a gate that was expected and did not run.",
            )
        synth_cannot_run = {
            "name": "scoped-pytest",
            "passed": False,
            "skipped": False,
            "severity": "block",
            "output": verdict_note(state),
        }
        return False, [*results, synth_cannot_run], "gate-could-not-run"
    if no_tests_expected:
        if append_notes_fn is not None:
            append_notes_fn(
                slug,
                f"Gates: no test maps to {files}, and the caller declared "
                "none was expected. Recorded with no_tests_declared=1 — "
                "this closure has no executed gate behind it and is "
                "auditable as such.",
            )
        try:
            _record_verification(
                conn,
                slug=slug,
                scope=scope,
                command=cache_command,
                exit_code=0,
                summary=summarize_results(results),
                files_hash=files_hash,
                duration_ms=duration_ms,
                gate_results=results,
                scope_desc=scope_desc,
                trigger=trigger,
                details=details,
                no_tests_declared=True,
            )
        except VerificationRecordError as exc:
            # This branch is greener than any other in the file, and it rests
            # ENTIRELY on the write: no gate executed, so `no_tests_declared=1`
            # on the row is the only thing that makes the closure auditable.
            # Without the row the closure rests on nothing at all — neither an
            # executed gate nor a countable declaration. So here the record
            # failure does flip the verdict (verify-record-failure-swallowed).
            return False, [*results, record_failure_result(exc)], RECORD_FAILED_STATUS
        return True, results, "no-tests-declared"
    # review-209-third-door: told twice, differently. The generic advice is
    # "re-run verify with --no-tests-expected" — which is exactly what the
    # closer ALREADY did when the cached row was written. Repeating it after
    # the zero-gate guard reset that row sends them round a loop they cannot
    # win: the missing act is on the CLOSING side, not the verify side. So the
    # remedy names the flag that is actually absent.
    remedy = (
        "This scope was already declared --no-tests-expected; the cached run "
        "was set aside because it executed no gate. The missing step is on the "
        f"closing side: `task done ... {ACK_FLAG}`."
        if after_zero_gate_reset
        else "Add tests/test_<basename>.py, or re-run verify with "
        "--no-tests-expected to declare that none should exist."
    )
    if append_notes_fn is not None:
        append_notes_fn(
            slug,
            f"FAIL: relevant_files {files} mapped to NO test files. {remedy}",
        )
    synth = {
        "name": "scoped-pytest",
        "passed": False,
        "skipped": False,
        "severity": "block",
        "output": f"No tests mapped for {files}. {remedy}",
    }
    # Same reason the security block above records: this branch returned
    # without writing anything, so the one verdict that stops a closure
    # left no trace at all — while the *unblocked* runs beside it were
    # written down. Decision #146: observability is not cache eligibility.
    # The skipped gates are kept alongside the synthetic failure, because
    # "every gate skipped" is the evidence for the verdict.
    blocked_results = [*results, synth]
    returned = [synth]
    try:
        _record_verification(
            conn,
            slug=slug,
            scope=scope,
            command=f"noncacheable|{cache_command}",
            exit_code=1,
            summary=summarize_results(blocked_results),
            files_hash=files_hash,
            duration_ms=duration_ms,
            gate_results=blocked_results,
            scope_desc=scope_desc,
            trigger=trigger,
            details=details,
        )
    except VerificationRecordError as exc:
        # Already blocking, so no verdict to escalate — but #242 says the
        # verdict that stops a closure must leave a trace, and that is exactly
        # what just failed. Report the loss beside the primary reason and keep
        # "no-test-mapped" as the status: that is why the run stopped, and
        # renaming it would hide the finding the caller has to act on.
        returned = [synth, record_failure_result(exc)]
    return False, returned, "no-test-mapped"
