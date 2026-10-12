"""Open the project database for READING ONLY — no WAL switch, no migration.

Session #266 (test-run-migrates-the-live-project-db): a test of the CLAUDE.md
state gate opened the developer's live `.tausik/tausik.db` through the ordinary
backend; `init_schema` migrated it, and the deployed copy of the code then
refused the database as "newer than code" until the next bootstrap. A reader
has no business writing the schema, so a reader opens with `mode=ro` and
REFUSES a version mismatch instead of fixing it.
"""

from __future__ import annotations

import os
import sqlite3

from tausik_utils import ServiceError


def open_read_only(db_path: str) -> sqlite3.Connection:
    """A `mode=ro` connection to a database at exactly the code's schema version."""
    from backend_schema import SCHEMA_VERSION

    uri = "file:" + os.path.abspath(db_path).replace("\\", "/") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    except sqlite3.Error:
        row = None
    found = int(row[0]) if row else None
    if found != SCHEMA_VERSION:
        conn.close()
        # Same words as backend_init for the newer case — receipts and tests key on them.
        side = "newer" if (found or 0) > SCHEMA_VERSION else "older"
        raise ServiceError(
            f"Database schema v{found} is {side} than code v{SCHEMA_VERSION}; a read-only "
            "check does not migrate it — run bootstrap (or any tausik command) first"
        )
    return conn
