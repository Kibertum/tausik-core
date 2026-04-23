"""Tests for tausik-brain MCP handlers (agents/claude/mcp/brain/handlers.py)."""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest

# Ensure scripts dir is importable (brain handlers.py imports brain_* modules).
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)

import brain_sync  # noqa: E402

_HANDLERS_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "agents",
        "claude",
        "mcp",
        "brain",
        "handlers.py",
    )
)


def _load_brain_handlers():
    """Load agents/claude/mcp/brain/handlers.py under a unique module name.

    Avoids clashing with agents/claude/mcp/project/handlers.py when both
    get added to sys.path by different tests in the same session.
    """
    spec = importlib.util.spec_from_file_location(
        "tausik_brain_handlers", _HANDLERS_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def handlers():
    """Fresh handlers module each test so module-level caches don't leak."""
    return _load_brain_handlers()


@pytest.fixture
def brain_env(tmp_path, monkeypatch):
    """Stub load_brain + mirror path + token env to a tmp enabled config."""
    db_path = tmp_path / "brain.db"
    brain_sync.open_brain_db(str(db_path)).close()

    fake_cfg = {
        "enabled": True,
        "local_mirror_path": str(db_path),
        "notion_integration_token_env": "FAKE_BRAIN_TOKEN",
        "database_ids": {
            "decisions": "db-dec",
            "web_cache": "db-wc",
            "patterns": "db-pat",
            "gotchas": "db-got",
        },
    }
    monkeypatch.setenv("FAKE_BRAIN_TOKEN", "fake-token-abc")

    import brain_config

    monkeypatch.setattr(brain_config, "load_brain", lambda: fake_cfg)
    monkeypatch.setattr(brain_config, "get_brain_mirror_path", lambda: str(db_path))
    return {"db_path": db_path, "cfg": fake_cfg}


# ---- Not-enabled paths ---------------------------------------------------


def test_brain_search_disabled_returns_setup_hint(handlers, monkeypatch):
    import brain_config

    monkeypatch.setattr(
        brain_config,
        "load_brain",
        lambda: {
            "enabled": False,
            "local_mirror_path": "/nope",
            "notion_integration_token_env": "X",
            "database_ids": {},
        },
    )
    out = handlers.handle_brain_search({"query": "anything"})
    assert "Brain is not enabled" in out
    assert "brain init" in out


def test_brain_get_disabled_returns_setup_hint(handlers, monkeypatch):
    import brain_config

    monkeypatch.setattr(
        brain_config,
        "load_brain",
        lambda: {
            "enabled": False,
            "local_mirror_path": "/nope",
            "notion_integration_token_env": "X",
            "database_ids": {},
        },
    )
    out = handlers.handle_brain_get({"id": "x", "category": "decisions"})
    assert "Brain is not enabled" in out


# ---- Arg validation ------------------------------------------------------


def test_brain_search_empty_query(handlers):
    out = handlers.handle_brain_search({"query": "   "})
    assert "query is empty" in out


def test_brain_get_missing_id(handlers):
    out = handlers.handle_brain_get({"category": "decisions"})
    assert "required" in out


def test_brain_get_missing_category(handlers):
    out = handlers.handle_brain_get({"id": "abc"})
    assert "required" in out


def test_dispatch_unknown_tool(handlers):
    out = handlers.handle_tool("mystery_tool", {})
    assert "Unknown tool" in out


# ---- Happy path with enabled config --------------------------------------


def test_brain_search_enabled_empty_mirror_no_fallback_found(
    brain_env, handlers, monkeypatch
):
    """Enabled, mirror empty, no token → handler still works, returns No matches."""
    monkeypatch.delenv("FAKE_BRAIN_TOKEN", raising=False)
    out = handlers.handle_brain_search({"query": "nothing-matches"})
    assert "No matches" in out


def test_brain_search_enabled_local_hit(brain_env, handlers):
    """Insert a row, handler returns formatted markdown with the match."""
    import sqlite3

    conn = sqlite3.connect(str(brain_env["db_path"]))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """INSERT INTO brain_decisions(notion_page_id, name, context, decision,
           rationale, tags, stack, date_value, source_project_hash, generalizable,
           last_edited_time, created_time) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "id1",
            "Pgbouncer",
            "chose pgbouncer",
            "",
            "",
            "[]",
            "[]",
            None,
            "h" * 16,
            1,
            "t",
            "t",
        ),
    )
    conn.commit()
    conn.close()

    out = handlers.handle_brain_search({"query": "pgbouncer"})
    assert "## Pgbouncer" in out
    assert "_[decisions]_" in out


def test_brain_get_enabled_miss_returns_no_record(brain_env, handlers, monkeypatch):
    monkeypatch.delenv("FAKE_BRAIN_TOKEN", raising=False)
    out = handlers.handle_brain_get({"id": "absent", "category": "decisions"})
    assert "No record" in out


def test_handle_tool_dispatches_brain_search(brain_env, handlers):
    out = handlers.handle_tool("brain_search", {"query": "noop"})
    assert "No matches" in out
