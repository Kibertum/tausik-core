"""Verify-First Contract enforcement (QG-2) — extracted from `service_gates`.

Same split as `gate_qg0_check` / `gate_ac_check`: the policy is a free
function, the mixin keeps only the thin delegation. Extracted when
verify-cache-empty-scope-hit pushed `service_gates.py` past the 400-line
filesize gate — the alternative was an exemption entry, which would have
silenced the gate rather than answered it.

Takes the service (`svc`), not its backend, so `svc.be` is resolved only where
it is actually used. The config-load path fails closed and returns before any
backend access, and callers may legitimately pass a service with no backend
wired — `test_config_trust` constructs a bare mixin to assert exactly that
fail-closed return. Passing `self.be` at the call site turned that guarantee
into an AttributeError; the extraction has to keep the access as lazy as the
original method had it.
"""

from __future__ import annotations

import os
from typing import Any

from gate_block import _block, extract_files_from_gate_output


def _enforce_no_file_changes(
    svc: Any,
    report: dict[str, Any],
    slug: str,
    relevant_files: list[str] | None,
) -> None:
    """Prove — via git, not the agent's word — that the declared scope has no
    uncommitted changes, for a `task done --no-file-changes` close.

    Clean scope → allowed; the countable record is left for _task_done_report
    to write in the status=done transaction. Dirty scope, unavailable git, or a
    service with no project directory → blocked, fail-closed: a declaration git
    cannot back must never close a task (verify_scope_honesty tri-state).
    """
    from verify_git_diff import uncommitted_changes

    tausik_dir = getattr(svc, "tausik_dir", None)
    if not callable(tausik_dir):
        # Fail-closed: with no way to resolve which project this service speaks
        # for, falling back to cwd would git-check whatever repo the process
        # happens to stand in — the read-path defect mcp-config-read-paths, in a
        # gate. A close we cannot scope to the right tree does not proceed.
        _block(
            report,
            "verify-first",
            f"QG-2: task '{slug}' declares --no-file-changes, but this service "
            f"exposes no project directory to scope the git check to. Cannot "
            f"prove an empty scope — fail-closed.",
            f".tausik/tausik task done {slug} --ac-verified --relevant-files <paths...>",
        )
        return
    root = os.path.dirname(tausik_dir())
    dirty = uncommitted_changes(relevant_files, root=root)
    scope_desc = (
        "declared paths " + ", ".join(relevant_files) if relevant_files else "the working tree"
    )
    remediation = f".tausik/tausik task done {slug} --ac-verified --relevant-files <paths...>"
    if dirty is None:
        _block(
            report,
            "verify-first",
            f"QG-2: task '{slug}' declares --no-file-changes, but git could not "
            f"verify it (not a repo, git missing, or the call failed). An "
            f"unprovable empty scope is 'unknown', not 'verified empty' — "
            f"fail-closed. Fix git, or declare the files this task touched.",
            remediation,
        )
        return
    if dirty:
        shown = ", ".join(dirty[:10])
        more = "" if len(dirty) <= 10 else f" (+{len(dirty) - 10} more)"
        _block(
            report,
            "verify-first",
            f"QG-2: task '{slug}' declares --no-file-changes, but git reports "
            f"uncommitted changes in {scope_desc}: {shown}{more}. Either these "
            f"files ARE this task's work — declare them and drop the flag — or "
            f"they are earlier uncommitted work: commit/stash it, then close.",
            remediation,
        )
        return
    # Clean scope — the declaration is backed by git. Allow the close; the
    # countable record (tasks.no_file_changes_declared) is written by
    # _task_done_report inside the status=done transaction, so a later blocking
    # stage cannot leave the flag set on a task that never closed.
    svc.be.task_append_notes(
        slug,
        f"Verify-First: --no-file-changes verified — git scope clean "
        f"({scope_desc}), no gates run (nothing to gate).",
    )


def enforce_verify_first(
    svc: Any,
    report: dict[str, Any],
    slug: str,
    relevant_files: list[str] | None,
    *,
    no_file_changes: bool = False,
) -> None:
    """Add a synthetic blocking_failure if no fresh `tausik verify` run
    exists for this task and the project has verify-trigger gates.

    Three opt-out paths:
      - config.task_done.auto_verify = true  →  legacy inline behavior;
        in that case we run the verify-trigger gates inline right here.
      - No verify-trigger gates configured (small projects, no pytest
        etc.) →  nothing to wait on, skip enforcement.
      - Security-sensitive files →  cache always refused, but we still
        require an explicit verify run; the agent must call `tausik
        verify` immediately before `task done` to avoid stale greens.

    `no_file_changes` (qg2-cannot-close-fileless-task) selects the THIRD
    scope state: the caller declares this task touched no files. Unlike the
    two states this contract had — declared and undeclared — this one is
    provable, and the proof is git's, not the agent's word: the declared
    scope (relevant_files as a pathspec, or the whole tree when empty) must
    have NO uncommitted changes. A dirty scope or an unavailable git blocks,
    fail-closed. This is symmetric to how no_tests_declared closes a run with
    no gate executed — here we close with no scope to gate.
    """
    from service_verification import (
        DEFAULT_CACHE_TTL_S,
        has_fresh_verify_run,
        run_gates_with_cache,
    )

    try:
        from project_config import get_gates_for_trigger, load_config

        cfg = load_config()
        verify_gates = get_gates_for_trigger("verify", cfg)
    except Exception as e:  # noqa: BLE001 — turned into a blocking failure below
        # FAIL CLOSED. Swallowing this into `verify_gates = []` reads as
        # "no verify gates configured", so one malformed `gates` entry
        # skipped the whole Verify-First Contract in silence.
        _block(
            report,
            "config-load",
            f"{type(e).__name__}: {e}",
            "Verify-First cannot tell which gates to enforce: the config failed "
            "to load. Fix `.tausik/config.json` (`tausik doctor` names the key), "
            "then retry.",
        )
        return

    # qg2-cannot-close-fileless-task: the third scope state. Decided ahead of
    # every other branch INCLUDING the no-verify-gates early return below —
    # otherwise a project with no verify-trigger gates would skip the git proof
    # entirely and `--no-file-changes` would close on a dirty tree, recording a
    # `no_file_changes_declared=1` flag that git never backed (fail-open found by
    # review, defect-fileless-close-fail-open-no-verify-gates). The declaration
    # never closes on its own; git has to back it, gates configured or not.
    if no_file_changes:
        _enforce_no_file_changes(svc, report, slug, relevant_files)
        return

    if not verify_gates:
        return  # no heavy gates configured, nothing to enforce

    # `.get(key, {})` yields None when the key is present and explicitly
    # null — the default never applies. Type-check the value, not `cfg`.
    td_raw = cfg.get("task_done")
    td_cfg = td_raw if isinstance(td_raw, dict) else {}
    auto_verify = bool(td_cfg.get("auto_verify", False))
    ttl = int(
        cfg.get("verify_cache_ttl_seconds", DEFAULT_CACHE_TTL_S)
        if isinstance(cfg, dict)
        else DEFAULT_CACHE_TTL_S
    )

    # verify-cache-empty-scope-hit: an undeclared scope cannot be certified
    # by anything, so decide it here — ahead of both the cache lookup and
    # the auto_verify branch. Placing it after auto_verify would leave the
    # hole intact behind a config flag: that path runs the gates inline,
    # `gate_runner` skips the scoped ones for want of declared files, and a
    # scope-independent gate going green would close the task on a run that
    # examined nothing. `.tausik/config.json` travels with the repository,
    # so "legacy opt-out" is not a safe place to keep a bypass.
    #
    # It also has to be its own message. The generic block below tells the
    # agent to run `tausik verify` — advice that can never succeed while the
    # scope is undeclared, because no verify run for an empty scope is
    # accepted. A misleading red is cheaper than the silent green it
    # replaced, but it is still a failure.
    if not relevant_files:
        _block(
            report,
            "verify-first",
            f"QG-2: task '{slug}' declares no relevant_files, so no verify run "
            f"can certify it. With an empty scope the scoped gates are SKIPPED "
            f"(gate_runner), and the resulting green is recorded as "
            f"non-cacheable — an undeclared scope is 'unknown', not 'verified "
            f"empty'. Declare the files this task touched, then verify.",
            f".tausik/tausik task update {slug} --relevant-files <paths...>  &&  "
            f".tausik/tausik verify --task {slug}  &&  "
            f".tausik/tausik task done {slug} --ac-verified",
        )
        return

    fresh, hit = has_fresh_verify_run(svc.be._conn, slug, relevant_files, max_age_s=ttl)
    if fresh and hit is not None:
        # v15-receipt-check-on-done: a cached green only counts if its
        # signed receipt still verifies — tamper-evidence for QG-2.
        from verify_receipt_check import check_receipt_for_hit

        ok, note = check_receipt_for_hit(svc.be._conn, hit["id"], slug)
        svc.be.task_append_notes(
            slug,
            f"Verify-First: cache hit (verify run #{hit['id']} at {hit['ran_at']}) | {note}",
        )
        if not ok:
            _block(
                report,
                "receipt-signature",
                note,
                f"Re-run `tausik verify --task {slug}` to record a freshly "
                f"signed receipt; inspect `tausik receipt show --run "
                f"{hit['id']}` and `tausik key show` if it persists.",
            )
        return

    if auto_verify:
        # Legacy CI-style behavior: run the verify trigger inline.
        svc.be.task_append_notes(
            slug,
            "Verify-First: auto_verify=true — running verify gates inline "
            "(legacy behavior; task_done will block until they finish).",
        )
        # l26-bypass-telemetry: auto_verify weakens Verify-First (no signed
        # cached receipt required) — leave a trace so the bypass is countable.
        # Best-effort: a telemetry write failure must never crash task_done
        # (AC5 fail-open) — event_add/_ins do no exception handling of their own.
        try:
            svc.be.event_add(
                "supervision",
                slug,
                "bypass_auto_verify",
                "auto_verify=true — Verify-First cached-receipt requirement bypassed (inline gates)",
            )
        except Exception:  # noqa: BLE001 — best-effort telemetry, never blocks
            pass
        try:
            passed, results, _status = run_gates_with_cache(
                svc.be._conn,
                slug,
                relevant_files,
                scope=report.get("scope") or "standard",
                append_notes_fn=svc.be.task_append_notes,
                trigger="verify",
            )
        except Exception as e:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            _block(
                report,
                "verify-first",
                f"auto_verify run crashed: {e}",
                "Fix the failing verify gate or set "
                "config.task_done.auto_verify=false and run `tausik verify` "
                "manually.",
            )
            return
        if not passed:
            report["passed"] = False
            blocking = [r for r in results if not r.get("passed") and r.get("severity") == "block"]
            report["blocking_failures"].extend(
                {
                    "gate": r.get("name"),
                    "files": extract_files_from_gate_output(r.get("output", "")),
                    "output": r.get("output", ""),
                    "remediation": (
                        "Fix gate issues and rerun task_done. (auto_verify=true caused inline run.)"
                    ),
                }
                for r in blocking
            )
        return

    # Default v1.4 behavior: refuse to close.
    gate_names = ", ".join(g.get("name", "?") for g in verify_gates)
    _block(
        report,
        "verify-first",
        f"QG-2: no fresh `tausik verify` run for this task "
        f"(verify gates configured: {gate_names}). "
        f"Run `tausik verify --task {slug}` first — it caches; "
        f"then `task done` closes in milliseconds. To opt out "
        f"set config.task_done.auto_verify=true (legacy).",
        f".tausik/tausik verify --task {slug}  &&  .tausik/tausik task done {slug} --ac-verified",
        files=relevant_files,
    )
