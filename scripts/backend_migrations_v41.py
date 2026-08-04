"""v41 migration SQL — declared "no file changes" on tasks
(qg2-cannot-close-fileless-task).

Held in its own module to keep backend_migrations.py under the 400-line
filesize gate. ``MIGRATION_V41`` is the ordered statement list referenced by
backend_migrations._CURRENT_MIGRATIONS[41]. Purely additive: one ALTER TABLE
ADD COLUMN with a default, no rebuild.

The third scope state of QG-2. The Verify-First contract knew two: a declared
`relevant_files` and an undeclared (empty) one, which it blocks — "an
undeclared scope is unknown, not verified empty". That left no honest exit for
a task that legitimately touches no files (pure planning, a `tausik decide`,
a premise reformulation), a class the framework itself encourages
(convention #251). This column marks the close that used the new path,
`task done --no-file-changes`, whose emptiness is proven by a clean git scope
rather than declared away.

Why a column and not a `status`/`scope` value: exactly the v40 lesson.
`tasks.status` is CHECK-constrained to the lifecycle set and `scope` here would
overload an unrelated field; a dedicated column keeps the marker countable
(`SELECT * FROM tasks WHERE no_file_changes_declared = 1`) without touching a
constrained column. Symmetric to verification_runs.no_tests_declared.

Historical rows default to 0, which is a fact rather than a convenience: a task
closed before v41 could not have used the flag, so "not declared" is true of it.
"""

from __future__ import annotations

MIGRATION_V41: list[str] = [
    # NOT NULL with DEFAULT 0 is safe: 0 is a true statement about every
    # historical row (none could have carried the flag), so the default asserts
    # nothing that was not already the case.
    "ALTER TABLE tasks ADD COLUMN no_file_changes_declared INTEGER NOT NULL DEFAULT 0",
    # The audit query this column exists to make possible; indexed because it is
    # a small-cardinality filter over a table read on every dashboard.
    "CREATE INDEX IF NOT EXISTS idx_tasks_no_file_changes_declared "
    "ON tasks(no_file_changes_declared)",
]
