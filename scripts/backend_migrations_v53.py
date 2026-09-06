"""v53 migration SQL -- actz_points.tz_ref (final-tz-is-the-acceptance-reference-and-we-have-none).

Held in its own module to keep backend_migrations.py under the filesize gate.
ADD COLUMN only -- no rebuild needed, unlike v50's CHECK-widen.

The INDEX on the new column is deliberately NOT in ``MIGRATION_V53`` (or in
``backend_schema_actz.ACTZ_STATEMENTS``'s unconditional DDL): ``init_schema``
re-runs that whole DDL block on EVERY call, including against a database
already at v52 with an actz_points table that predates this column --
``CREATE TABLE IF NOT EXISTS`` no-ops safely there, but an index statement
referencing tz_ref does not, and it runs BEFORE migrations/postseed ever get a
chance to add the column (measured: it crashed the upgrade path with `no such
column: tz_ref`). ``ensure_actz_points_tz_ref_index`` is a guarded postseed
step instead (registered in backend_migrations_postseed.py), which runs AFTER
the column is guaranteed to exist on both the fresh-install path (the column
is already in the CREATE TABLE) and the upgrade path (this migration's ALTER
just ran, within the same ``run_migrations`` call).
"""

from __future__ import annotations

import sqlite3

MIGRATION_V53: list[str] = [
    "ALTER TABLE actz_points ADD COLUMN tz_ref TEXT NOT NULL DEFAULT ''",
]


def ensure_actz_points_tz_ref_index(conn: sqlite3.Connection) -> None:
    """Idempotent: safe to call whether the column arrived via a fresh
    CREATE TABLE or via this module's ALTER on an upgrade path -- and safe
    when ``actz_points`` does not exist at all yet, which run_migrations
    permits directly against a bare connection (test_migrations.py exercises
    exactly that: no init_schema DDL has ever run on it)."""
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='actz_points'"
    ).fetchone()
    if not exists:
        return
    conn.execute("CREATE INDEX IF NOT EXISTS idx_actz_points_tz_ref ON actz_points(tz_ref)")
    conn.commit()
