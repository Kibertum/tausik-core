"""Optional external_repo_url validation on artifact pattern/gotcha writes."""

from __future__ import annotations

import io
import os
import sys
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import brain_artifact_card  # noqa: E402
import brain_mcp_write  # noqa: E402
import brain_publish_flow  # noqa: E402
import brain_sync  # noqa: E402

from test_brain_mcp_write import FakeClient  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    c = brain_sync.open_brain_db(str(tmp_path / "brain.db"))
    yield c
    c.close()


@pytest.fixture
def cfg():
    return {
        "enabled": True,
        "database_ids": {
            "decisions": "db-dec",
            "web_cache": "db-wc",
            "patterns": "db-pat",
            "gotchas": "db-got",
        },
    }


def test_validate_external_repo_url_bad_scheme():
    ok, err = brain_artifact_card.validate_external_repo_url_for_store(
        "patterns",
        {"external_repo_url": "ftp://example.com/r"},
        {"skip_external_repo_url_reachability_check": True},
    )
    assert ok is False
    assert err and "http" in err.lower()


def test_validate_external_repo_url_syntax_only_when_skip_config():
    ok, err = brain_artifact_card.validate_external_repo_url_for_store(
        "patterns",
        {"external_repo_url": "https://example.com/repo.git"},
        {"skip_external_repo_url_reachability_check": True},
    )
    assert ok is True
    assert err is None


def test_validate_external_repo_url_decisions_category_ignored():
    ok, err = brain_artifact_card.validate_external_repo_url_for_store(
        "decisions",
        {"external_repo_url": "ftp://oops"},
        {},
    )
    assert ok is True


def test_check_reachable_accepts_403():
    err = HTTPError(
        "https://example.com/",
        403,
        "Forbidden",
        hdrs={},
        fp=io.BytesIO(),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        ok, msg = brain_artifact_card.check_external_repo_url_reachable(
            "https://example.com/x"
        )
    assert ok is True
    assert msg is None


def test_store_record_blocks_unreachable_external_url(conn, cfg):
    client = MagicMock()
    with patch(
        "urllib.request.urlopen",
        side_effect=OSError("simulated network failure"),
    ):
        r = brain_mcp_write.store_record(
            client,
            conn,
            "patterns",
            {
                "name": "n",
                "description": "d",
                "external_repo_url": "https://example.com/repo",
            },
            cfg,
        )
    assert r["status"] == "card_schema_blocked"
    assert "external_repo_url" in (r.get("error") or "").lower()
    client.pages_create.assert_not_called()


def test_store_record_ok_when_skip_reachability_no_network(conn, cfg):
    cfg2 = dict(cfg)
    cfg2["skip_external_repo_url_reachability_check"] = True
    fake = FakeClient()
    r = brain_mcp_write.store_record(
        fake,
        conn,
        "patterns",
        {
            "name": "n",
            "description": "body text here",
            "external_repo_url": "https://example.com/repo",
        },
        cfg2,
    )
    assert r["status"] == "ok"
    assert fake.create_calls


def test_draft_blocks_when_external_url_unreachable(cfg):
    with patch(
        "urllib.request.urlopen",
        side_effect=OSError("down"),
    ):
        out = brain_publish_flow.draft_artifact_publish(
            "patterns",
            {
                "name": "n",
                "description": "ok",
                "external_repo_url": "https://example.com/r",
            },
            cfg,
        )
    assert out["external_repo_ok"] is False
    assert out["external_repo_error"]
    assert out["would_publish_ok"] is False

