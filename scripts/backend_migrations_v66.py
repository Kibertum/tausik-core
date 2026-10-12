"""Migration v66: a decision records what it turned down.

1.10, story D (decisions-have-no-lifecycle). `rejected` is a JSON list of
"option :: why" strings — alternatives the decision rejected, searchable rather
than buried in the rationale's prose. NULL for every existing row: what earlier
decisions rejected was never recorded as data, and inventing it now would be
worse than the gap. Same column in the `decisions` CREATE TABLE for fresh
installs, appended last; the migration guard skips the ALTER where it exists.

THE LITERAL BELOW IS FROZEN (convention #646).
"""

from __future__ import annotations

MIGRATION_V66: list[str] = [
    "ALTER TABLE decisions ADD COLUMN rejected TEXT",
]
