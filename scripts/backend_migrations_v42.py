"""v42 migration SQL — stable slug identity for decisions and memory
(state-git-stable-ids).

Held in its own module to keep backend_migrations.py under the 400-line
filesize gate. ``MIGRATION_V42`` is the ordered statement list referenced by
backend_migrations._CURRENT_MIGRATIONS[42].

Purely ADDITIVE: two ``ALTER TABLE ADD COLUMN``, both NULLABLE. NOT NULL is
impossible here — the existing 171 decisions and 300+ memory rows have no slug
to supply as a default, and a UNIQUE constraint cannot be added inline while
those rows are all NULL. The values, and the UNIQUE index, are filled in
afterwards by the idempotent post-migration backfill
(backend_migrations_v42_backfill.maybe_backfill_v42), which runs in Python
because the slug is a transliteration a stock SQLite cannot compute. Fresh
databases get the same columns from SCHEMA_SQL and the same unique index from
the same backfill (which no-ops over zero rows), so both paths converge on one
schema shape.
"""

from __future__ import annotations

MIGRATION_V42: list[str] = [
    "ALTER TABLE decisions ADD COLUMN slug TEXT",
    "ALTER TABLE memory ADD COLUMN slug TEXT",
]
