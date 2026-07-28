"""TAUSIK RAG — FTS5 SQLite storage for code chunks.

Zero external dependencies. Always available as baseline search.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS rag_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    language TEXT,
    start_line INTEGER,
    end_line INTEGER,
    chunk_type TEXT DEFAULT 'code',
    context_prefix TEXT DEFAULT '',
    indexed_at TEXT NOT NULL,
    UNIQUE(file_path, chunk_index)
);

CREATE TABLE IF NOT EXISTS rag_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_code USING fts5(
    file_path, content, language, context_prefix,
    content='rag_chunks', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS rag_ai AFTER INSERT ON rag_chunks BEGIN
    INSERT INTO fts_code(rowid, file_path, content, language, context_prefix)
    VALUES (new.id, new.file_path, new.content, new.language, new.context_prefix);
END;

CREATE TRIGGER IF NOT EXISTS rag_ad AFTER DELETE ON rag_chunks BEGIN
    INSERT INTO fts_code(fts_code, rowid, file_path, content, language, context_prefix)
    VALUES ('delete', old.id, old.file_path, old.content, old.language, old.context_prefix);
END;

CREATE TRIGGER IF NOT EXISTS rag_au AFTER UPDATE ON rag_chunks BEGIN
    INSERT INTO fts_code(fts_code, rowid, file_path, content, language, context_prefix)
    VALUES ('delete', old.id, old.file_path, old.content, old.language, old.context_prefix);
    INSERT INTO fts_code(rowid, file_path, content, language, context_prefix)
    VALUES (new.id, new.file_path, new.content, new.language, new.context_prefix);
END;
"""

# Bumped when the physical layout changes in a way an existing rag.db cannot
# simply grow into. v2 added the context_prefix column plus an FTS column for
# it — `CREATE TABLE IF NOT EXISTS` is silent on an existing table, so without
# an explicit step an upgraded install would keep the old index forever and the
# feature would appear to do nothing.
SCHEMA_VERSION = 2


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RAGStore:
    """FTS5-backed code search index."""

    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        migrated = self._migrate_legacy_layout()
        self._conn.executescript(SCHEMA)
        if migrated:
            # SCHEMA recreated fts_code empty; refill it from the chunks, which
            # are the source of truth. Without this the store would answer every
            # query with nothing until the next full reindex.
            self._conn.execute("INSERT INTO fts_code(fts_code) VALUES ('rebuild')")
        self._conn.execute(
            "INSERT OR REPLACE INTO rag_meta(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._conn.commit()

    def _migrate_legacy_layout(self) -> bool:
        """Grow a pre-v2 database into the current layout, in place.

        Only the FTS index is rebuilt — it is derived data, recomputable from
        `rag_chunks` at any time, so this cannot lose anything. Chunk rows keep
        an empty `context_prefix` until the next reindex fills it, which
        degrades to exactly the old behaviour rather than to a broken one.
        """
        cur = self._conn.cursor()
        tables = {
            row[0]
            for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "rag_chunks" not in tables:
            return False  # fresh database — SCHEMA creates the current layout directly
        columns = {row[1] for row in cur.execute("PRAGMA table_info(rag_chunks)").fetchall()}
        if "context_prefix" in columns:
            return False
        cur.execute("ALTER TABLE rag_chunks ADD COLUMN context_prefix TEXT DEFAULT ''")
        # The triggers reference the old FTS column list; drop both so the
        # SCHEMA script recreates them in step with each other.
        for trigger in ("rag_ai", "rag_ad", "rag_au"):
            cur.execute(f"DROP TRIGGER IF EXISTS {trigger}")
        cur.execute("DROP TABLE IF EXISTS fts_code")
        self._conn.commit()
        return True

    def close(self) -> None:
        self._conn.close()

    # --- Chunk operations ---

    def upsert_file(self, file_path: str, chunks: list[dict[str, Any]]) -> int:
        """Replace all chunks for a file. Returns number of chunks inserted."""
        cur = self._conn.cursor()
        # Delete old chunks for this file
        cur.execute("DELETE FROM rag_chunks WHERE file_path=?", (file_path,))
        now = _utcnow()
        for chunk in chunks:
            cur.execute(
                """INSERT INTO rag_chunks
                   (file_path, chunk_index, content, language, start_line, end_line,
                    chunk_type, context_prefix, indexed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    file_path,
                    chunk["chunk_index"],
                    chunk["content"],
                    chunk.get("language"),
                    chunk.get("start_line"),
                    chunk.get("end_line"),
                    chunk.get("chunk_type", "code"),
                    chunk.get("context_prefix", ""),
                    now,
                ),
            )
        self._conn.commit()
        return len(chunks)

    def delete_file(self, file_path: str) -> None:
        """Remove all chunks for a deleted file."""
        self._conn.execute("DELETE FROM rag_chunks WHERE file_path=?", (file_path,))
        self._conn.commit()

    def clear(self) -> None:
        """Drop all indexed data."""
        self._conn.execute("DELETE FROM rag_chunks")
        self._conn.execute("DELETE FROM rag_meta")
        self._conn.commit()

    # --- Search ---

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Full-text search across indexed code. Returns ranked results."""
        # Sanitize query for FTS5: strip special chars, add prefix matching
        sanitized = self._sanitize_query(query)
        if not sanitized:
            return []
        try:
            rows = self._conn.execute(
                """SELECT r.file_path, r.content, r.language,
                          r.start_line, r.end_line, r.chunk_type,
                          rank
                   FROM fts_code fc
                   JOIN rag_chunks r ON r.id = fc.rowid
                   WHERE fts_code MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (sanitized, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # Fallback: try LIKE search if FTS fails
            return self._fallback_search(query, limit)
        return [dict(r) for r in rows]

    def _sanitize_query(self, query: str) -> str:
        """Make user query safe for FTS5 MATCH."""
        # Remove FTS5 operators and special chars
        cleaned = []
        for ch in query:
            if ch.isalnum() or ch in " _.-/":
                cleaned.append(ch)
        words = "".join(cleaned).split()
        if not words:
            return ""
        # Each word as prefix match, combined with OR for broader results
        return " OR ".join(f'"{w}"' for w in words[:10])

    def _fallback_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        """LIKE-based fallback when FTS query fails."""
        pattern = f"%{query}%"
        rows = self._conn.execute(
            """SELECT file_path, content, language, start_line, end_line, chunk_type
               FROM rag_chunks
               WHERE content LIKE ? OR file_path LIKE ?
               ORDER BY file_path
               LIMIT ?""",
            (pattern, pattern, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Metadata ---

    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM rag_meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO rag_meta(key, value) VALUES(?, ?)",
            (key, value),
        )
        self._conn.commit()

    # --- Status ---

    def status(self) -> dict[str, Any]:
        """Return index statistics."""
        total_chunks = self._conn.execute("SELECT COUNT(*) as c FROM rag_chunks").fetchone()["c"]
        total_files = self._conn.execute(
            "SELECT COUNT(DISTINCT file_path) as c FROM rag_chunks"
        ).fetchone()["c"]
        languages = self._conn.execute(
            "SELECT language, COUNT(*) as c FROM rag_chunks GROUP BY language ORDER BY c DESC"
        ).fetchall()
        return {
            "mode": "fts5",
            "total_chunks": total_chunks,
            "total_files": total_files,
            "last_commit": self.get_meta("last_commit"),
            "last_indexed": self.get_meta("last_indexed"),
            "languages": {r["language"]: r["c"] for r in languages if r["language"]},
        }
