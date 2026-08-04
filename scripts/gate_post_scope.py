"""Run the QG-2 gates that come after the scoped pipeline (gate-registry-single-source).

`run_gates` judges a task's declared files. Two gates cannot: Verify-First asks
whether a fresh signed verify green exists for this task, and the changelog gate
asks whether the project's changelog gained a line. They take the close context
and edit the QG-2 *report* instead of returning ``(passed, output)``.

Those two used to be two hardcoded calls inside `service_gates`, which is why
`gates status` never listed them, `gates enable/disable` never reached them, and
— the one that mattered — they left no `gate_runs` row, so nothing downstream
could prove the QG-2 gate had run at all. The framework asks every task for
evidence and kept none about its own most load-bearing check.

They are ordinary registry entries now, with three consequences this module
implements:

* **Order is declaration order.** Verify-First runs before changelog so both
  blocking reasons aggregate into one report — the agent sees everything to fix
  at once rather than one gate per attempt.
* **`enabled` is honoured, and never silently.** `config_trust` guards
  ``gates.*.enabled``: a repository-travelling `.tausik/config.json` may tighten
  it but not turn a gate off, so the only way to disable one that ships ON is
  the per-machine user tier or `$TAUSIK_MANAGED_CONFIG`. When that happens the
  skip is recorded as a supervision-bypass event and as a skipped `gate_runs`
  row (convention l26-bypass-telemetry) — an opt-out is allowed to exist, not to
  be invisible. Turning OFF a gate that ships off is not a bypass and is not
  reported as one. A config that cannot be read leaves the gate ON: unknown
  policy is not "off", and for the changelog gate a malformed policy block
  deliberately resolves to ON so the gate itself can fail closed on it.
* **Every outcome is persisted.** One `gate_runs` row per gate, with
  ``verification_run_id`` NULL — these gates belong to a close, not to a verify
  run. The rows are committed immediately and independently of whether the close
  then succeeds: a gate that ran and blocked is exactly the event the table
  exists to record, and losing it because the close failed would erase the
  evidence in precisely the cases that matter most.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from gate_registry import PHASE_POST_SCOPE, bound_impl_for, specs_for_phase

_log = logging.getLogger("tausik.gates")

_TRIGGER = "task-done"


def _enabled_map(svc: Any) -> dict[str, bool]:
    """Effective on/off for post-scope gates, read from THIS project's config.

    Resolved through `load_gates`, so it already accounts for the trust tiers
    and for the changelog gate's legacy `task_done.changelog_gate.enabled` key.
    An unreadable config yields an empty map and every gate defaults to ON —
    fail-closed, the same rule `gate_changelog` applies to its own policy.

    A service exposing no project directory takes that same path rather than
    falling back to the ambient config: reading whichever project the process
    stands in would let another repository's `gates` block decide whether THIS
    close is gated (memory #265 / `mcp-config-read-paths`). Unknown scope means
    every gate runs.
    """
    try:
        import os

        from project_config import load_gates
        from project_root import root_from_service

        root = root_from_service(svc)
        if root is None:
            _log.warning("Post-scope gates: no project directory on the service — gates stay ON")
            return {}
        gates = load_gates(tausik_dir=os.path.join(root, ".tausik"))
        return {
            name: bool(g.get("enabled", True))
            for name, g in gates.items()
            if g.get("phase") == PHASE_POST_SCOPE
        }
    except Exception as e:  # noqa: BLE001 — unknown policy is not "off"
        _log.warning(
            "Post-scope gate config unreadable (%s: %s) — gates stay ON", type(e).__name__, e
        )
        return {}


def _record_bypass(svc: Any, slug: str, name: str) -> None:
    """Leave a countable trace that an enabled=false skipped a QG-2 gate."""
    try:
        svc.be.event_add(
            "supervision",
            slug,
            f"bypass_post_scope_gate_{name}",
            f"gates.{name}.enabled=false — post-scope QG-2 gate '{name}' skipped",
        )
    except Exception:  # noqa: BLE001 — best-effort telemetry, never blocks
        pass


def _persist(svc: Any, report: dict[str, Any], slug: str, results: list[dict]) -> None:
    """Write one `gate_runs` row per post-scope gate and commit.

    A failure here blocks the close rather than raising: the report is the
    channel the agent reads, and "the gate ran but its record could not be
    written" has to arrive as a fixable blocking reason, not a traceback out of
    `task_done`. Convention #221 — a check that cannot record its result must
    not report success.
    """
    if not results:
        return
    try:
        from gate_run_record import record_gate_runs

        conn = svc.be._conn
        record_gate_runs(
            conn,
            verification_run_id=None,
            task_slug=slug,
            trigger=_TRIGGER,
            gate_results=results,
        )
        conn.commit()
    except Exception as e:  # noqa: BLE001 — surfaced as a blocking failure below
        from gate_block import _block

        _block(
            report,
            "gate-runs-record",
            f"QG-2: post-scope gates ran but their outcome could not be recorded "
            f"in `gate_runs` ({type(e).__name__}: {e}). A close whose gate evidence "
            f"is missing is indistinguishable afterwards from one that never ran "
            f"the gates — fail-closed.",
            "Run `tausik doctor` (DB schema / migration v39), then retry the close.",
        )


def run_post_scope_gates(
    svc: Any,
    report: dict[str, Any],
    slug: str,
    relevant_files: list[str] | None,
    *,
    no_file_changes: bool = False,
    no_changelog: bool = False,
    verify_handle: str | None = None,
) -> list[dict]:
    """Run every post-scope gate in registry order. Returns the gate results.

    Each implementation is called with the uniform post-scope shape —
    ``(report, slug, relevant_files, *, no_file_changes, no_changelog,
    verify_handle)`` — and uses the parts it needs; Verify-First ignores
    `no_changelog`, the changelog gate ignores the file list and the handle.
    The shape is uniform rather than per-gate precisely so that adding an
    argument is one edit here plus an ignored keyword on the gates that do not
    want it — the alternative, dispatching by signature, makes a gate that
    quietly stops receiving a new argument indistinguishable from one that
    chose to ignore it. Pass/fail is read from the report itself (did
    this gate add a blocking failure?) rather than from a return value, so a
    gate cannot claim an outcome different from the one it recorded.
    """
    report.setdefault("blocking_failures", [])
    enabled = _enabled_map(svc)
    results: list[dict] = []

    for spec in specs_for_phase(PHASE_POST_SCOPE):
        if no_file_changes and spec.skip_on_fileless_close:
            # A fileless close has no scope to gate and, by construction, no
            # changelog diff to find. Declared on the spec, not branched here.
            results.append(_result(spec.name, True, skipped=True, duration_ms=0))
            continue
        if not enabled.get(spec.name, True):
            # Telemetry only for a gate that ships ON and was turned off. An
            # opt-in gate a project never adopted (changelog, by default) is not
            # a bypass, and recording it as one would bury the real bypasses
            # under a supervision event on every close of every project.
            if spec.default_config.get("enabled") is True:
                _record_bypass(svc, slug, spec.name)
            results.append(_result(spec.name, True, skipped=True, duration_ms=0))
            continue

        before = len(report["blocking_failures"])
        start = time.monotonic()
        bound_impl_for(spec, svc)(
            report,
            slug,
            relevant_files,
            no_file_changes=no_file_changes,
            no_changelog=no_changelog,
            verify_handle=verify_handle,
        )
        results.append(
            _result(
                spec.name,
                passed=len(report["blocking_failures"]) == before,
                skipped=False,
                duration_ms=int((time.monotonic() - start) * 1000),
                severity=str(spec.default_config.get("severity") or "block"),
            )
        )

    _persist(svc, report, slug, results)
    return results


def _result(
    name: str,
    passed: bool,
    *,
    skipped: bool,
    duration_ms: int,
    severity: str = "block",
) -> dict[str, Any]:
    return {
        "name": name,
        "severity": severity,
        "passed": passed,
        "skipped": skipped,
        "duration_ms": duration_ms,
    }
