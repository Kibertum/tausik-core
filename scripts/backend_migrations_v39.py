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

WHY THIS DDL IS A FROZEN COPY AND NOT AN IMPORT. It used to be derived from the
live ``GATE_RUNS_SQL`` at import time, which quietly made a migration mean
whatever the CURRENT schema means. That held only while the table never changed
again. When v47 added ``outcome``/``reason_code`` to the fresh-DB DDL, this
migration silently started creating the NEW shape at step 39, and the v47
``ALTER TABLE`` that followed it in the same chain died on "duplicate column
name" — an upgrade from any older version could not complete at all.

A migration is a historical fact: it must build what the schema looked like AT
THAT VERSION, no matter what the schema looks like today. Later shapes are the
business of later migrations. The equivalence the parity tests assert is between
the FRESH path and the END of the migration chain — not between the fresh path
and any single step of it.
"""

from __future__ import annotations

# Frozen snapshot of backend_schema_gate_runs.GATE_RUNS_SQL as it stood at v39.
# Do NOT re-point this at the live constant; see the module docstring.
_GATE_RUNS_SQL_V39 = """
CREATE TABLE IF NOT EXISTS gate_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verification_run_id INTEGER REFERENCES verification_runs(id),
    task_slug TEXT,
    trigger TEXT,
    gate_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
    skipped INTEGER NOT NULL DEFAULT 0 CHECK(skipped IN (0, 1)),
    duration_ms INTEGER,
    ran_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gate_runs_name ON gate_runs(gate_name);
CREATE INDEX IF NOT EXISTS idx_gate_runs_run ON gate_runs(verification_run_id);
CREATE INDEX IF NOT EXISTS idx_gate_runs_task ON gate_runs(task_slug);
"""

MIGRATION_V39: list[str] = [
    stmt.strip() for stmt in _GATE_RUNS_SQL_V39.strip().split(";") if stmt.strip()
]
