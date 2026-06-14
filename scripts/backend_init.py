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
from backend_schema_snippets import SNIPPETS_SQL
from backend_schema_specs import SPECS_SQL

logger = logging.getLogger("tausik.backend")


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
            for fts_table in (
                "fts_tasks",
                "fts_memory",
                "fts_decisions",
                "fts_specs",
                "fts_adapts",
                "fts_snippets",
            ):
                try:
                    cur.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
                except Exception as e:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
                    logger.warning("FTS rebuild failed for %s: %s", fts_table, e)
            logger.info("Schema migrated %d -> %d", current_ver, new_ver)
    conn.commit()
