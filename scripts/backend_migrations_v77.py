"""Migration v77: a blocked task carries its QUESTION and UNBLOCK CRITERIA as fields.

blocked-is-a-status-without-a-question-to-unblock-it. `task block` wrote prose
into the journal and one timestamp; every consumer after that — status, the
agent that inherits the session, the owner asked to decide — had to read three
places of free text to learn what the block was even asking. A block without a
question is a task abandoned with a note to self, and the live corpus carried
exactly that shape since 1.8 (release-18-breaking-change-notes).

Columns:
- blocked_question: the CONCRETE question to the owner. Written NOT NULL in
  effect from v77 on — `task block` refuses to record a block without it —
  though the column itself stays nullable for history.
- unblock_criteria: what must become TRUE for the task to proceed — a
  checkable statement, not a date.
- unblocked_by / unblocked_at: the audit trail of the ANSWER — who stated the
  criterion met and when. Silent unblocking is what these exist to prevent.

The backfill of pre-v77 blocked rows (marker 'не задан') is a GUARDED POST-STEP
(`backfill_blocked_questions_v77`, convention #445), not a statement in this
list: the DML references ``tasks.status``, and a synthetic pre-migration
fixture is allowed to seed a tasks table that never had that column — the
guard asks PRAGMA table_info instead of assuming, and no-ops there. On every
real database (status born in V1) the marker lands exactly once: the UPDATE
only touches rows whose blocked_question is still NULL.
"""

import sqlite3

MIGRATION_V77: list[str] = [
    "ALTER TABLE tasks ADD COLUMN blocked_question TEXT",
    "ALTER TABLE tasks ADD COLUMN unblock_criteria TEXT",
    "ALTER TABLE tasks ADD COLUMN unblocked_by TEXT",
    "ALTER TABLE tasks ADD COLUMN unblocked_at TEXT",
]


def backfill_blocked_questions_v77(conn: sqlite3.Connection) -> None:
    """Stamp the debt marker on blocks that predate questions. Idempotent.

    'не задан' is deliberately not NULL: NULL means "never blocked", the
    marker means "blocked before questions existed" — status renders it as
    DEBT, never as an acceptable state, which is the migration's honesty rule.
    Rows whose blocked_question is already set (any real block from v77 on)
    are untouched, so the step may run any number of times.
    """
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    except Exception:  # noqa: BLE001 — a database with no tasks table owes no backfill
        return
    if "status" not in cols or "blocked_question" not in cols:
        return
    conn.execute(
        "UPDATE tasks SET blocked_question='не задан', unblock_criteria='не задан' "
        "WHERE status='blocked' AND blocked_question IS NULL"
    )
