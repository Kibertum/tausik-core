"""v38 migration SQL — declared-scope honesty on verification runs
(l26-verify-git-diff-wire).

Held in its own module to keep backend_migrations.py under the 400-line
filesize gate. ``MIGRATION_V38`` is the ordered statement list referenced by
backend_migrations._CURRENT_MIGRATIONS[38]. Purely additive: two nullable
ALTER TABLE ADD COLUMN, no rebuild, no CHECK, no NOT NULL.

Historical rows are deliberately NOT backfilled. A run recorded before v38
carries no evidence about whether its declared scope matched git, and inventing
'complete' for it would manufacture exactly the false assurance this change
removes. NULL is read as 'unknown' by every reader (memory #221 — a check that
could not be computed must not report success).

Structurally mirrors the verification_runs baseline in backend_schema.py so a
fresh DB and an upgraded DB end up with identical columns.
"""

from __future__ import annotations

MIGRATION_V38: list[str] = [
    # 'complete' | 'under-declared' | 'unknown'. NOT NULL is omitted on purpose:
    # SQLite cannot ADD COLUMN NOT NULL without a default, and a default here
    # would assert a status for historical rows that were never measured.
    "ALTER TABLE verification_runs ADD COLUMN declared_scope_status TEXT",
    # JSON array of paths git reported changed while relevant_files omitted them,
    # sorted and capped at verify_scope_honesty.MAX_LISTED_UNDECLARED.
    "ALTER TABLE verification_runs ADD COLUMN undeclared_files TEXT",
    "CREATE INDEX IF NOT EXISTS idx_verify_scope_status "
    "ON verification_runs(declared_scope_status)",
]
