"""Integration tests: universality hint emission from real call sites.

Covers AC #5 (memory_add) and AC #6 (brain_runtime success paths).
"""

from __future__ import annotations

import os
import sqlite3
import sys
from unittest.mock import patch

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_runtime  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    db = tmp_path / "t.db"
    be = SQLiteBackend(str(db))
    return ProjectService(be)


# --- service_knowledge.memory_add emits hint -------------------------------


def test_memory_add_emits_hint_for_universal_content(svc, capsys):
    svc.memory_add(
        "pattern",
        "Auth choice",
        "Use JWT for stateless auth across services",
    )
    err = capsys.readouterr().err
    assert "Universal pattern(s) detected" in err
    assert "jwt" in err
    assert "brain_draft_artifact" in err


def test_memory_add_silent_for_project_specific_content(svc, capsys):
    svc.memory_add(
        "pattern",
        "Local refactor",
        "Refactor scripts/foo.py to extract helper",
    )
    err = capsys.readouterr().err
    assert "Universal pattern" not in err


def test_memory_add_silent_for_aggregate_false_positive(svc, capsys):
    """'aggregate' must NOT trigger rate-limit hint (word boundary guard)."""
    svc.memory_add(
        "pattern",
        "Stats",
        "Aggregate the rows separately for each tenant",
    )
    err = capsys.readouterr().err
    assert "rate-limit" not in err
    assert "Universal pattern" not in err


def test_memory_add_succeeds_when_hint_emission_fails(svc, capsys, monkeypatch):
    """Hint must NEVER block memory_add — even if detector blows up."""

    def boom(*_a, **_kw):
        raise RuntimeError("detector exploded")

    monkeypatch.setattr("brain_universality.detect_universal_patterns", boom)
    msg = svc.memory_add("pattern", "T", "Use JWT")
    assert "saved" in msg.lower()


# --- brain_runtime.try_brain_write_decision emits hint --------------------


def _patch_brain_success(text_arg_capture: list[str]):
    """Helper context: stub Notion + sqlite so try_brain_write_* returns ok."""

    def fake_open(path):
        return sqlite3.connect(":memory:")

    def fake_store(client, conn, category, fields, cfg):
        # capture content for assertion if caller wants
        text_arg_capture.append(fields.get("decision") or fields.get("content") or "")
        return {"status": "ok", "notion_page_id": "page-xyz"}

    return [
        patch.dict(os.environ, {"FAKE_TOK": "t"}),
        patch("brain_notion_client.NotionClient", autospec=True),
        patch("brain_sync.open_brain_db", side_effect=fake_open),
        patch("brain_mcp_write.store_record", side_effect=fake_store),
        patch("brain_config.get_brain_mirror_path", return_value=":memory:"),
    ]


def test_try_brain_write_decision_emits_hint_on_success(capsys):
    cfg = {
        "enabled": True,
        "notion_integration_token_env": "FAKE_TOK",
        "database_ids": {"decisions": "d"},
    }
    captured: list[str] = []
    patches = _patch_brain_success(captured)
    for p in patches:
        p.start()
    try:
        ok, detail = brain_runtime.try_brain_write_decision(
            "Always use OAuth2 for SSO integration", None, cfg
        )
    finally:
        for p in reversed(patches):
            p.stop()
    assert ok is True
    err = capsys.readouterr().err
    assert "Universal pattern(s) detected" in err
    assert "oauth" in err


def test_try_brain_write_decision_silent_for_project_specific(capsys):
    cfg = {
        "enabled": True,
        "notion_integration_token_env": "FAKE_TOK",
        "database_ids": {"decisions": "d"},
    }
    captured: list[str] = []
    patches = _patch_brain_success(captured)
    for p in patches:
        p.start()
    try:
        ok, _ = brain_runtime.try_brain_write_decision("Refactor scripts/foo.py helpers", None, cfg)
    finally:
        for p in reversed(patches):
            p.stop()
    assert ok is True
    err = capsys.readouterr().err
    assert "Universal pattern" not in err


def test_try_brain_write_web_cache_emits_hint_on_success(capsys):
    cfg = {
        "enabled": True,
        "notion_integration_token_env": "FAKE_TOK",
        "database_ids": {"web_cache": "w"},
    }
    captured: list[str] = []
    patches = _patch_brain_success(captured)
    for p in patches:
        p.start()
    try:
        ok, _ = brain_runtime.try_brain_write_web_cache(
            "https://api.example.com/docs",
            "Webhooks must be retried with exponential backoff",
            cfg,
        )
    finally:
        for p in reversed(patches):
            p.stop()
    assert ok is True
    err = capsys.readouterr().err
    assert "Universal pattern(s) detected" in err
    assert "retry" in err
    assert "webhook" in err


def test_brain_runtime_hint_failure_does_not_break_write(capsys, monkeypatch):
    """Detector exception must not flip the (True, page_id) success contract."""

    def boom(*_a, **_kw):
        raise RuntimeError("detector down")

    monkeypatch.setattr("brain_universality.detect_universal_patterns", boom)
    cfg = {
        "enabled": True,
        "notion_integration_token_env": "FAKE_TOK",
        "database_ids": {"decisions": "d"},
    }
    patches = _patch_brain_success([])
    for p in patches:
        p.start()
    try:
        ok, page = brain_runtime.try_brain_write_decision("Use JWT", None, cfg)
    finally:
        for p in reversed(patches):
            p.stop()
    assert ok is True
    assert page == "page-xyz"
