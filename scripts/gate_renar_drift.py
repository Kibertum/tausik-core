"""RENAR drift gate runner — wraps renar_drift detectors for the gate pipeline.

Extracted from gate_runner.py (filesize budget, memory #144). gate_runner
re-exports ``run_renar_drift_gate`` so existing dispatch keeps working.
"""

from __future__ import annotations

import os

_GATE_TO_DETECTOR = {
    "renar_drift_schema": "schema",
    "renar_drift_provenance": "provenance",
}


def run_renar_drift_gate(name: str) -> tuple[bool, str]:
    """Run a RENAR drift detector against the project artifact store.

    Read-only: opens its own short-lived connection to the project DB (WAL lets
    it read alongside the MCP server's connection) and never writes. Warn-only —
    findings never block; a DB/import failure degrades to a SKIP-style pass so a
    detector bug can't wedge task-done. ``name`` maps to renar_drift's short key.
    """
    which = _GATE_TO_DETECTOR.get(name)
    if which is None:
        return True, f"Unknown RENAR drift gate {name!r} — skipped."
    try:
        import sqlite3  # noqa: PLC0415

        from project_config import get_db_path  # noqa: PLC0415
        from renar_drift import format_findings, run_detector  # noqa: PLC0415

        db_path = get_db_path()
        if not os.path.isfile(db_path):
            return True, "No project DB — RENAR drift check skipped."
        conn = sqlite3.connect(db_path, timeout=10)
        try:
            findings = run_detector(conn, which)
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001 — warn gate must never crash task-done
        return True, f"RENAR drift check unavailable ({type(e).__name__}: {e})."
    return (not findings), format_findings(findings)
