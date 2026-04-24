"""Tests for brain_runtime.try_brain_write_web_cache.

Covers the contract: returns (True, page_id) on ok/ok_not_mirrored,
(False, reason) on token missing / scrub block / notion error / empty
input / bad config. Mocks store_record to drive status variants without
hitting the network.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_runtime  # noqa: E402


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBCACHE_FAKE_TOKEN", "tok-abc")
    return {
        "enabled": True,
        "local_mirror_path": str(tmp_path / "brain.db"),
        "notion_integration_token_env": "WEBCACHE_FAKE_TOKEN",
        "database_ids": {
            "decisions": "dec",
            "web_cache": "wc",
            "patterns": "pat",
            "gotchas": "got",
        },
        "project_names": [],
        "private_url_patterns": [],
        "ttl_web_cache_days": 30,
    }


def test_ok_returns_true_and_page_id(cfg):
    with (
        patch(
            "brain_notion_client.NotionClient",
            autospec=True,
        ),
        patch(
            "brain_mcp_write.store_record",
            return_value={"status": "ok", "notion_page_id": "page-xyz"},
        ) as mock_store,
    ):
        ok, ret = brain_runtime.try_brain_write_web_cache(
            "https://example.com/a",
            "content body",
            cfg,
            query="search me",
        )
    assert ok is True
    assert ret == "page-xyz"
    # fields passed through correctly
    (_client, _conn, category, fields, _cfg) = mock_store.call_args.args
    assert category == "web_cache"
    assert fields["url"] == "https://example.com/a"
    assert fields["content"] == "content body"
    assert fields["query"] == "search me"
    assert fields["ttl_days"] == 30


def test_ok_not_mirrored_returns_true(cfg):
    with (
        patch("brain_notion_client.NotionClient", autospec=True),
        patch(
            "brain_mcp_write.store_record",
            return_value={
                "status": "ok_not_mirrored",
                "notion_page_id": "page-partial",
                "warning": "local disk full",
            },
        ),
    ):
        ok, ret = brain_runtime.try_brain_write_web_cache(
            "https://example.com/a", "body", cfg
        )
    assert ok is True
    assert ret == "page-partial"


def test_scrub_blocked_returns_false_with_detector_names(cfg):
    with (
        patch("brain_notion_client.NotionClient", autospec=True),
        patch(
            "brain_mcp_write.store_record",
            return_value={
                "status": "scrub_blocked",
                "issues": [
                    {
                        "detector": "private_urls",
                        "severity": "block",
                        "match": "some-secret.internal",
                        "hint": "",
                    },
                    {
                        "detector": "project_names_blocklist",
                        "severity": "block",
                        "match": "competitor-x",
                        "hint": "",
                    },
                ],
            },
        ),
    ):
        ok, reason = brain_runtime.try_brain_write_web_cache(
            "https://some-secret.internal/x", "body", cfg
        )
    assert ok is False
    assert "scrub_blocked" in reason
    # Raw `match` values must not leak into the reason.
    assert "some-secret.internal" not in reason
    assert "competitor-x" not in reason
    # Detector names appear (sorted).
    assert "private_urls" in reason
    assert "project_names_blocklist" in reason


def test_scrub_blocked_without_issues(cfg):
    """Edge case: scrub_blocked with an empty issues list — shouldn't crash."""
    with (
        patch("brain_notion_client.NotionClient", autospec=True),
        patch(
            "brain_mcp_write.store_record",
            return_value={"status": "scrub_blocked", "issues": []},
        ),
    ):
        ok, reason = brain_runtime.try_brain_write_web_cache(
            "https://x.example", "body", cfg
        )
    assert ok is False
    assert "matched patterns" in reason


def test_notion_error_returns_false(cfg):
    with (
        patch("brain_notion_client.NotionClient", autospec=True),
        patch(
            "brain_mcp_write.store_record",
            return_value={
                "status": "notion_error",
                "error": "503 Service Unavailable",
                "error_category": "transient",
            },
        ),
    ):
        ok, reason = brain_runtime.try_brain_write_web_cache(
            "https://x.example", "body", cfg
        )
    assert ok is False
    assert "notion_error" in reason
    assert "503" in reason


def test_token_missing_returns_false(tmp_path, monkeypatch):
    monkeypatch.delenv("WEBCACHE_NO_SUCH_TOKEN", raising=False)
    cfg = {
        "enabled": True,
        "local_mirror_path": str(tmp_path / "brain.db"),
        "notion_integration_token_env": "WEBCACHE_NO_SUCH_TOKEN",
        "database_ids": {
            "decisions": "dec",
            "web_cache": "wc",
            "patterns": "pat",
            "gotchas": "got",
        },
    }
    ok, reason = brain_runtime.try_brain_write_web_cache(
        "https://x.example", "body", cfg
    )
    assert ok is False
    assert "token" in reason


def test_empty_url_returns_false(cfg):
    ok, reason = brain_runtime.try_brain_write_web_cache("", "body", cfg)
    assert ok is False
    assert "url" in reason.lower() or "content" in reason.lower()


def test_empty_content_returns_false(cfg):
    ok, reason = brain_runtime.try_brain_write_web_cache("https://x.example", "", cfg)
    assert ok is False


def test_title_override_truncates_at_60(cfg):
    with (
        patch("brain_notion_client.NotionClient", autospec=True),
        patch(
            "brain_mcp_write.store_record",
            return_value={"status": "ok", "notion_page_id": "p"},
        ) as mock_store,
    ):
        long_title = "A very long title " * 20  # > 60 chars
        brain_runtime.try_brain_write_web_cache(
            "https://x.example", "body", cfg, title=long_title
        )
    (_c, _db, _cat, fields, _cfg) = mock_store.call_args.args
    assert len(fields["name"]) == 60


def test_falls_back_to_url_when_title_empty(cfg):
    with (
        patch("brain_notion_client.NotionClient", autospec=True),
        patch(
            "brain_mcp_write.store_record",
            return_value={"status": "ok", "notion_page_id": "p"},
        ) as mock_store,
    ):
        brain_runtime.try_brain_write_web_cache(
            "https://example.com/longpath/x/y", "body", cfg, title=""
        )
    (_c, _db, _cat, fields, _cfg) = mock_store.call_args.args
    # Fallback uses the URL (truncated at 60 chars)
    assert fields["name"].startswith("https://example.com")


def test_exception_inside_returns_false(cfg):
    with patch(
        "brain_notion_client.NotionClient",
        side_effect=RuntimeError("client init broke"),
    ):
        ok, reason = brain_runtime.try_brain_write_web_cache(
            "https://x.example", "body", cfg
        )
    assert ok is False
    assert "exception" in reason
