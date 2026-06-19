"""Baseline DDL for RENAR ADAPT artifacts (v16r-adapt).

Kept out of backend_schema.py to hold that file under the 400-line filesize
gate. ``init_schema`` runs ADAPTS_SQL on the fresh-DB path; the migration path
(v36 in backend_migrations.py) builds the same objects for existing DBs.

The two DDL sources MUST stay byte-equivalent in structure — the v36 migration
test and the fresh-DB test both assert the same tables/triggers exist.
"""

from __future__ import annotations

ADAPTS_SQL = """
CREATE TABLE IF NOT EXISTS adapts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    tz_ref TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN
        ('draft', 'signed', 'superseded')),
    parent_adapt TEXT REFERENCES adapts(slug) ON DELETE SET NULL,
    delta_n INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS adapt_interpretations (
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
);

CREATE TABLE IF NOT EXISTS adapt_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK(category IN
        ('contradiction', 'gap', 'hidden-assumption', 'feasibility',
         'regulatory', 'terminology', 'scope')),
    description TEXT NOT NULL,
    tz_ref TEXT,
    resolution TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS adapt_signatures (
    adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('client', 'architect')),
    signed_by TEXT NOT NULL,
    signed_at TEXT NOT NULL,
    key_fingerprint TEXT,
    signature TEXT,
    PRIMARY KEY (adapt_slug, role)
);

CREATE TABLE IF NOT EXISTS adapt_links (
    adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
    target_type TEXT NOT NULL CHECK(target_type IN ('task', 'spec')),
    target_slug TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (adapt_slug, target_type, target_slug)
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_adapts USING fts5(
    slug, title, tz_ref,
    content='adapts', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS adapts_ai AFTER INSERT ON adapts BEGIN
    INSERT INTO fts_adapts(rowid, slug, title, tz_ref)
    VALUES (new.id, new.slug, new.title, new.tz_ref);
END;
CREATE TRIGGER IF NOT EXISTS adapts_ad AFTER DELETE ON adapts BEGIN
    INSERT INTO fts_adapts(fts_adapts, rowid, slug, title, tz_ref)
    VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
END;
CREATE TRIGGER IF NOT EXISTS adapts_au AFTER UPDATE ON adapts BEGIN
    INSERT INTO fts_adapts(fts_adapts, rowid, slug, title, tz_ref)
    VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
    INSERT INTO fts_adapts(rowid, slug, title, tz_ref)
    VALUES (new.id, new.slug, new.title, new.tz_ref);
END;

CREATE INDEX IF NOT EXISTS idx_adapts_parent ON adapts(parent_adapt);
CREATE INDEX IF NOT EXISTS idx_adapt_interp_adapt ON adapt_interpretations(adapt_slug);
CREATE INDEX IF NOT EXISTS idx_adapt_findings_adapt ON adapt_findings(adapt_slug);
CREATE INDEX IF NOT EXISTS idx_adapt_links_target ON adapt_links(target_type, target_slug);
"""
