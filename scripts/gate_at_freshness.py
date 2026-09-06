"""AT freshness gate — warn-severity, RENAR §8A property 2.

Read-only: opens its own short-lived connection to the project DB (same
pattern as gate_renar_drift.py) and never writes. Warn-only — a stale AT
never blocks; a DB/import failure degrades to COULD_NOT_RUN so a gate bug
cannot wedge task-done. ``files`` is ignored by design: this scans the AT
artifact store against the live final-TZ, not the task's changed files.
"""

from __future__ import annotations

import os

import gate_outcome


def run_at_freshness_gate(gate: dict, files: list[str]) -> gate_outcome.GateOutcome:
    """Registry-uniform ``(gate, files)`` entrypoint."""
    try:
        from project_backend import SQLiteBackend  # noqa: PLC0415
        from project_config import get_db_path  # noqa: PLC0415
        from project_service import ProjectService  # noqa: PLC0415

        db_path = get_db_path()
        if not os.path.isfile(db_path):
            return gate_outcome.not_applicable(
                gate_outcome.REASON_NO_DATABASE,
                "No project DB — AT freshness check skipped.",
            )
        be = SQLiteBackend(db_path)
        try:
            svc = ProjectService(be)
            stale = svc.at_check_freshness()
        finally:
            be.close()
    except Exception as e:  # noqa: BLE001 — caught, recorded as non-execution, not as a pass
        return gate_outcome.could_not_run(
            gate_outcome.REASON_RUNNER_ERROR,
            f"AT freshness check could not run: {e}",
        )
    if not stale:
        return gate_outcome.passed("No stale AT records — every one matches the current final-TZ.")
    names = ", ".join(f"{s['slug']} ({s['tz_ref']})" for s in stale[:5])
    more = f" (+{len(stale) - 5} more)" if len(stale) > 5 else ""
    return gate_outcome.failed(
        f"{len(stale)} AT record(s) no longer match the current final-TZ (§8A property 2): "
        f"{names}{more}. Regenerate via docs/en/at-generation-procedure.md before trial."
    )
