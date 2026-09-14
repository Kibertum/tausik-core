"""Migration v62: the defect-of lookup gets the index the verify lookup has.

WHAT WAS MEASURED (session #261, this project's live database, 1654 tasks of
which 1504 done). `tausik status` took 5.3 s, and 5.04 s of it was ONE query —
`backend_defect_escape._done_rows`, whose correlated subquery
`EXISTS(SELECT 1 FROM tasks d WHERE d.defect_of = t.slug)` had no index on
`tasks.defect_of` and re-scanned the wide `tasks` table for each done row. The
sibling `EXISTS` over `verification_runs` in the same statement took 0.0 s,
because `idx_verify_task` exists. Same shape, one index apart.

WHY IT IS A RELEASE FIX AND NOT A TUNING. The SessionStart and Stop hooks call
`status`; on this machine they took 5.9 s against deployed timeouts of 6 s and
5 s, and in a headless probe the SessionStart hook was CANCELLED — the whole
auto-injected context (active tasks, memory, reminders) never reached the
model, silently. A framework whose context delivery fails once the project has
a history is not the framework the notes describe.

WHY A MIGRATION AND NOT ONLY THE INDEX BLOCK. `defect_of` was added by v10, so
the index belongs in `POST_MIGRATION_INDEXES_SQL` too (fresh installs, and the
CURRENT set) — but `init_schema` returns before any DDL when the database is
already at `SCHEMA_VERSION`, so a v61 database would never receive it. The bump
is what carries the index to every existing install.

THE LITERAL BELOW IS FROZEN (convention #646).
"""

from __future__ import annotations

MIGRATION_V62: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_tasks_defect_of ON tasks(defect_of)",
]
