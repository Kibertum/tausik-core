"""v35 migration SQL — RENAR SPEC artifacts (v16r-spec-types).

Held in its own module to keep backend_migrations.py under the 400-line
filesize gate. ``MIGRATION_V35`` is the ordered statement list referenced by
backend_migrations._CURRENT_MIGRATIONS[35]. Purely additive — new tables only,
no ALTER on any existing table.
"""

from __future__ import annotations

MIGRATION_V35: list[str] = [
    """CREATE TABLE IF NOT EXISTS specs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL CHECK(type IN
            ('ARCH', 'API', 'DATA', 'INT', 'PROC', 'UI', 'AI', 'SEC', 'OPS')),
        title TEXT NOT NULL,
        content_ref TEXT,
        version TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN
            ('draft', 'active', 'deprecated')),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS task_specs (
        task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
        spec_slug TEXT NOT NULL REFERENCES specs(slug) ON DELETE CASCADE,
        relation TEXT NOT NULL DEFAULT 'implements' CHECK(relation IN
            ('implements', 'constrained_by')),
        created_at TEXT NOT NULL,
        PRIMARY KEY (task_slug, spec_slug, relation)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_specs_type ON specs(type)",
    "CREATE INDEX IF NOT EXISTS idx_task_specs_spec ON task_specs(spec_slug)",
    """CREATE VIRTUAL TABLE IF NOT EXISTS fts_specs USING fts5(
        slug, title, content_ref,
        content='specs', content_rowid='id'
    )""",
    """CREATE TRIGGER IF NOT EXISTS specs_ai AFTER INSERT ON specs BEGIN
        INSERT INTO fts_specs(rowid, slug, title, content_ref)
        VALUES (new.id, new.slug, new.title, new.content_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS specs_ad AFTER DELETE ON specs BEGIN
        INSERT INTO fts_specs(fts_specs, rowid, slug, title, content_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.content_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS specs_au AFTER UPDATE ON specs BEGIN
        INSERT INTO fts_specs(fts_specs, rowid, slug, title, content_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.content_ref);
        INSERT INTO fts_specs(rowid, slug, title, content_ref)
        VALUES (new.id, new.slug, new.title, new.content_ref);
    END""",
]
