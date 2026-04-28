"""Tests for brain_runtime.resolve_brain_token cascade (env > .env > config.json)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from brain_runtime import _parse_dotenv, resolve_brain_token


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.delenv("NOTION_TAUSIK_TOKEN", raising=False)
    yield


def test_env_var_wins(clean_env, monkeypatch, tmp_path):
    monkeypatch.setenv("NOTION_TAUSIK_TOKEN", "env_token")
    # Even with .env file present, env wins
    (tmp_path / ".tausik").mkdir()
    (tmp_path / ".tausik" / ".env").write_text("NOTION_TAUSIK_TOKEN=dotenv_token\n")
    cfg = {
        "notion_integration_token_env": "NOTION_TAUSIK_TOKEN",
        "notion_integration_token": "config_token",
    }
    assert resolve_brain_token(cfg, project_dir=str(tmp_path)) == "env_token"


def test_dotenv_fallback(clean_env, tmp_path):
    (tmp_path / ".tausik").mkdir()
    (tmp_path / ".tausik" / ".env").write_text("NOTION_TAUSIK_TOKEN=dotenv_token\n")
    cfg = {"notion_integration_token_env": "NOTION_TAUSIK_TOKEN"}
    assert resolve_brain_token(cfg, project_dir=str(tmp_path)) == "dotenv_token"


def test_config_inline_emits_warning(clean_env, tmp_path, capsys):
    cfg = {
        "notion_integration_token_env": "NOTION_TAUSIK_TOKEN",
        "notion_integration_token": "inline_token",
    }
    assert resolve_brain_token(cfg, project_dir=str(tmp_path)) == "inline_token"
    err = capsys.readouterr().err
    assert "WARN" in err and "config.json" in err


def test_all_empty_returns_empty(clean_env, tmp_path):
    cfg = {"notion_integration_token_env": "NOTION_TAUSIK_TOKEN"}
    assert resolve_brain_token(cfg, project_dir=str(tmp_path)) == ""


def test_dotenv_parser_strips_quotes_and_comments(tmp_path):
    p = tmp_path / ".env"
    p.write_text(
        "# comment\n"
        '\n'
        'NOTION_TAUSIK_TOKEN="quoted_value"\n'
        "PLAIN=plain_value\n"
        "  WHITESPACE  =  spaced  \n"
    )
    out = _parse_dotenv(str(p))
    assert out == {
        "NOTION_TAUSIK_TOKEN": "quoted_value",
        "PLAIN": "plain_value",
        "WHITESPACE": "spaced",
    }


def test_dotenv_missing_file_returns_empty():
    assert _parse_dotenv("/nonexistent/file/.env") == {}


def test_default_env_var_name_when_unset(clean_env, tmp_path):
    """If config doesn't specify notion_integration_token_env, default to NOTION_TAUSIK_TOKEN."""
    (tmp_path / ".tausik").mkdir()
    (tmp_path / ".tausik" / ".env").write_text("NOTION_TAUSIK_TOKEN=default_picked\n")
    cfg: dict = {}  # no token_env specified
    assert resolve_brain_token(cfg, project_dir=str(tmp_path)) == "default_picked"
