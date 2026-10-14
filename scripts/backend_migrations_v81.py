"""Migration v81: review_cohort_rounds.reviewer_context admits 'external' (1.11.6).

one-family-per-environment: L3 separation of duties now holds by the isolated
read-only context, and the reviewer runs on the SAME model family as the
author. The context token for new rounds is 'external'; the CHECK born in v79
admitted only 'different-model', so the first honest new round would die as
IntegrityError. Historical rows keep their legacy token and stay readable.

SAME SHAPE AS v76, FOR THE SAME REASON. SQLite cannot alter a CHECK: the table
is rebuilt (CREATE new / INSERT SELECT / DROP / RENAME). The rebuild cannot
live in the statement list — it must skip itself on a partial fixture (no
table, or a synthetic one without the canonical columns) and on a database
that already admits 'external' (fresh install, second call). So the registry
carries an empty marker and the work is `maybe_widen_round_context_v81`,
called from run_post_migrations.

THE DDL BELOW IS A FROZEN SNAPSHOT (convention #646): it must equal the
review_cohort_rounds block of backend_schema.SCHEMA_SQL at v81, and it is
duplicated on purpose — reading the live constant would let a later column
change what v81 builds. Pinned mechanically by
test_schema_upgrade_parity's rebuilt-DDL list, not by trust.
"""

from __future__ import annotations

import logging
import sqlite3

MIGRATION_V81: list[str] = []

_log = logging.getLogger("tausik.migrations")

_CREATE_ROUNDS_V81 = """
CREATE TABLE review_cohort_rounds_v81 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cohort_pk INTEGER NOT NULL REFERENCES review_cohorts(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL CHECK(round_number IN (1, 2)),
    packet_json TEXT NOT NULL,
    author_model TEXT NOT NULL,
    reviewer_model TEXT NOT NULL,
    reviewer_context TEXT NOT NULL
        CHECK(reviewer_context IN ('external', 'different-model')),
    reviewer_invocations INTEGER NOT NULL CHECK(reviewer_invocations=1),
    usage_json TEXT,
    recorded_at TEXT NOT NULL,
    UNIQUE(cohort_pk, round_number)
)
"""

_ROUNDS_COLUMNS = (
    "id, cohort_pk, round_number, packet_json, author_model, "
    "reviewer_model, reviewer_context, reviewer_invocations, usage_json, recorded_at"
)


def _needs_rebuild(conn: sqlite3.Connection) -> bool:
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='review_cohort_rounds'"
        ).fetchone()
    except sqlite3.Error:
        return False
    if not row or not row[0]:
        return False
    ddl = str(row[0])
    if "CHECK(reviewer_context" not in ddl or "'external'" in ddl:
        return False
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(review_cohort_rounds)")}
    except sqlite3.Error:
        return False
    return {c.strip() for c in _ROUNDS_COLUMNS.split(",")}.issubset(cols)


def maybe_widen_round_context_v81(conn: sqlite3.Connection) -> int:
    """Rebuild `review_cohort_rounds` so its CHECK admits 'external'.

    Idempotent; 1 if rebuilt, else 0. Runs after v77's backfill, which may
    leave its implicit UPDATE transaction open — in that case the rebuild
    joins that transaction instead of opening a second one (a child-table
    DROP/RENAME needs no FK rewrite, so it is safe either way).
    """
    if not _needs_rebuild(conn):
        return 0
    statements = [
        _CREATE_ROUNDS_V81,
        f"INSERT INTO review_cohort_rounds_v81 ({_ROUNDS_COLUMNS}) "
        f"SELECT {_ROUNDS_COLUMNS} FROM review_cohort_rounds",
        "DROP TABLE review_cohort_rounds",
        "ALTER TABLE review_cohort_rounds_v81 RENAME TO review_cohort_rounds",
    ]
    owns_transaction = not conn.in_transaction
    conn.execute("PRAGMA foreign_keys=OFF")
    if owns_transaction:
        conn.execute("BEGIN")
    try:
        for stmt in statements:
            conn.execute(stmt)
        if owns_transaction:
            conn.execute("COMMIT")
    except Exception:
        if owns_transaction:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        conn.execute("PRAGMA foreign_keys=ON")
        raise
    conn.execute("PRAGMA foreign_keys=ON")
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"v81 rounds rebuild broke FK integrity: {violations}")
    _log.info("v81: rebuilt review_cohort_rounds — reviewer_context now admits 'external' (1.11.6)")
    return 1
