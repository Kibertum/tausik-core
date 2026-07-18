"""SENAR verification cache: record + lookup verify runs to skip redundant gates.

Per SENAR Rule 5 (Verification Checklist tiers), per-task verification should
be scoped — not a full-suite re-run. To avoid wasted cycles, every successful
gate run is recorded with a stable hash of the relevant files. On subsequent
`task done` calls within the freshness window, if the same files have not
changed, the cached result is reused.

Stack-agnostic: the cache layer doesn't know about pytest/cargo/etc. — it
records `(command, exit_code)` and trusts the caller to recompute the right
hash for the file set being verified.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Callable

# v1.3.4 git-diff cross-check lives in its own module for filesize compliance;
# re-export so existing callers keep working with `service_verification.X`.
from verify_git_diff import (  # noqa: F401
    changed_files_since,
    is_declared_consistent_with_git_diff,
)

# l26-verify-git-diff-wire: tri-state scope description + the narrow
# security-only block. Kept in its own module for filesize compliance.
from verify_scope_honesty import (  # noqa: F401
    STATUS_UNDER_DECLARED,
    describe_declared_scope,
    security_block_reason,
)

# Single source of truth for the verify-cache TTL; re-exported here so callers
# (e.g. service_gates) keep importing `service_verification.DEFAULT_CACHE_TTL_S`.
from verify_constants import DEFAULT_CACHE_TTL_S  # noqa: F401

# v14-verify-pipeline-envelope-timeout: wall-time envelope for the entire
# `run_gates` cycle (NOT per-gate). Guards against a misconfigured / hanging
# gate making `task done` look like the agent froze. Default 60s suits
# interactive MCP hosts; CI can disable via `verify_pipeline_timeout_seconds=0`.
DEFAULT_PIPELINE_TIMEOUT_S = 60


class GateEnvelopeTimeoutError(RuntimeError):
    """Raised when `run_gates` exceeds the verify pipeline envelope timeout.

    Surfaces a remediation hint (raise the limit, opt into auto_verify, or
    narrow `relevant_files`) so an interactive agent can recover deliberately
    instead of guessing whether the host hung.
    """


def resolve_pipeline_timeout_s(cfg: dict | None) -> int:
    """Resolve `verify_pipeline_timeout_seconds` from config.

    Returns the configured value when ≥0; `DEFAULT_PIPELINE_TIMEOUT_S` when
    missing or invalid; `0` is a valid disable-sentinel and is preserved.
    """
    if not isinstance(cfg, dict):
        return DEFAULT_PIPELINE_TIMEOUT_S
    raw = cfg.get("verify_pipeline_timeout_seconds", DEFAULT_PIPELINE_TIMEOUT_S)
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PIPELINE_TIMEOUT_S
    return max(0, v)


# v14b-filesize-debt-paydown: security pattern definitions + is_security_sensitive
# moved to security_pattern.py for filesize compliance. Re-exported below so
# existing callers (service_gates, tests/*) keep working unchanged.
from security_pattern import (  # noqa: F401, E402
    _SEC_BASE,
    _SEC_EXT,
    _SECURITY_BASENAMES,
    _SECURITY_EXTENSIONS,
    _SECURITY_PATH_TOKENS,
    is_security_sensitive,
)


# v1.3.4: compute_files_hash extracted to verify_files_hash.py for filesize
# compliance. Re-exported so existing callers don't need to change.
from verify_files_hash import (  # noqa: F401, E402
    _FILES_HASH_CONTENT_SAMPLE_BYTES,
    compute_files_hash,
)
from verify_recent_lookup import lookup_recent_for_task  # noqa: E402


# is_security_sensitive moved to security_pattern.py — re-exported above.


# l26-verify-git-diff-wire: record_run + _utcnow_iso extracted to
# verify_run_record.py for filesize compliance when the declared-scope
# columns were added. Re-exported so every existing caller keeps working.
from verify_run_record import _utcnow_iso, record_run  # noqa: F401, E402


# v14b-filesize-debt-paydown: cache helpers (is_cache_allowed,
# resolve_gate_signature, _build_cache_command, has_fresh_verify_run) moved to
# verify_cache.py. Re-exported here so all existing callers (service_gates,
# service_task, tests/*) continue importing them from service_verification.
from verify_cache import (  # noqa: F401, E402
    _build_cache_command,
    has_fresh_verify_run,
    is_cache_allowed,
    resolve_gate_signature,
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
) -> tuple[bool, list[dict[str, Any]], str | None]:
    """SENAR Rule 5 cache-aware gate run.

    Returns (passed, results, cache_status) where:
      passed: bool — final gate verdict (True if cache hit OR fresh green)
      results: gate_runner result list (empty when cache hit)
      cache_status: "hit" / "miss" / "bypass" / "git-mismatch" /
                    "no-test-mapped" / "scope-security-mismatch" / None

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
        return False, [synth], "scope-security-mismatch"

    if cache_ok and git_diff_consistent:
        try:
            from project_config import load_config

            ttl = load_config().get("verify_cache_ttl_seconds", DEFAULT_CACHE_TTL_S)
        except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            ttl = DEFAULT_CACHE_TTL_S
        hit = lookup_recent_for_task(
            conn, slug, files_hash=files_hash, command=cache_command, max_age_s=ttl
        )
        if hit is not None:
            if append_notes_fn is not None:
                append_notes_fn(
                    slug,
                    f"Gates: cache hit (verify run #{hit['id']}, "
                    f"ran_at={hit['ran_at']}, scope={hit['scope']})",
                )
            return True, [], "hit"
        # v14-cache-relaxed-mismatch-hit: a strict miss is acceptable for the
        # specific Sharp edge where verify ran with `files=[]` (manual scope —
        # user explicitly verified *this slug* without naming files) and
        # task_done arrives with explicit `relevant_files`. Accept the
        # broad-pass row in *that direction only*. Verify rows that named
        # specific files must keep their strict hash check so mtime / gate
        # signature invalidation continues to work.
        from verify_recent_lookup import (
            _extract_files_from_cache_command,
            lookup_any_fresh_run_for_task,
        )

        relaxed = lookup_any_fresh_run_for_task(conn, slug, max_age_s=ttl)
        if relaxed is not None:
            relaxed_files = _extract_files_from_cache_command(relaxed.get("command", "") or "")
            if not relaxed_files:
                if append_notes_fn is not None:
                    append_notes_fn(
                        slug,
                        f"Gates: cache hit (relaxed — verify run #{relaxed['id']} "
                        f"recorded with files=[] (manual scope), "
                        f"ran_at={relaxed['ran_at']}, scope={relaxed['scope']})",
                    )
                return True, [], "hit"

    t0 = _time.monotonic()
    # v14-verify-pipeline-envelope-timeout: enforce wall-time bound around
    # the whole gate cycle so a hung gate can't make `task done` look frozen.
    try:
        from project_config import load_config as _load_envelope_cfg

        envelope_s = resolve_pipeline_timeout_s(_load_envelope_cfg())
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        envelope_s = DEFAULT_PIPELINE_TIMEOUT_S
    if envelope_s <= 0:
        passed, results = run_gates(trigger, relevant_files, progress_callback=progress_fn)
    else:
        # daemon thread + join(timeout): ThreadPoolExecutor.__exit__ waits for
        # in-flight workers, which would block the abort path. A daemon thread
        # leaves the lingering subprocess unwound at interpreter exit instead.
        import threading as _threading

        _result: dict[str, Any] = {}
        _exc: dict[str, BaseException] = {}

        def _runner() -> None:
            try:
                _result["v"] = run_gates(trigger, relevant_files, progress_callback=progress_fn)
            except BaseException as _e:  # noqa: BLE001
                _exc["e"] = _e

        _t = _threading.Thread(target=_runner, daemon=True)
        _t.start()
        _t.join(envelope_s)
        if _t.is_alive():
            raise GateEnvelopeTimeoutError(
                f"verify pipeline exceeded {envelope_s}s envelope timeout. "
                "Options: raise `verify_pipeline_timeout_seconds` in "
                ".tausik/config.json, set `task_done.auto_verify=true` "
                "to run gates inline (legacy), or narrow `relevant_files` "
                "to reduce gate fan-out."
            )
        if "e" in _exc:
            raise _exc["e"]
        passed, results = _result["v"]
    duration_ms = int((_time.monotonic() - t0) * 1000)
    if results and append_notes_fn is not None:
        summary = ", ".join(r["name"] + "=" + ("PASS" if r["passed"] else "FAIL") for r in results)
        append_notes_fn(slug, f"Gates: {summary}")
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
    if files and results and all(r.get("skipped") for r in results):
        if append_notes_fn is not None:
            append_notes_fn(
                slug,
                f"FAIL: relevant_files {files} mapped to NO test files. "
                "Add tests/test_<basename>.py or pass --no-knowledge if intentional.",
            )
        synth = {
            "name": "scoped-pytest",
            "passed": False,
            "skipped": False,
            "severity": "block",
            "output": f"No tests mapped for {files}",
        }
        return False, [synth], "no-test-mapped"
    # Don't cache an "all-skipped" run as if it were verified — that would
    # let the next caller's gates be silently skipped via cache hit on the
    # same files_hash for 10 minutes. SCOPED-SKIP means "no test mapped" —
    # not "verified clean". Require at least one real (non-skipped) PASS.
    has_real_pass = any(r.get("passed") and not r.get("skipped") for r in results)
    if passed and cache_ok and has_real_pass:
        try:
            summary = (
                ", ".join(r["name"] + "=" + ("PASS" if r["passed"] else "FAIL") for r in results)
                or "ok"
            )
            record_run(
                conn,
                task_slug=slug,
                scope=scope,
                command=cache_command,
                exit_code=0,
                summary=summary,
                files_hash=files_hash,
                duration_ms=duration_ms,
                gate_results=results,
                scope_description=scope_desc,
            )
        except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            import logging

            logging.getLogger("tausik.gates").warning(
                "Failed to record verification run for %s", slug, exc_info=True
            )
    if not cache_ok:
        cache_status = "bypass"
    elif not git_diff_consistent:
        cache_status = "git-mismatch"
    else:
        cache_status = "miss"
    return passed, results, cache_status
