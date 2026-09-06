"""v54 migration SQL -- RENAR AT (Acceptance Test) artifacts, ORIGINAL shape as shipped.

FROZEN, like backend_migrations_v52 (ACTZ) stayed frozen once v53 added a
column: v54 shipped as AT's only migration on the (correct, at the time)
premise that a brand-new entity has no history to be a delta against. v55
(at_results) proved that premise short-lived, so this module holds its own
independent copy of what it shipped, and backend_schema_at.AT_STATEMENTS
moves on to describe the CURRENT cumulative shape for the fresh-DB path.
"""

from __future__ import annotations

MIGRATION_V54: list[str] = [
    """CREATE TABLE IF NOT EXISTS ats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT NOT NULL UNIQUE,
        tz_ref TEXT NOT NULL,
        tz_text TEXT NOT NULL,
        scenario TEXT NOT NULL,
        source_as_of TEXT NOT NULL,
        generated_by TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_ats_tz_ref ON ats(tz_ref)",
    """CREATE VIRTUAL TABLE IF NOT EXISTS fts_ats USING fts5(
        slug, tz_ref, tz_text, scenario,
        content='ats', content_rowid='id'
    )""",
    """CREATE TRIGGER IF NOT EXISTS ats_ai AFTER INSERT ON ats BEGIN
        INSERT INTO fts_ats(rowid, slug, tz_ref, tz_text, scenario)
        VALUES (new.id, new.slug, new.tz_ref, new.tz_text, new.scenario);
    END""",
    """CREATE TRIGGER IF NOT EXISTS ats_ad AFTER DELETE ON ats BEGIN
        INSERT INTO fts_ats(fts_ats, rowid, slug, tz_ref, tz_text, scenario)
        VALUES ('delete', old.id, old.slug, old.tz_ref, old.tz_text, old.scenario);
    END""",
    """CREATE TRIGGER IF NOT EXISTS ats_au AFTER UPDATE ON ats BEGIN
        INSERT INTO fts_ats(fts_ats, rowid, slug, tz_ref, tz_text, scenario)
        VALUES ('delete', old.id, old.slug, old.tz_ref, old.tz_text, old.scenario);
        INSERT INTO fts_ats(rowid, slug, tz_ref, tz_text, scenario)
        VALUES (new.id, new.slug, new.tz_ref, new.tz_text, new.scenario);
    END""",
]
