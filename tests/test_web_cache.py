"""Tests for rag_web_cache — web search result caching with FTS5."""

from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "agents", "claude", "mcp", "codebase-rag"
    ),
)

from rag_web_cache import WebCache


class TestWebCacheStore:
    def test_store_and_search(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        cache.store(
            "python async", "asyncio is the standard library for async IO in Python"
        )
        results = cache.search("python async")
        assert len(results) >= 1
        assert "asyncio" in results[0]["content"]
        cache.close()

    def test_store_replaces_existing(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        cache.store("test query", "old content")
        cache.store("test query", "new content")
        results = cache.search("test query")
        assert len(results) == 1
        assert "new" in results[0]["content"]
        cache.close()

    def test_store_with_url(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        cache.store("docs", "Python docs", url="https://docs.python.org")
        results = cache.search("docs")
        assert results[0]["url"] == "https://docs.python.org"
        cache.close()


class TestWebCacheSearch:
    def test_empty_cache(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        results = cache.search("anything")
        assert results == []
        cache.close()

    def test_empty_query(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        cache.store("test", "content")
        results = cache.search("")
        assert results == []
        cache.close()

    def test_search_exact(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        cache.store("exact query", "exact content")
        result = cache.search_exact("exact query")
        assert result is not None
        assert result["content"] == "exact content"
        cache.close()

    def test_search_exact_miss(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        result = cache.search_exact("nonexistent")
        assert result is None
        cache.close()

    def test_multiple_results(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        cache.store("python tutorial", "beginner python guide")
        cache.store(
            "python advanced", "advanced python patterns", url="https://example.com"
        )
        results = cache.search("python")
        assert len(results) >= 2
        cache.close()


class TestWebCacheTTL:
    def test_fresh_result_not_stale(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        cache.store("fresh", "fresh content", ttl_hours=24)
        results = cache.search("fresh")
        assert len(results) == 1
        assert results[0]["stale"] is False
        cache.close()

    def test_stale_excluded_by_default(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        # Store with 0 TTL (immediately stale)
        cache.store("stale query", "stale content", ttl_hours=0)
        # Hack: update fetched_at to 2 hours ago
        cache._conn.execute(
            "UPDATE web_cache SET fetched_at = datetime('now', '-2 hours')"
        )
        cache._conn.commit()
        results = cache.search("stale query", include_stale=False)
        assert len(results) == 0
        cache.close()

    def test_stale_included_when_requested(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        cache.store("stale query", "stale content", ttl_hours=0)
        cache._conn.execute(
            "UPDATE web_cache SET fetched_at = datetime('now', '-2 hours')"
        )
        cache._conn.commit()
        results = cache.search("stale query", include_stale=True)
        assert len(results) >= 1
        cache.close()


class TestWebCacheCleanup:
    def test_cleanup_removes_old(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        cache.store("old", "old content", ttl_hours=1)
        # Set fetched_at to 3 hours ago (> 2x TTL)
        cache._conn.execute(
            "UPDATE web_cache SET fetched_at = datetime('now', '-3 hours')"
        )
        cache._conn.commit()
        removed = cache.cleanup_stale()
        assert removed == 1
        assert cache.search("old", include_stale=True) == []
        cache.close()

    def test_cleanup_keeps_fresh(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        cache.store("fresh", "fresh content", ttl_hours=24)
        removed = cache.cleanup_stale()
        assert removed == 0
        cache.close()


class TestWebCacheStatus:
    def test_empty_status(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        status = cache.status()
        assert status["total_entries"] == 0
        cache.close()

    def test_status_with_data(self, tmp_path):
        cache = WebCache(str(tmp_path / "cache.db"))
        cache.store("q1", "c1", source="web_search")
        cache.store("q2", "c2", source="web_fetch")
        status = cache.status()
        assert status["total_entries"] == 2
        assert "web_search" in status["sources"]
        assert "web_fetch" in status["sources"]
        cache.close()
