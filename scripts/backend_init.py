"""SQLite schema initialization & migration runner — extracted from
project_backend.py (`v14b-project-backend-debt-paydown`).

`init_schema(conn)` does the full DDL bootstrap path: skip when the meta
table already records the current schema version, raise on a newer DB,
otherwise run SCHEMA_SQL + FTS_SQL + FTS_TRIGGERS_SQL + INDEXES_SQL and
record the version. On a stale-but-compatible version it backs up the
DB file (idempotent — ``.bak.v<old>``) and runs `run_migrations`, then
rebuilds the FTS indexes. Behaviour is byte-for-byte identical to the
prior `SQLiteBackend._init_schema` method.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import sqlite3

from backend_migrations import run_migrations
from backend_schema import (
    FTS_SQL,
    FTS_TRIGGERS_SQL,
    INDEXES_SQL,
    SCHEMA_SQL,
    SCHEMA_VERSION,
)
from backend_schema_adapts import ADAPTS_SQL
from backend_schema_gate_runs import GATE_RUNS_SQL
from backend_schema_snippets import SNIPPETS_SQL
from backend_schema_specs import SPECS_SQL

logger = logging.getLogger("tausik.backend")

# `content='<table>'` in an FTS5 declaration — an external-content index, whose
# rows live in another table and therefore need an explicit 'rebuild' after a
# migration touches that table. A contentless index (`content=''`) does not
# match, and must not: 'rebuild' is invalid for it.
_FTS_EXTERNAL_CONTENT_RE = re.compile(r"content\s*=\s*'([^']+)'", re.IGNORECASE)


#: How many `.bak.v<N>` snapshots to keep. One per migration is created and the
#: old runner never removed any — a long-lived project accumulated 10 backups
#: (~150 MB) beside a 24 MB database. Three is enough to step back through a bad
#: migration; older ones are dead weight in everyone's working tree.
BACKUP_KEEP = 3

_BAK_SUFFIX_RE = re.compile(r"\.bak\.v(\d+)$")


def prune_db_backups(db_path: str, keep: int = BACKUP_KEEP) -> list[str]:
    """Delete all but the `keep` newest `<db>.bak.v<N>` files. Returns removed paths.

    Ordered by the version NUMBER parsed out of the name, not by string sort —
    lexically ``v9`` sorts after ``v10``, which would delete the newest backups
    and keep the oldest, i.e. exactly backwards.

    Best-effort by design: this runs inside the migration path, and failing to
    tidy up must never abort a migration that otherwise succeeded. Every failure
    is logged rather than swallowed silently.
    """
    directory = os.path.dirname(os.path.abspath(db_path))
    base = os.path.basename(db_path)
    try:
        entries = os.listdir(directory)
    except OSError as e:
        logger.warning("Backup prune skipped, cannot list %s: %s", directory, e)
        return []
    versioned: list[tuple[int, str]] = []
    for name in entries:
        m = _BAK_SUFFIX_RE.search(name)
        if not m:
            continue
        # EXACT name, not a prefix: `db.db2.bak.v1` starts with `db.db`, so a
        # bare startswith() pooled a *different* database's backups with this
        # one's. Sorted together by version number, the target database's only
        # real snapshot could be the entry chosen for deletion.
        if os.path.normcase(name) != os.path.normcase(f"{base}.bak.v{m.group(1)}"):
            continue
        versioned.append((int(m.group(1)), os.path.join(directory, name)))
    if len(versioned) <= keep:
        return []
    versioned.sort(key=lambda pair: pair[0])
    removed: list[str] = []
    for _ver, path in versioned[: len(versioned) - keep]:
        try:
            os.remove(path)
            removed.append(path)
        except OSError as e:
            logger.warning("Backup prune failed for %s: %s", path, e)
    if removed:
        logger.info("Pruned %d old DB backup(s), kept newest %d", len(removed), keep)
    return removed


def external_content_fts_tables(cur: sqlite3.Cursor) -> list[str]:
    """Names of every external-content FTS5 table present in this database.

    Derived from ``sqlite_master`` rather than hardcoded. A hardcoded list goes
    stale the moment a migration adds an FTS table, and does so *silently* —
    which is exactly how ``fts_task_logs`` and ``fts_reasoning_steps`` came to
    be created, trigger-maintained, and never rebuilt: search over task logs and
    RENAR reasoning steps returned stale rows after every migration, with no
    error anywhere. Deriving the list removes the whole failure class instead of
    adding two more names to forget.
    """
    rows = cur.execute(
        # Anchored on the DDL shape, not a bare substring: an ordinary table
        # whose DDL merely *contains* that phrase (a CHECK constraint, a default
        # holding the text) must not be probed as an FTS candidate.
        "SELECT name, sql FROM sqlite_master "
        "WHERE type='table' AND sql LIKE 'CREATE VIRTUAL TABLE%USING fts5%'"
    ).fetchall()
    names = [
        name
        for name, sql in rows
        if sql and (m := _FTS_EXTERNAL_CONTENT_RE.search(sql)) and m.group(1).strip()
    ]
    return sorted(names)


def init_schema(conn: sqlite3.Connection) -> None:
    """Bootstrap or migrate the SQLite schema on `conn`.

    Idempotent: when the `meta.schema_version` row already matches
    `SCHEMA_VERSION`, returns without running any DDL. Raises
    ``RuntimeError`` when the on-disk schema is newer than the code
    so the caller refuses to operate on a database it cannot reason
    about.
    """
    cur = conn.cursor()
    # Check if schema already at current version (skip DDL for performance)
    try:
        row = cur.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row:
            db_ver = int(row[0])
            if db_ver == SCHEMA_VERSION:
                conn.commit()
                return  # Schema up to date, skip DDL
            if db_ver > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema v{db_ver} is newer than code v{SCHEMA_VERSION}. "
                    f"Update .tausik-lib to the latest version."
                )
    except RuntimeError:
        raise  # Re-raise schema version guard errors
    except Exception:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
        pass  # Table doesn't exist yet -- run full DDL
    cur.executescript(SCHEMA_SQL)
    cur.executescript(FTS_SQL)
    cur.executescript(FTS_TRIGGERS_SQL)
    cur.executescript(INDEXES_SQL)
    cur.executescript(SPECS_SQL)  # RENAR SPEC artifacts (v16r-spec-types)
    cur.executescript(ADAPTS_SQL)  # RENAR ADAPT artifacts (v16r-adapt)
    cur.executescript(SNIPPETS_SQL)  # snippet store (v15-snippet-table)
    cur.executescript(GATE_RUNS_SQL)  # per-gate outcomes (l26-gate-results-persist)
    row = cur.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    if not row:
        cur.execute(
            "INSERT INTO meta(key,value) VALUES('schema_version',?)",
            (str(SCHEMA_VERSION),),
        )
        conn.commit()
        run_migrations(conn, SCHEMA_VERSION)
    else:
        current_ver = int(row[0])
        if current_ver < SCHEMA_VERSION:
            # Backup DB before migration
            db_path = conn.execute("PRAGMA database_list").fetchone()[2]
            backup_path = f"{db_path}.bak.v{current_ver}"
            if db_path and not os.path.exists(backup_path):
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    shutil.copy2(db_path, backup_path)
                    logger.info("Backup created: %s", backup_path)
                except OSError as e:
                    logger.warning("Backup failed for %s: %s", db_path, e)
            new_ver = run_migrations(conn, current_ver)
            cur.execute(
                "UPDATE meta SET value=? WHERE key='schema_version'",
                (str(new_ver),),
            )
            # Rebuild FTS indexes after migration
            for fts_table in external_content_fts_tables(cur):
                try:
                    cur.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
                except Exception as e:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
                    logger.warning("FTS rebuild failed for %s: %s", fts_table, e)
            logger.info("Schema migrated %d -> %d", current_ver, new_ver)
            # Only after the migration succeeded — a failed run must keep every
            # snapshot it might need to roll back to.
            if db_path:
                prune_db_backups(db_path)
    conn.commit()
