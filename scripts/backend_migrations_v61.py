"""Migration v61: a task remembers which external ticket it came from.

WHAT WAS MISSING. A task carried 43 columns and not one of them said "this work
came from someone's ticket". So closing a task could not close a ticket — the
link did not exist as data, and there was nowhere to read it. Measured twice
(sessions #178 and #241): GitHub #7 and #8 fixed by 056818b and 3de2528, both
still OPEN; GitLab #3, #4, #7 fixed by the same commits, also OPEN. The outside
author who filed the finding never learned it was fixed.

WHY A COLUMN AND NOT A TABLE. A ticket reference is a short string with no
attributes of its own — no state to keep, nothing to join on, nothing this
framework may ask the tracker about. `relevant_files` is the precedent in this
same table: a JSON list in TEXT, read by one module. A table would buy foreign
keys to rows that live in someone else's system.

THE LITERAL BELOW IS FROZEN (convention #646). A migration that read the live
schema would mean whatever that schema means today, so a database migrated now
and one migrated next year would differ while both reported v61.
"""

from __future__ import annotations

#: JSON list of `<tracker>#<id>` strings and/or ticket URLs, as parsed by
#: `tracker_ref`. NULL and `[]` mean the same thing — no ticket — and both are
#: normal: most tasks are not filed by anyone outside.
MIGRATION_V61: list[str] = [
    "ALTER TABLE tasks ADD COLUMN tracker_refs TEXT",
]
