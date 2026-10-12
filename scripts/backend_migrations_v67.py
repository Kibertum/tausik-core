"""Migration v67: a task can be closed as obsolete, with its reason.

1.10 (a-task-cannot-be-closed-as-obsolete, decision #390). `resolution` is NULL
for every task closed as delivered and 'obsolete' for one whose premise time
resolved; `resolution_reason` says why. The status stays 'done', so nothing that
asks "is it open?" changes; the delivery metrics exclude resolution='obsolete'.
Same columns in the `tasks` CREATE TABLE for fresh installs, appended last; the
migration guard skips an ALTER whose column exists.

THE LITERAL BELOW IS FROZEN (convention #646).
"""

from __future__ import annotations

MIGRATION_V67: list[str] = [
    "ALTER TABLE tasks ADD COLUMN resolution TEXT "
    "CHECK(resolution IS NULL OR resolution IN ('obsolete'))",
    "ALTER TABLE tasks ADD COLUMN resolution_reason TEXT",
]
