"""v40 migration SQL — declared "no test expected" on verification runs
(verify-no-test-mapped-dead-end).

Held in its own module to keep backend_migrations.py under the 400-line
filesize gate. ``MIGRATION_V40`` is the ordered statement list referenced by
backend_migrations._CURRENT_MIGRATIONS[40]. Purely additive: one ALTER TABLE
ADD COLUMN with a default, no rebuild.

Why a column and not a `scope` value: the first cut of this feature encoded the
marker as `scope='no-tests-expected'`, which looked free — no migration, an
existing column, one-query audit. It was not free. `scope` carries
`CHECK(scope IN ('lightweight','standard','high','critical','manual'))`, so
every such write raised IntegrityError against a real database. Tests did not
catch it because their `verification_runs` DDL is a hand-written copy without
the constraint (see task `test-ddl-drift-verification-runs`), and the write
failure was swallowed into a log warning while verify still printed a pass (see
task `verify-record-failure-swallowed`). Three separate holes had to line up
for a broken feature to look green, and they did.

Historical rows default to 0, which is correct rather than convenient: a run
recorded before v40 could not have carried the declaration, so "not declared"
is a fact about it, not an assumption.
"""

from __future__ import annotations

MIGRATION_V40: list[str] = [
    # NOT NULL is safe here (unlike v38) precisely because 0 is a true statement
    # about every historical row, so a default asserts nothing that was not
    # already the case.
    "ALTER TABLE verification_runs ADD COLUMN no_tests_declared INTEGER NOT NULL DEFAULT 0",
    # The audit query this feature exists to make possible; indexed because it
    # is a small-cardinality filter over a table that grows with every run.
    "CREATE INDEX IF NOT EXISTS idx_verify_no_tests_declared "
    "ON verification_runs(no_tests_declared)",
]
