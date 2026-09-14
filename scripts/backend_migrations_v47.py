"""v47 migration SQL — a gate row records its OUTCOME and its REASON
(check-result-conflates-could-not-run-with-passed, wave 2 of release 1.9).

Held in its own module to keep backend_migrations.py under the filesize gate.
``MIGRATION_V47`` is the ordered statement list referenced by
backend_migrations._CURRENT_MIGRATIONS[47]. Purely additive: two new columns,
no table rebuild, no existing column touched.

WHY THE TWO BOOLEANS WERE NOT ENOUGH. ``gate_runs`` stored ``passed`` and
``skipped`` — four representable combinations for what is really four distinct
events, one of which the pair cannot spell at all: a check that COULD NOT RUN.
It was stored as ``passed=1, skipped=1``, the same row a legitimately empty
check writes, so the table could not answer the one question the framework most
needs to ask of itself: how often does a gate certify a closure without having
executed? Session #182 measured both readings of that hole in one afternoon —
a non-execution recorded as a blocking failure, and a non-execution recorded as
a pass.

WHY A REASON COLUMN AND NOT JUST A STATUS. A non-execution without its cause is
the dead end the #182 receipt already demonstrated: the refusal named neither
why nothing ran nor what would make it run, and the distance between "blocking
failure" and "all green" turned out to be one environment variable the record
never mentioned. The reason code is machine-readable on purpose — the human
sentence lives in the gate's output and may be reworded, but a query that asks
"which gates never executed, and why" has to match on something stable.

WHY NULLABLE AND WHY NO BACKFILL. Rows written before this migration genuinely
do not know which of the two skip meanings they carried; that is the defect
being fixed, and inventing a value for them would manufacture the evidence this
task exists to stop manufacturing. They stay NULL, which reads as "recorded
before the distinction existed" — an honest gap rather than a confident lie.
`gate_verdict` falls back to the legacy boolean reading for exactly those rows.

WHY `passed`/`skipped` SURVIVE. They are the legacy reading, still written and
still correct for the three outcomes they CAN express, which keeps the rollback
plan a plain `git revert` with no downward migration. New decisions are made on
``outcome``; the booleans are derived from it, never the other way round.
"""

from __future__ import annotations

MIGRATION_V47: list[str] = [
    "ALTER TABLE gate_runs ADD COLUMN outcome TEXT",
    "ALTER TABLE gate_runs ADD COLUMN reason_code TEXT",
    # The question this table exists to answer cheaply: which gates are
    # certifying without executing, and how often.
    "CREATE INDEX IF NOT EXISTS idx_gate_runs_outcome ON gate_runs(outcome)",
]
