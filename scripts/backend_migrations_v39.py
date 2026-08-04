"""v39 — per-gate run records (l26-gate-results-persist).

Structurally mirrors backend_schema_gate_runs.GATE_RUNS_SQL (the fresh-DB
path). The two MUST stay equivalent; tests/test_gate_runs_persist.py asserts it
by diffing sqlite_master between a migrated DB and a freshly initialised one,
rather than against a hardcoded column list (convention #214).

Additive only: creates one table and three indexes, alters nothing, backfills
nothing. There is no historical gate data to recover — the outcomes this table
records were never written down, which is the defect being fixed. Existing DBs
therefore start empty and accumulate from the next verify onward, so metrics
computed right after upgrade legitimately read "0 runs" for every gate. That is
the honest answer, not a bug: nothing is known about gates that ran before the
table existed, and reporting silence as zero-so-far is the point of the
never_fired list carrying the configured gate set alongside it.
"""

from __future__ import annotations

from backend_schema_gate_runs import GATE_RUNS_SQL

MIGRATION_V39: list[str] = [
    stmt.strip() for stmt in GATE_RUNS_SQL.strip().split(";") if stmt.strip()
]
