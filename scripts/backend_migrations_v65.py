"""Migration v65: a memory record says where its claim came from.

1.10, story D (memory-record-does-not-say-where-its-claim-came-from). The
framework turns words into checkable records everywhere but in its own memory:
a gotcha measured by a test and a convention someone asserted read alike.
`provenance` is one of `observed` (backed by something checkable — a task log,
a verify run, a test), `inferred` (reasoned, not measured) or `told` (a person
said so).

EVERY EXISTING ROW BECOMES `inferred`. Observation cannot be proven after the
fact, and declaring it would be a claim about the whole past corpus that nobody
checked. `inferred` is the weak statement, so it is also the default for new
rows; `observed` is earned per record (service_knowledge.memory_add).

Same column in the `memory` CREATE TABLE for fresh installs, appended LAST so a
fresh and a migrated table have the same column order. The `memory` table exists
on every database old enough to be migrated; the guard in
backend_migrations_guard skips the ALTER where the column is already there.

THE LITERAL BELOW IS FROZEN (convention #646).
"""

from __future__ import annotations

MIGRATION_V65: list[str] = [
    "ALTER TABLE memory ADD COLUMN provenance TEXT NOT NULL DEFAULT 'inferred' "
    "CHECK(provenance IN ('observed', 'inferred', 'told'))",
]
