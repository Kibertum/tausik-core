"""v52 migration SQL -- RENAR ACTZ artifacts, ORIGINAL shape as shipped.

Held in its own module to keep backend_migrations.py under the filesize gate,
matching v35/v36/v37's split. Purely additive -- new tables only, no ALTER on
any existing table.

FROZEN, like v36 (ADAPT's original 3-status shape) stayed frozen once v50
widened it: v52 shipped as ACTZ's only migration on the (correct, at the time)
premise that a brand-new entity has no history to be a delta against, and
literally reused ``backend_schema_actz.ACTZ_STATEMENTS`` by reference rather
than retyping it. v53 (actz_points.tz_ref) proved that premise short-lived --
ACTZ now HAS history, so this module holds its own independent copy of what it
shipped, and ``backend_schema_actz.ACTZ_STATEMENTS`` moves on to describe the
CURRENT cumulative shape for the fresh-DB path, same as
``backend_schema_adapts.ADAPTS_SQL`` already does relative to v36.
"""

from __future__ import annotations

MIGRATION_V52: list[str] = [
    """CREATE TABLE IF NOT EXISTS actz (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        tz_ref TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN
            ('draft', 'sent', 'signed', 'superseded')),
        parent_actz TEXT REFERENCES actz(slug) ON DELETE SET NULL,
        delta_n INTEGER NOT NULL DEFAULT 0,
        supersession_rationale TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS actz_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actz_slug TEXT NOT NULL REFERENCES actz(slug) ON DELETE CASCADE,
        point_no INTEGER NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(actz_slug, point_no)
    )""",
    """CREATE TABLE IF NOT EXISTS actz_signatures (
        actz_slug TEXT NOT NULL REFERENCES actz(slug) ON DELETE CASCADE,
        role TEXT NOT NULL CHECK(role IN ('architect', 'client')),
        signed_by TEXT NOT NULL,
        signed_at TEXT NOT NULL,
        key_fingerprint TEXT,
        signature TEXT,
        PRIMARY KEY (actz_slug, role)
    )""",
    """CREATE TABLE IF NOT EXISTS actz_links (
        actz_slug TEXT NOT NULL REFERENCES actz(slug) ON DELETE CASCADE,
        target_type TEXT NOT NULL CHECK(target_type IN ('task', 'spec')),
        target_slug TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (actz_slug, target_type, target_slug)
    )""",
    """CREATE TABLE IF NOT EXISTS actz_decided_in (
        adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
        finding_id INTEGER NOT NULL REFERENCES adapt_findings(id) ON DELETE CASCADE,
        actz_slug TEXT NOT NULL,
        actz_point_no INTEGER NOT NULL,
        linked_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (adapt_slug, finding_id, actz_slug, actz_point_no),
        FOREIGN KEY (actz_slug, actz_point_no)
            REFERENCES actz_points(actz_slug, point_no) ON DELETE CASCADE
    )""",
    "CREATE INDEX IF NOT EXISTS idx_actz_parent ON actz(parent_actz)",
    "CREATE INDEX IF NOT EXISTS idx_actz_points_actz ON actz_points(actz_slug)",
    "CREATE INDEX IF NOT EXISTS idx_actz_links_target ON actz_links(target_type, target_slug)",
    "CREATE INDEX IF NOT EXISTS idx_actz_decided_in_adapt ON actz_decided_in(adapt_slug, finding_id)",
    "CREATE INDEX IF NOT EXISTS idx_actz_decided_in_actz ON actz_decided_in(actz_slug, actz_point_no)",
    """CREATE VIRTUAL TABLE IF NOT EXISTS fts_actz USING fts5(
        slug, title, tz_ref,
        content='actz', content_rowid='id'
    )""",
    """CREATE TRIGGER IF NOT EXISTS actz_ai AFTER INSERT ON actz BEGIN
        INSERT INTO fts_actz(rowid, slug, title, tz_ref)
        VALUES (new.id, new.slug, new.title, new.tz_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS actz_ad AFTER DELETE ON actz BEGIN
        INSERT INTO fts_actz(fts_actz, rowid, slug, title, tz_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS actz_au AFTER UPDATE ON actz BEGIN
        INSERT INTO fts_actz(fts_actz, rowid, slug, title, tz_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
        INSERT INTO fts_actz(rowid, slug, title, tz_ref)
        VALUES (new.id, new.slug, new.title, new.tz_ref);
    END""",
]
