"""Migration v76: verification_cohorts.state admits 'invalidated' (1.11.3).

fix-pooled-verify-recovery-ss4-widening-inputs, per SPEC
verification-cohort-contract SS4: a named invalidator refuses REUSE of a
prior green cohort, never EXECUTION — the prior row is marked 'invalidated'
and the full lane runs, recording a superseding cohort row. The CHECK born
in v75 admitted only ('open','green','red'), so the widening's own first
UPDATE died as IntegrityError: the refusal loop this code was written to
break came back as a constraint loop bricking the same membership
differently (memory: novyy-state-v-check-ogranichenii-sqlite-migratsiya-
rebuild).

SAME SHAPE AS v49/v64, FOR THE SAME REASON. SQLite cannot alter a CHECK:
the table is rebuilt (CREATE new / INSERT SELECT / DROP / RENAME). The
rebuild cannot live in the statement list — it must skip itself on a
partial fixture (no table, or a synthetic one without the canonical
columns) and on a database that already admits 'invalidated' (fresh
install, second call). So the registry carries an empty marker and the
work is `maybe_widen_cohort_state_v76`, called from run_post_migrations.

THE DDL BELOW IS A FROZEN SNAPSHOT (convention #646): it must equal the
verification_cohorts block of backend_schema.SCHEMA_SQL at v76, and it is
duplicated on purpose — reading the live constant would let a later column
change what v76 builds. Pinned mechanically by
test_schema_upgrade_parity's rebuilt-DDL list, not by trust.
"""

from __future__ import annotations

import logging
import sqlite3

MIGRATION_V76: list[str] = []

_log = logging.getLogger("tausik.migrations")

_CREATE_COHORTS_V76 = """
CREATE TABLE verification_cohorts_v76 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identity TEXT NOT NULL UNIQUE,
    members_json TEXT NOT NULL,
    identity_inputs_json TEXT NOT NULL,
    union_files_hash TEXT NOT NULL,
    gate_signature TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'open'
        CHECK(state IN ('open', 'green', 'red', 'invalidated')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_COHORT_COLUMNS = (
    "id, identity, members_json, identity_inputs_json, "
    "union_files_hash, gate_signature, state, created_at, updated_at"
)


def _needs_rebuild(conn: sqlite3.Connection) -> bool:
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='verification_cohorts'"
        ).fetchone()
    except sqlite3.Error:
        return False
    if not row or not row[0]:
        return False
    ddl = str(row[0])
    if "CHECK(state IN" not in ddl or "'invalidated'" in ddl:
        return False
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(verification_cohorts)")}
    except sqlite3.Error:
        return False
    return {c.strip() for c in _COHORT_COLUMNS.split(",")}.issubset(cols)


def maybe_widen_cohort_state_v76(conn: sqlite3.Connection) -> int:
    """Rebuild `verification_cohorts` so its state CHECK admits 'invalidated'.

    Idempotent; 1 if rebuilt, else 0.
    """
    if not _needs_rebuild(conn):
        return 0
    statements = [
        _CREATE_COHORTS_V76,
        f"INSERT INTO verification_cohorts_v76 ({_COHORT_COLUMNS}) "
        f"SELECT {_COHORT_COLUMNS} FROM verification_cohorts",
        "DROP TABLE verification_cohorts",
        "ALTER TABLE verification_cohorts_v76 RENAME TO verification_cohorts",
    ]
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("BEGIN")
    try:
        for stmt in statements:
            conn.execute(stmt)
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        conn.execute("PRAGMA foreign_keys=ON")
        raise
    conn.execute("PRAGMA foreign_keys=ON")
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"v76 cohorts rebuild broke FK integrity: {violations}")
    _log.info("v76: rebuilt verification_cohorts — state now admits 'invalidated' (SS4 widening)")
    return 1
