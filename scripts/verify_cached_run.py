"""Cache-aware gate run — the single implementation of "verify this task".

Extracted from `service_verification.py` (which stayed a facade of
re-exports) when `cli-verify-bypasses-cache-guards` collapsed the second,
guard-less write path in `project_cli_verify` into this one and the file
crossed the 400-line filesize gate.

Nothing here may import `service_verification`: that module imports this one
to re-export `run_gates_with_cache`, so the dependency runs one way only.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Callable

# Bound at import time, unlike `run_gates` below. The distinction is the point:
# `run_gates` EXECUTES gates and is what a test legitimately swaps out;
# `summarize_results` only names outcomes and has no reason to be stubbed.
# Several tests replace the entire `gate_runner` module with a MagicMock to
# control `run_gates`, which would otherwise hand this function an auto-stubbed
# formatter and put a MagicMock into the `summary` column. Inject behaviour,
# not formatting.
from gate_runner import summarize_results
from verify_cache import _build_cache_command, is_cache_allowed

# The envelope-timeout machinery moved to `verify_envelope` when this file
# crossed the filesize gate. Re-exported: `service_verification` re-exports
# these three onward, and tests import them by these names.
from verify_envelope import (  # noqa: F401
    DEFAULT_PIPELINE_TIMEOUT_S,
    GateEnvelopeTimeoutError,
    resolve_pipeline_timeout_s,
    run_within_envelope,
)
from verify_constants import DEFAULT_CACHE_TTL_S
from verify_files_hash import compute_files_hash
from verify_recent_lookup import lookup_recent_for_task
from verify_no_test_mapped import handle_no_test_mapped
from verify_run_record import (
    RECORD_FAILED_STATUS,
    VerificationRecordError,
    _record_verification,
    record_failure_result,
)
from verify_scope_honesty import (
    STATUS_UNDER_DECLARED,
    describe_declared_scope,
    security_block_reason,
)


# verify-no-test-mapped-dead-end: the audit query this feature exists to make
# answerable — "which closures rest on no executed gate at all?". Exported as a
# constant so docs, tests and any future report agree on one spelling.
#
# The first cut put the marker in `scope` instead, to avoid a migration. That
# column is CHECK-constrained to the SENAR tiers, so every write raised
# IntegrityError on a real database while passing in tests whose DDL is a
# hand-written copy without the constraint. Hence a column, and hence v40.
AUDIT_NO_TESTS_DECLARED_SQL = (
    "SELECT task_slug, ran_at FROM verification_runs WHERE no_tests_declared = 1"
)


def run_gates_with_cache(
    conn: sqlite3.Connection,
    slug: str,
    relevant_files: list[str] | None,
    *,
    scope: str = "lightweight",
    append_notes_fn: Callable[[str, str], None] | None = None,
    task_created_at: str | None = None,
    progress_fn: Callable[[dict[str, Any]], None] | None = None,
    trigger: str = "task-done",
    details: dict[str, Any] | None = None,
    no_tests_expected: bool = False,
) -> tuple[bool, list[dict[str, Any]], str | None]:
    """SENAR Rule 5 cache-aware gate run.

    Returns (passed, results, cache_status) where:
      passed: bool — final gate verdict (True if cache hit OR fresh green)
      results: gate_runner result list (empty when cache hit)
      cache_status: "hit" / "miss" / "bypass" / "git-mismatch" /
                    "no-test-mapped" / "no-tests-declared" /
                    "scope-security-mismatch" / None

    `no_tests_expected` is the caller declaring, for this run, that the
    declared files are not expected to map to any test — documentation,
    config, migrations. Without it the all-skipped run blocks, as it must;
    with it the run is recorded green with `no_tests_declared=1`. The flag
    buys visibility, not permission: the closure still happens with no
    gate executed, and the point is that this is now countable rather than
    indistinguishable from a verified one.

    `details`, when a dict is passed, is filled with what a presentation layer
    needs and the tuple cannot carry: `run_id` (for receipt lookup),
    `duration_ms`, and `cache_hit` (the reused row). An out-parameter rather
    than a wider return type so the CLI could stop duplicating this function
    without touching its ~30 existing call sites.

    On a cache miss this records the run on green so future calls can hit.
    Security-sensitive file sets bypass the cache (always re-verify).
    `append_notes_fn(slug, msg)` is called once with a one-line summary so
    the caller does not need to know cache details.

    `task_created_at` (v1.3.4): when provided, the cache lookup is also
    gated on the declared-vs-git comparison — if the agent declared a strict
    subset of files actually changed since task start (per `git log --since`
    + `git diff HEAD`), the cache is refused (status "git-mismatch") to
    prevent the bypass where a misreported file scope masks a
    security-sensitive change. None or empty falls back to the pre-v1.3.4
    behavior (security-only bypass).

    l26-verify-git-diff-wire changed what happens to that comparison after
    the cache decision. It used to be discarded; it is now recorded on the
    verification_runs row and signed into the receipt, so a proof states
    whether its own coverage was known to be complete. Divergence still does
    NOT block (Decision #138 — it fires on nearly every honest closure). The
    one exception is an undeclared file that is security-sensitive: the
    scoped gates would run against the declared list and verify it with
    nothing, so that returns "scope-security-mismatch" and fails.

    Concurrency note: two simultaneous `task done` calls for the same slug
    both miss cache, both run gates, both `record_run`. SQLite WAL keeps this
    safe (no corruption); the cost is duplicate `verification_runs` rows and
    redundant gate work. Accepted: blocking with BEGIN IMMEDIATE for the
    full gate-run window would lock the DB for the entire pytest duration,
    which is worse than the duplicate-row cost.
    """
    import time as _time

    # `run_gates` stays a local import ON PURPOSE: it is the injection point,
    # and the suite patches it (both as `gate_runner.run_gates` and, in older
    # tests, by swapping the whole module in `sys.modules`). `summarize_results`
    # is imported at module level instead — see the note beside that import.
    from gate_runner import run_gates

    files = relevant_files or []
    files_hash = compute_files_hash(files)
    cache_command = _build_cache_command(trigger, files)
    cache_ok = is_cache_allowed(files)

    # l26-verify-git-diff-wire: describe the declared scope ALWAYS, not only
    # when the cache is in play. A security-sensitive declared set bypasses the
    # cache (cache_ok=False) — and that is precisely the run where an
    # undeclared file matters most, so computing this under `cache_ok` would
    # blind the receipt in the highest-risk path. Cheap when it cannot apply:
    # describe_declared_scope returns "unknown" without touching git when
    # task_created_at or the declared list is missing.
    scope_desc = describe_declared_scope(files, task_created_at)
    if details is not None:
        details["scope_description"] = scope_desc
    git_diff_consistent = scope_desc["status"] != STATUS_UNDER_DECLARED
    if not git_diff_consistent and append_notes_fn is not None:
        append_notes_fn(
            slug,
            "WARN: declared relevant_files is a strict subset of files "
            "changed since task start (git diff). Cache refused — "
            "running fresh verify to prevent stale-green via misreported scope. "
            f"Undeclared: {', '.join(scope_desc['undeclared'][:10])}"
            f"{' …' if scope_desc['undeclared_count'] > 10 else ''}",
        )

    # The narrow block (Decision #139). Divergence alone is normal and stays
    # non-blocking; an undeclared *security-sensitive* file is not, because the
    # scoped gates below would run against the declared list and verify it with
    # nothing. Refusing the cache never closed this half of the v1.3.4 hole.
    blocked = security_block_reason(scope_desc)
    if blocked:
        if append_notes_fn is not None:
            append_notes_fn(slug, blocked)
        synth = {
            "name": "scope-declaration",
            "passed": False,
            "skipped": False,
            "severity": "block",
            "output": blocked,
        }
        # Record the block. It used to be written only on the CLI path, so the
        # question "how often does the security-scope gate fire?" was
        # answerable for one entry point and not the other — the same
        # observability argument as Decision #146.
        blocked_results = [synth]
        try:
            _record_verification(
                conn,
                slug=slug,
                scope=scope,
                command=f"noncacheable|{cache_command}",
                exit_code=1,
                summary="scope-declaration=FAIL (undeclared security-sensitive files)",
                files_hash=files_hash,
                gate_results=blocked_results,
                scope_desc=scope_desc,
                trigger=trigger,
                details=details,
            )
        except VerificationRecordError as exc:
            # The verdict is already a block, so there is nothing to escalate —
            # returning a *different* block would add no safety. What must not
            # happen is the loss going unmentioned: convention #242 exists
            # because a verdict that stops a closure has to leave a trace, and
            # here the trace failed. Surface it beside the primary reason and
            # keep that reason as the status: "scope-security-mismatch" is why
            # this run stopped, and renaming it would hide the real finding.
            blocked_results = [synth, record_failure_result(exc)]
        return False, blocked_results, "scope-security-mismatch"

    # verify-cache-empty-scope-hit: an undeclared scope is "unknown", not
    # "verified empty" (#226). With `files=[]` the scoped gates are SKIPPED by
    # gate_runner, so the run proves nothing — and `compute_files_hash([])` is a
    # stable empty-marker that no edit moves, so a green recorded against it
    # would stay valid for the whole TTL across arbitrary tree changes. Neither
    # read nor write may treat it as a certificate.
    if files and cache_ok and git_diff_consistent:
        try:
            from project_config import load_config

            ttl = load_config().get("verify_cache_ttl_seconds", DEFAULT_CACHE_TTL_S)
        except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            ttl = DEFAULT_CACHE_TTL_S
        hit = lookup_recent_for_task(
            conn, slug, files_hash=files_hash, command=cache_command, max_age_s=ttl
        )
        if hit is not None:
            if details is not None:
                details["cache_hit"] = hit
            if append_notes_fn is not None:
                append_notes_fn(
                    slug,
                    f"Gates: cache hit (verify run #{hit['id']}, "
                    f"ran_at={hit['ran_at']}, scope={hit['scope']})",
                )
            return True, [], "hit"
        # The relaxed fallback that used to live here (v14-cache-relaxed-
        # mismatch-hit) is gone. It accepted any fresh green row whose recorded
        # command named no files as a certificate for an explicit file set, on
        # the premise that a manual-scope verify was a *broader* pass. The
        # premise was false — with no declared files the scoped gates are
        # skipped, so the row proved nothing about the files it was certifying.
        # It leaked two further ways: the lookup was called WITHOUT a
        # `command_prefix`, so it also matched rows stamped `noncacheable|`
        # (contradicting the guarantee claimed further down this function) and
        # rows from the `task-done` bucket. Removed rather than tightened:
        # under the empty-scope rule above, every branch of it now rejects.

    t0 = _time.monotonic()
    # The wall-time bound lives in `verify_envelope`. `run_gates` is handed to
    # it rather than imported there, so the suite's patching of this local
    # import keeps working.
    passed, results = run_within_envelope(
        run_gates, trigger, relevant_files, progress_fn=progress_fn
    )
    duration_ms = int((_time.monotonic() - t0) * 1000)
    if results and append_notes_fn is not None:
        append_notes_fn(slug, f"Gates: {summarize_results(results)}")
    if not files and any(r.get("skipped") for r in results):
        if append_notes_fn is not None:
            append_notes_fn(
                slug,
                "WARN: no relevant_files passed — scoped gates SKIPPED. "
                "v1.3 removed full-suite fallback. Pass --relevant-files for verification.",
            )
    # v1.3 blind-review pass: If relevant_files was supplied but EVERY gate was skipped (no
    # test mapped, source-without-test), don't pass as green. Report a synthetic
    # blocking failure so QG-2 surfaces the missing tests instead of silently
    # closing the task. This is the "auth/login.py exists, no tests/test_login.py"
    # bypass discovered by the v1.3 blind review.
    # verify-no-test-mapped-dead-end: сам вердикт живёт в verify_no_test_mapped.
    # Здесь остаётся только условие входа — три решения этой ветки (блокировать,
    # записывать блокировку, дать явный выход) слишком велики для тела функции.
    if files and results and all(r.get("skipped") for r in results):
        return handle_no_test_mapped(
            conn,
            slug=slug,
            files=files,
            results=results,
            scope=scope,
            cache_command=cache_command,
            files_hash=files_hash,
            duration_ms=duration_ms,
            scope_desc=scope_desc,
            trigger=trigger,
            details=details,
            no_tests_expected=no_tests_expected,
            append_notes_fn=append_notes_fn,
        )
    # Don't cache an "all-skipped" run as if it were verified — that would
    # let the next caller's gates be silently skipped via cache hit on the
    # same files_hash for 10 minutes. SCOPED-SKIP means "no test mapped" —
    # not "verified clean". Require at least one real (non-skipped) PASS.
    has_real_pass = any(r.get("passed") and not r.get("skipped") for r in results)
    # `files` is part of the condition for the same reason `has_real_pass` is:
    # a green that covered nothing must not be replayable. A scope-independent
    # gate (filesize, hadolint) can pass while the scoped gates are skipped for
    # want of declared files — that combination satisfied `has_real_pass` and
    # got cached under the empty-marker hash, which no subsequent edit moves.
    cacheable = passed and cache_ok and has_real_pass and bool(files)
    # Record whenever gates actually ran — cache eligibility governs *reuse*,
    # not observability. Tying the two together meant a blocking failure from
    # this path was never written down, so "how often does this gate block?"
    # was unanswerable for exactly the runs that matter most.
    #
    # Two independent guards keep a recorded run from being replayed as a
    # green: failures carry exit_code=1, and the cache lookup filters
    # `exit_code = 0` (verify_recent_lookup.py). A run that passed but is not
    # cacheable (all gates skipped, or no declared scope) needs more than that
    # — exit_code would be 0 — so its command gets a `noncacheable|` prefix.
    # Since verify-cache-empty-scope-hit removed the relaxed fallback, the only
    # reader left is the strict lookup, which matches `command` exactly; the
    # prefix is therefore unmatchable by construction. That claim used to be
    # stated here while the relaxed lookup in this very function was called
    # without a `command_prefix` and happily matched prefixed rows — the guard
    # is now as narrow as the comment.
    if details is not None:
        details["duration_ms"] = duration_ms
    # AC6 of verify-record-failure-swallowed: an empty `results` means no gate
    # ran at all, so there is nothing to write and no write to fail. That path
    # is untouched — "nothing to record" is not "failed to record".
    if results:
        summary = summarize_results(results)
        try:
            _record_verification(
                conn,
                slug=slug,
                scope=scope,
                command=cache_command if cacheable else f"noncacheable|{cache_command}",
                exit_code=0 if passed else 1,
                summary=summary,
                files_hash=files_hash,
                duration_ms=duration_ms,
                gate_results=results,
                scope_desc=scope_desc,
                trigger=trigger,
                details=details,
            )
        except VerificationRecordError as exc:
            # The one branch where the fix actually changes a verdict. Gates may
            # have passed, but nothing was written down, so this run proves
            # nothing and can certify nothing. Returning it as green was the
            # defect: `task done` could not tell it apart from a run whose
            # evidence exists.
            return False, [*results, record_failure_result(exc)], RECORD_FAILED_STATUS
    if not cache_ok:
        cache_status = "bypass"
    elif not git_diff_consistent:
        cache_status = "git-mismatch"
    else:
        cache_status = "miss"
    return passed, results, cache_status
