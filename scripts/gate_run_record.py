"""Persist one row per gate execution (l26-gate-results-persist).

Deliberately does NOT commit. The caller inserts the verification_runs row,
passes the fresh row id here, and commits once — so a run and the gate results
that justify it land together or not at all. A verification_runs row whose gate
rows silently failed to write would be a claim with no evidence behind it,
which is the failure mode this table exists to remove.

For the same reason nothing here is best-effort: a write that cannot happen
raises, and the caller's transaction takes the whole run down with it
(convention #221 — a check that cannot record its result must not report
success). Losing one verify run is cheap; a run that looks recorded but is not
is expensive, because it is indistinguishable from a real one afterwards.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_gate_runs(
    conn: sqlite3.Connection,
    *,
    verification_run_id: int,
    task_slug: str | None,
    trigger: str | None,
    gate_results: list[dict[str, Any]],
    ran_at: str | None = None,
) -> int:
    """Insert a row per gate result. Returns the number of rows written.

    Caller owns the transaction — see the module docstring.
    """
    if not gate_results:
        return 0
    stamp = ran_at or _utcnow_iso()
    rows = [
        (
            verification_run_id,
            task_slug,
            trigger,
            str(r.get("name") or ""),
            str(r.get("severity") or ""),
            1 if r.get("passed") else 0,
            1 if r.get("skipped") else 0,
            r.get("duration_ms"),
            stamp,
        )
        for r in gate_results
    ]
    conn.executemany(
        """
        INSERT INTO gate_runs
            (verification_run_id, task_slug, trigger, gate_name, severity,
             passed, skipped, duration_ms, ran_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def gate_activity(conn: sqlite3.Connection, known_gates: list[str]) -> dict[str, Any]:
    """Per-gate aggregates: runs, failures, blocks, skips, never-fired.

    `known_gates` is the configured gate set. Gates in it with zero rows are
    reported explicitly with runs=0 rather than omitted: "this gate has never
    once fired" is the single most useful thing this table can say, and it is
    invisible if absence is rendered as absence (convention #226).
    """
    seen: dict[str, dict[str, Any]] = {}
    for name, severity, passed, skipped, n in conn.execute(
        """
        SELECT gate_name, severity, passed, skipped, COUNT(*)
        FROM gate_runs GROUP BY gate_name, severity, passed, skipped
        """
    ):
        entry = seen.setdefault(
            name,
            {"gate": name, "runs": 0, "failures": 0, "blocking_failures": 0, "skips": 0},
        )
        entry["runs"] += n
        if skipped:
            entry["skips"] += n
        elif not passed:
            entry["failures"] += n
            if severity == "block":
                entry["blocking_failures"] += n

    for name in known_gates:
        seen.setdefault(
            name,
            {"gate": name, "runs": 0, "failures": 0, "blocking_failures": 0, "skips": 0},
        )

    gates = sorted(seen.values(), key=lambda g: (-g["runs"], g["gate"]))
    total_runs = sum(g["runs"] for g in gates)
    total_blocking = sum(g["blocking_failures"] for g in gates)
    return {
        "gates": gates,
        "total_runs": total_runs,
        "blocking_failure_rate": round(total_blocking / total_runs, 4) if total_runs else None,
        "never_fired": sorted(g["gate"] for g in gates if g["runs"] == 0),
    }
