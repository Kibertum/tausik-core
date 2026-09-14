"""RENAR drift gate runner — wraps renar_drift detectors for the gate pipeline.

Extracted from gate_runner.py (filesize budget, memory #144). gate_runner
re-exports ``run_renar_drift_gate`` so existing dispatch keeps working.
"""

from __future__ import annotations

import os

import gate_outcome

_GATE_TO_DETECTOR = {
    "renar_drift_schema": "schema",
    "renar_drift_provenance": "provenance",
    # ADR-007's own name for the gate it promised, kept verbatim (in the
    # registry's snake_case spelling) so the promise is greppable from the ADR.
    "check_adapt_supersession": "supersession",
}


def run_renar_drift_gate_for(gate: dict, files: list[str]) -> gate_outcome.GateOutcome:
    """Registry-uniform ``(gate, files)`` entrypoint (gate-registry-single-source).

    Two detectors share one implementation and are told apart by gate name, so
    the registry points here rather than at a per-detector wrapper. ``files`` is
    ignored by design — these detectors scan the RENAR artifact store, not the
    task's scope.
    """
    return run_renar_drift_gate(str(gate.get("name") or ""))


def run_renar_drift_gate(name: str) -> gate_outcome.GateOutcome:
    """Run a RENAR drift detector against the project artifact store.

    Read-only: opens its own short-lived connection to the project DB (WAL lets
    it read alongside the MCP server's connection) and never writes. Warn-only —
    findings never block; a DB/import failure degrades to a SKIP-style pass so a
    detector bug can't wedge task-done. ``name`` maps to renar_drift's short key.
    """
    which = _GATE_TO_DETECTOR.get(name)
    if which is None:
        # Not a skip: the caller named a gate this module has no detector for,
        # so nothing was checked. REASON_NO_GATE_IMPLEMENTATION is exactly that
        # event, and it already exists for the runner's own version of it.
        return gate_outcome.could_not_run(
            gate_outcome.REASON_NO_GATE_IMPLEMENTATION,
            f"Unknown RENAR drift gate {name!r} — no detector is mapped to it.",
            remedy="Fix the gate name in the registry, or map a detector to it.",
        )
    try:
        import sqlite3  # noqa: PLC0415

        from project_config import get_db_path  # noqa: PLC0415
        from renar_drift import format_findings, run_detector  # noqa: PLC0415

        db_path = get_db_path()
        if not os.path.isfile(db_path):
            return gate_outcome.not_applicable(
                gate_outcome.REASON_NO_DATABASE,
                "No project DB — RENAR drift check skipped.",
            )
        conn = sqlite3.connect(db_path, timeout=10)
        try:
            findings = run_detector(conn, which)
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001 — caught, but recorded as non-execution, not as a pass
        # COULD_NOT_RUN even though this gate is severity=warn. Measured, not
        # assumed: gate_runner:254 raises a blocking failure only when
        # `outcome.blocks AND severity == "block"`, so a warn gate that says
        # CANNOT-RUN stops nothing. The receipt stops lying at zero cost — and
        # recording it as PASSED would put a false green in the one place a
        # reader checks whether RENAR drift was actually looked for.
        return gate_outcome.could_not_run(
            gate_outcome.REASON_RUNNER_ERROR,
            f"RENAR drift check unavailable ({type(e).__name__}: {e}).",
            remedy=(
                "This gate produced no evidence, so it certifies nothing. Drift "
                "is unknown, not absent. Re-run once the fault above is gone."
            ),
        )
    if findings:
        return gate_outcome.failed(format_findings(findings))
    return gate_outcome.passed(format_findings(findings))
