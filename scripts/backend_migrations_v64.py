"""Migration v64: SPEC-UC, the twelfth type of the closed SPEC list (RENAR 1.1 §8.3).

RENAR 1.1 (2026-09-19, ADR-018) closes the SPEC type list at twelve: SPEC-UC
(use cases) with `role: human | agent` and a reference from every step to a
statement of SPEC-UI or SPEC-PROC (§8.5.12, §8.5.12.1). The drift detector,
once pointed at the standard's own repository, reported exactly this and
nothing else: "the corpus closes the list at 12; ours has 11".

SAME SHAPE AS v49, FOR THE SAME REASON. The type list lives in a CHECK on
`specs.type`, and SQLite cannot alter a CHECK: the table is rebuilt. The
rebuild cannot live in the statement list — it must skip itself on a partial
fixture (no `specs`, or a synthetic one without the canonical columns) and on
a database that already admits 'UC' (fresh install, second call). So the
registry carries an empty marker and the work is `maybe_widen_spec_types_v64`,
called from `run_post_migrations`. v49's own rebuild keys on 'TEST' and skips
any table that already admits it, so the two never fight.

THE DDL BELOW IS A FROZEN SNAPSHOT (convention #646): it must equal the specs
block of backend_schema_specs.SPECS_SQL at v64, and it is duplicated on purpose
— reading the live constant would let a later column change what v64 builds.
"""

from __future__ import annotations

import logging
import sqlite3

from backend_migrations_v49 import _SPEC_COLUMNS, _INDEXES, _TRIGGERS

MIGRATION_V64: list[str] = []

_log = logging.getLogger("tausik.migrations")

_CREATE_SPECS_V64 = """
CREATE TABLE specs_v64 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN
        ('ARCH', 'API', 'DATA', 'INT', 'PROC', 'UI', 'AI', 'SEC', 'OPS',
         'TEST', 'DOC', 'UC')),
    title TEXT NOT NULL,
    content_ref TEXT,
    version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN
        ('draft', 'active', 'deprecated')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _needs_rebuild(conn: sqlite3.Connection) -> bool:
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='specs'"
        ).fetchone()
    except sqlite3.Error:
        return False
    if not row or not row[0]:
        return False
    ddl = str(row[0])
    if "CHECK(type IN" not in ddl or "'UC'" in ddl:
        return False
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(specs)")}
    except sqlite3.Error:
        return False
    return {c.strip() for c in _SPEC_COLUMNS.split(",")}.issubset(cols)


def maybe_widen_spec_types_v64(conn: sqlite3.Connection) -> int:
    """Rebuild `specs` so its CHECK admits 'UC'. Idempotent; 1 if rebuilt, else 0."""
    if not _needs_rebuild(conn):
        return 0
    statements = [
        "DROP TRIGGER IF EXISTS specs_ai",
        "DROP TRIGGER IF EXISTS specs_ad",
        "DROP TRIGGER IF EXISTS specs_au",
        _CREATE_SPECS_V64,
        f"INSERT INTO specs_v64 ({_SPEC_COLUMNS}) SELECT {_SPEC_COLUMNS} FROM specs",
        "DROP TABLE specs",
        "ALTER TABLE specs_v64 RENAME TO specs",
        *_INDEXES,
        *_TRIGGERS,
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
        raise RuntimeError(f"v64 specs rebuild broke FK integrity: {violations}")
    _log.info("v64: rebuilt specs — the closed type list now carries SPEC-UC (twelve)")
    return 1
