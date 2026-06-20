"""v36 migration SQL — RENAR ADAPT artifacts (v16r-adapt full §7).

Held in its own module to keep backend_migrations.py under the 400-line
filesize gate. ``MIGRATION_V36`` is the ordered statement list referenced by
backend_migrations._CURRENT_MIGRATIONS[36]. Purely additive — new tables only,
no ALTER on any existing table.

ADAPT = forward interpretation (§7.4.3) + 7 closed-list backward findings (§7) +
dual signature (§7.5) + delta workflow (§7.6). The 7 finding categories and the
2 signature roles are CLOSED lists enforced by table CHECK constraints — a new
value requires a renar.tech standard amendment, never a free-text insert.
"""

from __future__ import annotations

MIGRATION_V36: list[str] = [
    """CREATE TABLE IF NOT EXISTS adapts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        tz_ref TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN
            ('draft', 'signed', 'superseded')),
        -- parent_adapt: self-ref for the delta chain (§7.6). ON DELETE SET NULL
        -- so deleting one ADAPT never cascade-wipes a whole delta chain; an
        -- orphaned delta keeps delta_n>0 as the audit trail of its lineage.
        parent_adapt TEXT REFERENCES adapts(slug) ON DELETE SET NULL,
        delta_n INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS adapt_interpretations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
        tz_ref TEXT NOT NULL,
        citation TEXT NOT NULL,
        engineering_interpretation TEXT NOT NULL,
        term_mapping TEXT,
        scenarios TEXT,
        scope_in TEXT NOT NULL,
        scope_out TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS adapt_findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
        category TEXT NOT NULL CHECK(category IN
            ('contradiction', 'gap', 'hidden-assumption', 'feasibility',
             'regulatory', 'terminology', 'scope')),
        description TEXT NOT NULL,
        tz_ref TEXT,
        resolution TEXT,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS adapt_signatures (
        adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
        role TEXT NOT NULL CHECK(role IN ('client', 'architect')),
        signed_by TEXT NOT NULL,
        signed_at TEXT NOT NULL,
        key_fingerprint TEXT,
        signature TEXT,
        PRIMARY KEY (adapt_slug, role)
    )""",
    """CREATE TABLE IF NOT EXISTS adapt_links (
        adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
        -- Polymorphic target (task|spec): SQLite has no FK on a type-discriminated
        -- column, so target existence is validated in the service layer
        -- (adapt_link) — there is no hard FK on target_slug by design.
        target_type TEXT NOT NULL CHECK(target_type IN ('task', 'spec')),
        target_slug TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (adapt_slug, target_type, target_slug)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_adapts_parent ON adapts(parent_adapt)",
    "CREATE INDEX IF NOT EXISTS idx_adapt_interp_adapt ON adapt_interpretations(adapt_slug)",
    "CREATE INDEX IF NOT EXISTS idx_adapt_findings_adapt ON adapt_findings(adapt_slug)",
    "CREATE INDEX IF NOT EXISTS idx_adapt_links_target ON adapt_links(target_type, target_slug)",
    """CREATE VIRTUAL TABLE IF NOT EXISTS fts_adapts USING fts5(
        slug, title, tz_ref,
        content='adapts', content_rowid='id'
    )""",
    """CREATE TRIGGER IF NOT EXISTS adapts_ai AFTER INSERT ON adapts BEGIN
        INSERT INTO fts_adapts(rowid, slug, title, tz_ref)
        VALUES (new.id, new.slug, new.title, new.tz_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS adapts_ad AFTER DELETE ON adapts BEGIN
        INSERT INTO fts_adapts(fts_adapts, rowid, slug, title, tz_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS adapts_au AFTER UPDATE ON adapts BEGIN
        INSERT INTO fts_adapts(fts_adapts, rowid, slug, title, tz_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
        INSERT INTO fts_adapts(rowid, slug, title, tz_ref)
        VALUES (new.id, new.slug, new.title, new.tz_ref);
    END""",
]
