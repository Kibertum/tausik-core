"""TAUSIK RAG — web search result cache with FTS5.

Caches web search results in SQLite to avoid repeated fetches.
Estimated savings: 60-80% on repeated queries within a session.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS web_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT,
    query TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT DEFAULT 'web_search',
    fetched_at TEXT NOT NULL,
    ttl_hours INTEGER DEFAULT 24,
    UNIQUE(query, url)
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_web USING fts5(
    query, content, source,
    content='web_cache', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS web_ai AFTER INSERT ON web_cache BEGIN
    INSERT INTO fts_web(rowid, query, content, source)
    VALUES (new.id, new.query, new.content, new.source);
END;

CREATE TRIGGER IF NOT EXISTS web_ad AFTER DELETE ON web_cache BEGIN
    INSERT INTO fts_web(fts_web, rowid, query, content, source)
    VALUES ('delete', old.id, old.query, old.content, old.source);
END;

CREATE TRIGGER IF NOT EXISTS web_au AFTER UPDATE ON web_cache BEGIN
    INSERT INTO fts_web(fts_web, rowid, query, content, source)
    VALUES ('delete', old.id, old.query, old.content, old.source);
    INSERT INTO fts_web(rowid, query, content, source)
    VALUES (new.id, new.query, new.content, new.source);
END;
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class WebCache:
    """FTS5-backed web search result cache."""

    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def store(
        self,
        query: str,
        content: str,
        url: str = "",
        source: str = "web_search",
        ttl_hours: int = 24,
    ) -> None:
        """Store a web search result. Replaces existing entry for same query+url."""
        self._conn.execute(
            """INSERT OR REPLACE INTO web_cache
               (url, query, content, source, fetched_at, ttl_hours)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (url, query, content, source, _utcnow(), ttl_hours),
        )
        self._conn.commit()

    def search(
        self, query: str, limit: int = 10, include_stale: bool = False
    ) -> list[dict[str, Any]]:
        """Search cached web results. Returns fresh results by default."""
        sanitized = self._sanitize_query(query)
        if not sanitized:
            return []
        try:
            rows = self._conn.execute(
                """SELECT w.id, w.url, w.query, w.content, w.source,
                          w.fetched_at, w.ttl_hours, rank
                   FROM fts_web fw
                   JOIN web_cache w ON w.id = fw.rowid
                   WHERE fts_web MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (sanitized, limit * 2),  # Fetch extra to filter stale
            ).fetchall()
        except sqlite3.OperationalError:
            rows = self._fallback_search(query, limit * 2)

        now = datetime.now(timezone.utc)
        results = []
        for r in rows:
            row = dict(r)
            try:
                fetched = datetime.fromisoformat(row["fetched_at"])
                age_hours = (now - fetched).total_seconds() / 3600
                row["stale"] = age_hours > row.get("ttl_hours", 24)
            except (ValueError, TypeError):
                row["stale"] = True

            if include_stale or not row["stale"]:
                results.append(row)
                if len(results) >= limit:
                    break
        return results

    def search_exact(self, query: str) -> dict[str, Any] | None:
        """Exact match on query string. Returns freshest result or None."""
        row = self._conn.execute(
            """SELECT * FROM web_cache
               WHERE query = ?
               ORDER BY fetched_at DESC LIMIT 1""",
            (query,),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        try:
            fetched = datetime.fromisoformat(result["fetched_at"])
            age_hours = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
            result["stale"] = age_hours > result.get("ttl_hours", 24)
        except (ValueError, TypeError):
            result["stale"] = True
        return result

    def cleanup_stale(self) -> int:
        """Remove expired entries. Returns count of deleted rows."""
        # SQLite doesn't have DATE_ADD, so we calculate in Python
        now = datetime.now(timezone.utc)
        rows = self._conn.execute(
            "SELECT id, fetched_at, ttl_hours FROM web_cache"
        ).fetchall()
        to_delete = []
        for r in rows:
            try:
                fetched = datetime.fromisoformat(r["fetched_at"])
                age_hours = (now - fetched).total_seconds() / 3600
                if age_hours > r["ttl_hours"] * 2:  # Delete after 2x TTL
                    to_delete.append(r["id"])
            except (ValueError, TypeError):
                to_delete.append(r["id"])
        if to_delete:
            placeholders = ",".join("?" * len(to_delete))
            self._conn.execute(
                f"DELETE FROM web_cache WHERE id IN ({placeholders})", to_delete
            )
            self._conn.commit()
        return len(to_delete)

    def status(self) -> dict[str, Any]:
        """Return cache statistics."""
        total = self._conn.execute("SELECT COUNT(*) as c FROM web_cache").fetchone()[
            "c"
        ]
        sources = self._conn.execute(
            "SELECT source, COUNT(*) as c FROM web_cache GROUP BY source"
        ).fetchall()
        return {
            "total_entries": total,
            "sources": {r["source"]: r["c"] for r in sources},
        }

    def _sanitize_query(self, query: str) -> str:
        """Make user query safe for FTS5 MATCH."""
        cleaned = []
        for ch in query:
            if ch.isalnum() or ch in " _.-/":
                cleaned.append(ch)
        words = "".join(cleaned).split()
        if not words:
            return ""
        return " OR ".join(f'"{w}"' for w in words[:10])

    def _fallback_search(self, query: str, limit: int) -> list[sqlite3.Row]:
        """LIKE-based fallback when FTS fails."""
        pattern = f"%{query}%"
        return self._conn.execute(
            """SELECT id, url, query, content, source, fetched_at, ttl_hours
               FROM web_cache
               WHERE content LIKE ? OR query LIKE ?
               ORDER BY fetched_at DESC
               LIMIT ?""",
            (pattern, pattern, limit),
        ).fetchall()
