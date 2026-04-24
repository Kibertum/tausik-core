"""Tests for brain_runtime.open_brain_deps.

The helper was folded in when the third in-tree caller landed (the
PostToolUse WebFetch hook is the third; the two MCP handler files are
one and two). It returns `(conn, client, cfg)` with None semantics for
disabled brain and missing-token.
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
def enabled_cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_DEPS_TOKEN", "tok-1")
    return {
        "enabled": True,
        "local_mirror_path": str(tmp_path / "brain.db"),
        "notion_integration_token_env": "OPEN_DEPS_TOKEN",
        "database_ids": {
            "decisions": "d",
            "web_cache": "w",
            "patterns": "p",
            "gotchas": "g",
        },
        "project_names": [],
        "private_url_patterns": [],
    }


def test_disabled_returns_none_conn_and_client(tmp_path):
    cfg = {"enabled": False}
    with patch("brain_config.load_brain", return_value=cfg):
        conn, client, returned_cfg = brain_runtime.open_brain_deps()
    assert conn is None
    assert client is None
    assert returned_cfg == cfg


def test_missing_token_returns_conn_but_no_client(enabled_cfg, monkeypatch):
    monkeypatch.delenv("OPEN_DEPS_TOKEN", raising=False)
    with (
        patch("brain_config.load_brain", return_value=enabled_cfg),
        patch(
            "brain_config.get_brain_mirror_path",
            return_value=enabled_cfg["local_mirror_path"],
        ),
    ):
        conn, client, _ = brain_runtime.open_brain_deps()
    try:
        assert conn is not None
        assert client is None
    finally:
        if conn is not None:
            conn.close()


def test_happy_path_both_set(enabled_cfg):
    with (
        patch("brain_config.load_brain", return_value=enabled_cfg),
        patch(
            "brain_config.get_brain_mirror_path",
            return_value=enabled_cfg["local_mirror_path"],
        ),
        patch("brain_notion_client.NotionClient", autospec=True) as mock_client,
    ):
        conn, client, cfg_out = brain_runtime.open_brain_deps()
    try:
        assert conn is not None
        assert client is not None
        assert cfg_out["enabled"] is True
        # Client was built with the token from the env var.
        args, kwargs = mock_client.call_args
        assert args[0] == "tok-1"
        assert kwargs.get("timeout") == brain_runtime._FAST_FALLBACK_TIMEOUT
        assert kwargs.get("max_retries") == 1
    finally:
        if conn is not None:
            conn.close()


def test_empty_token_env_name_treated_as_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_DEPS_TOKEN", "anything")
    cfg = {
        "enabled": True,
        "local_mirror_path": str(tmp_path / "brain.db"),
        "notion_integration_token_env": "",  # empty name
        "database_ids": {
            "decisions": "d",
            "web_cache": "w",
            "patterns": "p",
            "gotchas": "g",
        },
    }
    with (
        patch("brain_config.load_brain", return_value=cfg),
        patch(
            "brain_config.get_brain_mirror_path",
            return_value=cfg["local_mirror_path"],
        ),
    ):
        conn, client, _ = brain_runtime.open_brain_deps()
    try:
        assert conn is not None
        assert client is None
    finally:
        if conn is not None:
            conn.close()
