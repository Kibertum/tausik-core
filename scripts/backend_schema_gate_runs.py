"""Baseline DDL for per-gate run records (l26-gate-results-persist).

Gate outcomes used to live only in the return value of ``run_gates`` and were
discarded once the caller printed them. That made the enforcement layer the one
part of TAUSIK it could say nothing measurable about: how often `filesize`
actually blocks, which gate has never once fired, whether the failure rate is
climbing. A framework that asks every task for evidence kept none about itself.

Kept out of backend_schema.py to hold that file under the 400-line filesize
gate — same split as SNIPPETS_SQL / SPECS_SQL / ADAPTS_SQL. ``init_schema``
runs GATE_RUNS_SQL on the fresh-DB path; migration v39 builds the same objects
for existing DBs. The two DDL sources MUST stay structurally equivalent, and
the equivalence test derives its comparison from sqlite_master rather than a
hardcoded column list (convention #214) — a hand-written list is exactly how
the verification_runs tests drifted from the schema they claim to check.

``task_slug`` and ``trigger`` are denormalised on purpose: the questions this
table exists to answer are per-gate aggregates, and making every one of them
join back to verification_runs would price them out of the metrics path.

The foreign key IS enforced: project_backend opens every connection with
PRAGMA foreign_keys=ON. A gate row therefore cannot reference a run that does
not exist, which is what makes the single-transaction write in
verify_run_record load-bearing rather than merely tidy.
"""

from __future__ import annotations

GATE_RUNS_SQL = """
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
