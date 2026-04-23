"""Tests for scripts/brain_fallback.py — error classification + user messages."""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_fallback  # noqa: E402
from brain_notion_client import (  # noqa: E402
    NotionAuthError,
    NotionError,
    NotionNetworkError,
    NotionNotFoundError,
    NotionRateLimitError,
    NotionServerError,
)


# --- classify_error -------------------------------------------------------


def test_classify_auth():
    assert brain_fallback.classify_error(NotionAuthError("bad token")) == "auth"


def test_classify_not_found():
    assert brain_fallback.classify_error(NotionNotFoundError("gone")) == "not_found"


def test_classify_rate_limit():
    assert (
        brain_fallback.classify_error(NotionRateLimitError("slow down")) == "rate_limit"
    )


def test_classify_server():
    assert brain_fallback.classify_error(NotionServerError("5xx")) == "server"


def test_classify_network_by_type():
    """NotionNetworkError always classifies as 'network' regardless of message."""
    assert (
        brain_fallback.classify_error(NotionNetworkError("Connection refused"))
        == "network"
    )
    assert (
        brain_fallback.classify_error(NotionNetworkError("getaddrinfo failed"))
        == "network"
    )
    assert (
        brain_fallback.classify_error(NotionNetworkError("totally unfamiliar"))
        == "network"
    )


def test_classify_unknown_notion_error():
    assert brain_fallback.classify_error(NotionError("weird")) == "unknown"


def test_classify_non_notion_error():
    assert brain_fallback.classify_error(ValueError("boom")) == "unknown"


# --- user_message --------------------------------------------------------


def test_user_message_auth_mentions_init():
    msg = brain_fallback.user_message("auth", op="store")
    assert "brain init" in msg
    assert "token" in msg.lower()


def test_user_message_not_found_suggests_force_reinit():
    msg = brain_fallback.user_message("not_found", op="get")
    assert "brain init" in msg
    assert "force" in msg


def test_user_message_rate_limit_defaults_to_60s():
    msg = brain_fallback.user_message("rate_limit", op="search")
    assert "Retry in 60 seconds" in msg


def test_user_message_rate_limit_honors_retry_after():
    msg = brain_fallback.user_message("rate_limit", op="search", retry_after=15)
    assert "Retry in 15 seconds" in msg


def test_user_message_rejects_unknown_op():
    with pytest.raises(ValueError):
        brain_fallback.user_message("auth", op="typo")  # type: ignore[arg-type]


def test_retry_after_from_attached_attribute():
    exc = NotionRateLimitError("429")
    exc.retry_after = 42
    assert brain_fallback.retry_after_from(exc) == 42


def test_retry_after_from_default_is_none():
    assert brain_fallback.retry_after_from(NotionRateLimitError("429")) is None


def test_user_message_network_store_says_not_persisted():
    msg = brain_fallback.user_message("network", op="store")
    assert "not persisted" in msg or "Network unavailable" in msg


def test_user_message_network_search_says_local_only():
    msg = brain_fallback.user_message("network", op="search")
    assert "local mirror" in msg.lower() or "Offline" in msg


def test_user_message_server_mentions_retry():
    msg = brain_fallback.user_message("server", op="store")
    assert "server" in msg.lower() or "retry" in msg.lower()


def test_user_message_unknown_includes_detail():
    msg = brain_fallback.user_message("unknown", op="store", detail="weird thing")
    assert "weird thing" in msg


# --- integration: store_record uses classifier ---------------------------


def test_store_record_returns_category_for_auth_error(tmp_path, monkeypatch):
    """brain_mcp_write.store_record tags Notion errors with a category for format_store_result."""
    import sqlite3

    import brain_mcp_write
    import brain_schema

    # Minimal cfg + conn stubs
    conn = sqlite3.connect(":memory:")
    brain_schema.apply_schema(conn)

    class _AuthClient:
        def pages_create(self, **_k):
            raise NotionAuthError("bad token")

    cfg = {
        "enabled": True,
        "database_ids": {"decisions": "db1"},
        "project_names": [],
    }
    monkeypatch.setattr("os.getcwd", lambda: str(tmp_path))

    result = brain_mcp_write.store_record(
        _AuthClient(),
        conn,
        "decisions",
        {
            "name": "x",
            "context": "c",
            "decision": "d",
            "rationale": "r",
            "date": "2026-04-23",
        },
        cfg,
        project_name="test-proj",
    )

    assert result["status"] == "notion_error"
    assert result["error_category"] == "auth"


def test_format_store_result_renders_auth_friendly_message():
    import brain_mcp_write

    rendered = brain_mcp_write.format_store_result(
        {"status": "notion_error", "error_category": "auth", "error": "bad token"},
        "decisions",
    )
    assert "brain init" in rendered
    assert "token" in rendered.lower()


def test_format_store_result_network_error_says_not_persisted():
    import brain_mcp_write

    rendered = brain_mcp_write.format_store_result(
        {
            "status": "notion_error",
            "error_category": "network",
            "error": "timed out",
        },
        "patterns",
    )
    assert "not persisted" in rendered or "Network unavailable" in rendered


def test_format_store_result_rate_limit_with_retry_after():
    import brain_mcp_write

    rendered = brain_mcp_write.format_store_result(
        {
            "status": "notion_error",
            "error_category": "rate_limit",
            "error": "429",
            "retry_after": 20,
        },
        "gotchas",
    )
    assert "Retry in 20 seconds" in rendered


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
