"""Guards around the migration chain (github#51, gitlab#18).

Split out of backend_migrations.py for the 500-line file cap; the two helpers
are what the 1.8 -> 1.9 upgrade crash taught.
"""

from __future__ import annotations

import re
import sqlite3

_ADD_COLUMN = re.compile(r"^\s*ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", re.IGNORECASE)


def _column_already_there(conn: sqlite3.Connection, stmt: str) -> bool:
    """True when `stmt` adds a column its table already has (github#51, gitlab#18).

    On an existing database `init_schema` runs the cumulative creation scripts
    BEFORE the migration chain, so a table first created by a migration (v52's
    actz_points) can already exist in its CURRENT shape when a later migration
    (v53) adds the column that shape already carries. Only that case is
    skipped: a missing table, or any other statement, still runs and fails.
    """
    m = _ADD_COLUMN.match(stmt)
    if not m:
        return False
    table, column = m.group(1), m.group(2)
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    return column in cols


def _stamp(conn: sqlite3.Connection, ver: int) -> None:
    """Record `ver` inside the migration's own transaction.

    The stamp used to be written by init_schema after the WHOLE chain, while
    each migration committed on its own — an interruption left v45..v52
    committed under a stamp of 44 and the next start replayed them into
    duplicate-column errors (github#51). With the stamp in the same COMMIT the
    database always names the last migration it actually holds.
    """
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)", (str(ver),))
