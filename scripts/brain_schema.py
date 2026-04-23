"""TAUSIK brain database schema — shared cross-project knowledge.

Local SQLite mirror of 4 Notion databases (decisions, web_cache,
patterns, gotchas) persisted at ~/.tausik-brain/brain.db.

Mirror is read-optimized: writes go to Notion first, pull-sync mirrors
pages into local FTS5 index for fast offline search.

Design reference: references/brain-db-schema.md
"""

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS brain_meta (
    key TEXT PRIMARY KEY, value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brain_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notion_page_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    context TEXT,
    decision TEXT,
    rationale TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    stack TEXT NOT NULL DEFAULT '[]',
    date_value TEXT,
    source_project_hash TEXT NOT NULL,
    generalizable INTEGER NOT NULL DEFAULT 1
        CHECK(generalizable IN (0, 1)),
    superseded_by TEXT,
    last_edited_time TEXT NOT NULL,
    created_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brain_web_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notion_page_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    url TEXT,
    query TEXT,
    content TEXT,
    fetched_at TEXT NOT NULL,
    ttl_days INTEGER NOT NULL DEFAULT 30,
    domain TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    source_project_hash TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    last_edited_time TEXT NOT NULL,
    created_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brain_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notion_page_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    when_to_use TEXT,
    example TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    stack TEXT NOT NULL DEFAULT '[]',
    source_project_hash TEXT NOT NULL,
    date_value TEXT,
    confidence TEXT
        CHECK(confidence IS NULL OR confidence IN
              ('experimental', 'tested', 'proven')),
    last_edited_time TEXT NOT NULL,
    created_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brain_gotchas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notion_page_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    wrong_way TEXT,
    right_way TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    stack TEXT NOT NULL DEFAULT '[]',
    source_project_hash TEXT NOT NULL,
    date_value TEXT,
    severity TEXT
        CHECK(severity IS NULL OR severity IN ('low', 'medium', 'high')),
    evidence_url TEXT,
    last_edited_time TEXT NOT NULL,
    created_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_state (
    category TEXT PRIMARY KEY
        CHECK(category IN ('decisions', 'web_cache', 'patterns', 'gotchas')),
    last_pull_at TEXT,
    last_error TEXT,
    last_error_at TEXT
);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_brain_decisions USING fts5(
    name, context, decision, rationale, tags,
    content='brain_decisions', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_brain_web_cache USING fts5(
    name, url, query, content, domain, tags,
    content='brain_web_cache', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_brain_patterns USING fts5(
    name, description, when_to_use, example, tags,
    content='brain_patterns', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_brain_gotchas USING fts5(
    name, description, wrong_way, right_way, tags,
    content='brain_gotchas', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
"""

FTS_TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS brain_decisions_ai
AFTER INSERT ON brain_decisions BEGIN
    INSERT INTO fts_brain_decisions(rowid, name, context, decision, rationale, tags)
    VALUES (new.id, new.name, new.context, new.decision, new.rationale, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS brain_decisions_ad
AFTER DELETE ON brain_decisions BEGIN
    INSERT INTO fts_brain_decisions(fts_brain_decisions, rowid, name, context, decision, rationale, tags)
    VALUES ('delete', old.id, old.name, old.context, old.decision, old.rationale, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS brain_decisions_au
AFTER UPDATE ON brain_decisions BEGIN
    INSERT INTO fts_brain_decisions(fts_brain_decisions, rowid, name, context, decision, rationale, tags)
    VALUES ('delete', old.id, old.name, old.context, old.decision, old.rationale, old.tags);
    INSERT INTO fts_brain_decisions(rowid, name, context, decision, rationale, tags)
    VALUES (new.id, new.name, new.context, new.decision, new.rationale, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS brain_web_cache_ai
AFTER INSERT ON brain_web_cache BEGIN
    INSERT INTO fts_brain_web_cache(rowid, name, url, query, content, domain, tags)
    VALUES (new.id, new.name, new.url, new.query, new.content, new.domain, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS brain_web_cache_ad
AFTER DELETE ON brain_web_cache BEGIN
    INSERT INTO fts_brain_web_cache(fts_brain_web_cache, rowid, name, url, query, content, domain, tags)
    VALUES ('delete', old.id, old.name, old.url, old.query, old.content, old.domain, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS brain_web_cache_au
AFTER UPDATE ON brain_web_cache BEGIN
    INSERT INTO fts_brain_web_cache(fts_brain_web_cache, rowid, name, url, query, content, domain, tags)
    VALUES ('delete', old.id, old.name, old.url, old.query, old.content, old.domain, old.tags);
    INSERT INTO fts_brain_web_cache(rowid, name, url, query, content, domain, tags)
    VALUES (new.id, new.name, new.url, new.query, new.content, new.domain, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS brain_patterns_ai
AFTER INSERT ON brain_patterns BEGIN
    INSERT INTO fts_brain_patterns(rowid, name, description, when_to_use, example, tags)
    VALUES (new.id, new.name, new.description, new.when_to_use, new.example, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS brain_patterns_ad
AFTER DELETE ON brain_patterns BEGIN
    INSERT INTO fts_brain_patterns(fts_brain_patterns, rowid, name, description, when_to_use, example, tags)
    VALUES ('delete', old.id, old.name, old.description, old.when_to_use, old.example, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS brain_patterns_au
AFTER UPDATE ON brain_patterns BEGIN
    INSERT INTO fts_brain_patterns(fts_brain_patterns, rowid, name, description, when_to_use, example, tags)
    VALUES ('delete', old.id, old.name, old.description, old.when_to_use, old.example, old.tags);
    INSERT INTO fts_brain_patterns(rowid, name, description, when_to_use, example, tags)
    VALUES (new.id, new.name, new.description, new.when_to_use, new.example, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS brain_gotchas_ai
AFTER INSERT ON brain_gotchas BEGIN
    INSERT INTO fts_brain_gotchas(rowid, name, description, wrong_way, right_way, tags)
    VALUES (new.id, new.name, new.description, new.wrong_way, new.right_way, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS brain_gotchas_ad
AFTER DELETE ON brain_gotchas BEGIN
    INSERT INTO fts_brain_gotchas(fts_brain_gotchas, rowid, name, description, wrong_way, right_way, tags)
    VALUES ('delete', old.id, old.name, old.description, old.wrong_way, old.right_way, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS brain_gotchas_au
AFTER UPDATE ON brain_gotchas BEGIN
    INSERT INTO fts_brain_gotchas(fts_brain_gotchas, rowid, name, description, wrong_way, right_way, tags)
    VALUES ('delete', old.id, old.name, old.description, old.wrong_way, old.right_way, old.tags);
    INSERT INTO fts_brain_gotchas(rowid, name, description, wrong_way, right_way, tags)
    VALUES (new.id, new.name, new.description, new.wrong_way, new.right_way, new.tags);
END;
"""

INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_brain_decisions_last_edited
    ON brain_decisions(last_edited_time);
CREATE INDEX IF NOT EXISTS idx_brain_decisions_project
    ON brain_decisions(source_project_hash);
CREATE INDEX IF NOT EXISTS idx_brain_decisions_date
    ON brain_decisions(date_value);

CREATE INDEX IF NOT EXISTS idx_brain_web_cache_last_edited
    ON brain_web_cache(last_edited_time);
CREATE INDEX IF NOT EXISTS idx_brain_web_cache_project
    ON brain_web_cache(source_project_hash);
CREATE INDEX IF NOT EXISTS idx_brain_web_cache_content_hash
    ON brain_web_cache(content_hash);
CREATE INDEX IF NOT EXISTS idx_brain_web_cache_fetched
    ON brain_web_cache(fetched_at);

CREATE INDEX IF NOT EXISTS idx_brain_patterns_last_edited
    ON brain_patterns(last_edited_time);
CREATE INDEX IF NOT EXISTS idx_brain_patterns_project
    ON brain_patterns(source_project_hash);
CREATE INDEX IF NOT EXISTS idx_brain_patterns_date
    ON brain_patterns(date_value);

CREATE INDEX IF NOT EXISTS idx_brain_gotchas_last_edited
    ON brain_gotchas(last_edited_time);
CREATE INDEX IF NOT EXISTS idx_brain_gotchas_project
    ON brain_gotchas(source_project_hash);
CREATE INDEX IF NOT EXISTS idx_brain_gotchas_date
    ON brain_gotchas(date_value);
"""


def apply_schema(conn):
    """Apply DDL to a sqlite3.Connection. Idempotent (uses IF NOT EXISTS)."""
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    cur.executescript(FTS_SQL)
    cur.executescript(FTS_TRIGGERS_SQL)
    cur.executescript(INDEXES_SQL)
    cur.execute(
        "INSERT OR IGNORE INTO brain_meta(key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
