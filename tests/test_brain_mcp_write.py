"""Tests for brain_mcp_write — build payloads, scrub, create, mirror."""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import brain_mcp_write  # noqa: E402
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
    spec = importlib.util.spec_from_file_location(
        "tausik_brain_handlers_write", _HANDLERS_PATH
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- Fixtures ------------------------------------------------------------


@pytest.fixture
def conn(tmp_path):
    c = brain_sync.open_brain_db(str(tmp_path / "brain.db"))
    yield c
    c.close()


@pytest.fixture
def cfg():
    return {
        "enabled": True,
        "project_names": [],
        "private_url_patterns": [],
        "database_ids": {
            "decisions": "db-dec",
            "web_cache": "db-wc",
            "patterns": "db-pat",
            "gotchas": "db-got",
        },
    }


class FakeClient:
    def __init__(self, *, raise_on_create=False, raise_error=None, page_id="nid-1"):
        self.create_calls: list[dict] = []
        self.raise_on_create = raise_on_create
        self.raise_error = raise_error
        self.page_id = page_id

    def pages_create(self, *, parent, properties, children=None):
        self.create_calls.append(
            {"parent": parent, "properties": properties, "children": children}
        )
        if self.raise_error is not None:
            raise self.raise_error
        if self.raise_on_create:
            raise ConnectionError("network down")
        # Echo back a minimal Notion-shaped page with the properties included.
        return _fake_notion_response(
            page_id=self.page_id,
            database_id=parent["database_id"],
            properties=properties,
        )


def _enrich_plain_text(props: dict) -> dict:
    """Notion populates `plain_text` in responses; our outgoing JSON only
    has `text.content`. Add plain_text so brain_sync mappers can read it.
    """
    out: dict = {}
    for key, val in props.items():
        if not isinstance(val, dict):
            out[key] = val
            continue
        if "title" in val:
            out[key] = {
                "title": [
                    {**it, "plain_text": it.get("text", {}).get("content", "")}
                    for it in val["title"]
                ]
            }
        elif "rich_text" in val:
            out[key] = {
                "rich_text": [
                    {**it, "plain_text": it.get("text", {}).get("content", "")}
                    for it in val["rich_text"]
                ]
            }
        else:
            out[key] = val
    return out


def _fake_notion_response(*, page_id, database_id, properties):
    """Turn outgoing properties back into an inbound Notion page.

    Mirrors what Notion returns so brain_sync.map_page_to_row succeeds.
    """
    return {
        "object": "page",
        "id": page_id,
        "parent": {"database_id": database_id},
        "properties": _enrich_plain_text(properties),
        "last_edited_time": "2026-04-23T12:00:00Z",
        "created_time": "2026-04-23T12:00:00Z",
    }


# ---- Content hash --------------------------------------------------------


def test_content_hash_deterministic():
    assert brain_mcp_write.compute_content_hash("abc") == (
        brain_mcp_write.compute_content_hash("abc")
    )


def test_content_hash_16_hex_chars():
    h = brain_mcp_write.compute_content_hash("something")
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_content_hash_different_inputs_differ():
    assert brain_mcp_write.compute_content_hash("a") != (
        brain_mcp_write.compute_content_hash("b")
    )


def test_content_hash_rejects_non_string():
    with pytest.raises(TypeError):
        brain_mcp_write.compute_content_hash(123)  # type: ignore[arg-type]


# ---- Project name resolution --------------------------------------------


def test_resolve_project_name_explicit_wins(monkeypatch):
    monkeypatch.setenv("TAUSIK_PROJECT_NAME", "from-env")
    assert brain_mcp_write._resolve_project_name("explicit") == "explicit"


def test_resolve_project_name_env_fallback(monkeypatch):
    monkeypatch.setenv("TAUSIK_PROJECT_NAME", "from-env")
    assert brain_mcp_write._resolve_project_name(None) == "from-env"


def test_resolve_project_name_cwd_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("TAUSIK_PROJECT_NAME", raising=False)
    monkeypatch.chdir(tmp_path)
    assert brain_mcp_write._resolve_project_name(None) == tmp_path.name


# ---- Builders: decision --------------------------------------------------


def test_build_decision_shape():
    props = brain_mcp_write.build_properties_decision(
        name="Use pgbouncer",
        decision="go with pgbouncer",
        context="lots of connections",
        rationale="lower tail latency",
        tags=["db"],
        stack=["python"],
        project_hash="h" * 16,
    )
    assert props["Name"] == {"title": [{"text": {"content": "Use pgbouncer"}}]}
    assert props["Decision"]["rich_text"][0]["text"]["content"] == "go with pgbouncer"
    assert props["Tags"]["multi_select"] == [{"name": "db"}]
    assert props["Stack"]["multi_select"] == [{"name": "python"}]
    assert props["Generalizable"] == {"checkbox": True}
    assert "Date" in props  # defaults to today


def test_build_decision_requires_name():
    with pytest.raises(ValueError):
        brain_mcp_write.build_properties_decision(name="", decision="x")


def test_build_decision_drops_optional_url():
    props = brain_mcp_write.build_properties_decision(name="A", decision="B")
    assert "Superseded By" not in props  # None → dropped


def test_build_decision_superseded_by_url():
    props = brain_mcp_write.build_properties_decision(
        name="A", decision="B", superseded_by="https://old.example"
    )
    assert props["Superseded By"] == {"url": "https://old.example"}


# ---- Builders: web_cache -------------------------------------------------


def test_build_web_cache_shape():
    props = brain_mcp_write.build_properties_web_cache(
        name="Notion pages.create",
        url="https://developers.notion.com/reference/post-page",
        content="Full content body.",
        query="notion pages.create",
        domain="developers.notion.com",
        ttl_days=30,
        content_hash="deadbeefdeadbeef",
    )
    assert props["URL"] == {"url": "https://developers.notion.com/reference/post-page"}
    assert props["TTL Days"] == {"number": 30}
    assert props["Domain"] == {"select": {"name": "developers.notion.com"}}
    assert (
        props["Content Hash"]["rich_text"][0]["text"]["content"] == "deadbeefdeadbeef"
    )


def test_build_web_cache_requires_url_and_content():
    with pytest.raises(ValueError):
        brain_mcp_write.build_properties_web_cache(name="n", url="", content="x")
    with pytest.raises(ValueError):
        brain_mcp_write.build_properties_web_cache(
            name="n", url="https://x", content=""
        )


def test_build_web_cache_chunks_long_content():
    long = "x" * 4500
    props = brain_mcp_write.build_properties_web_cache(
        name="n", url="https://x", content=long, content_hash="h"
    )
    # 2000 + 2000 + 500 → 3 chunks
    assert len(props["Content"]["rich_text"]) == 3
    total = sum(len(c["text"]["content"]) for c in props["Content"]["rich_text"])
    assert total == 4500


# ---- Builders: pattern / gotcha -----------------------------------------


def test_build_pattern_shape():
    props = brain_mcp_write.build_properties_pattern(
        name="Mixin composition",
        description="split service into mixins",
        confidence="tested",
        tags=["arch"],
    )
    assert props["Name"]["title"][0]["text"]["content"] == "Mixin composition"
    assert props["Confidence"] == {"select": {"name": "tested"}}


def test_build_gotcha_shape():
    props = brain_mcp_write.build_properties_gotcha(
        name="FTS5 dash pitfall",
        description="dashes are column qualifiers",
        wrong_way="raw query",
        right_way="wrap in quotes",
        severity="high",
        evidence_url="https://sqlite.org",
    )
    assert props["Severity"] == {"select": {"name": "high"}}
    assert props["Evidence URL"] == {"url": "https://sqlite.org"}


def test_builders_strip_empty_multiselect_entries():
    props = brain_mcp_write.build_properties_decision(
        name="N", decision="D", tags=["  ", "", "real"]
    )
    assert props["Tags"]["multi_select"] == [{"name": "real"}]


# ---- scrub_inputs --------------------------------------------------------


def test_scrub_inputs_joins_text_fields(cfg):
    cfg["project_names"] = ["laplandka"]
    r = brain_mcp_write.scrub_inputs(
        "decisions",
        {
            "name": "X",
            "decision": "we use Laplandka's setup",
            "context": "",
            "rationale": "",
        },
        cfg,
    )
    assert r["ok"] is False


def test_scrub_inputs_clean_content_ok(cfg):
    r = brain_mcp_write.scrub_inputs(
        "patterns",
        {
            "name": "N",
            "description": "Mixin composition",
            "when_to_use": "when class grows",
            "example": "class X(A, B): ...",
        },
        cfg,
    )
    assert r["ok"] is True


# ---- store_record happy path -------------------------------------------


def test_store_record_happy_path_decision(conn, cfg, monkeypatch):
    monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo-project")
    client = FakeClient(page_id="nid-1")
    r = brain_mcp_write.store_record(
        client,
        conn,
        "decisions",
        {
            "name": "Pgbouncer",
            "decision": "adopt",
            "context": "high conn count",
            "rationale": "low latency",
            "tags": ["db"],
        },
        cfg,
    )
    assert r["status"] == "ok"
    assert r["notion_page_id"] == "nid-1"
    assert len(client.create_calls) == 1
    # Local mirror has the row
    row = conn.execute(
        "SELECT name, decision FROM brain_decisions WHERE notion_page_id = ?",
        ("nid-1",),
    ).fetchone()
    assert row["name"] == "Pgbouncer"


def test_store_record_happy_path_web_cache_autohashes_content(conn, cfg, monkeypatch):
    monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")
    client = FakeClient(page_id="wc-1")
    r = brain_mcp_write.store_record(
        client,
        conn,
        "web_cache",
        {
            "name": "Notion API",
            "url": "https://developers.notion.com/",
            "content": "Create a page...",
        },
        cfg,
    )
    assert r["status"] == "ok"
    props = client.create_calls[0]["properties"]
    assert len(props["Content Hash"]["rich_text"]) > 0


# ---- Scrub-blocked short-circuits --------------------------------------


def test_store_record_scrub_block_returns_issues(conn, cfg):
    cfg["project_names"] = ["secret"]
    client = FakeClient()
    r = brain_mcp_write.store_record(
        client,
        conn,
        "patterns",
        {
            "name": "secret pattern",
            "description": "something about secret",
        },
        cfg,
    )
    assert r["status"] == "scrub_blocked"
    assert r["issues"]
    assert not client.create_calls  # Notion NOT called


# ---- Error paths -------------------------------------------------------


def test_store_record_missing_database_id(conn, cfg):
    cfg["database_ids"]["decisions"] = ""
    client = FakeClient()
    r = brain_mcp_write.store_record(
        client, conn, "decisions", {"name": "X", "decision": "Y"}, cfg
    )
    assert r["status"] == "config_error"
    assert not client.create_calls


def test_store_record_notion_error_propagates(conn, cfg):
    client = FakeClient(raise_on_create=True)
    r = brain_mcp_write.store_record(
        client, conn, "decisions", {"name": "X", "decision": "Y"}, cfg
    )
    assert r["status"] == "notion_error"
    assert "network down" in r["error"]


def test_store_record_notion_auth_error_classified(conn, cfg):
    """NotionAuthError → error_category='auth', format renders auth hint."""
    from brain_notion_client import NotionAuthError

    client = FakeClient(raise_error=NotionAuthError("401 bad token"))
    r = brain_mcp_write.store_record(
        client, conn, "decisions", {"name": "X", "decision": "Y"}, cfg
    )
    assert r["status"] == "notion_error"
    assert r["error_category"] == "auth"
    md = brain_mcp_write.format_store_result(r, "decisions")
    assert "auth failed" in md or "integration token" in md


def test_store_record_notion_rate_limit_with_retry_after(conn, cfg):
    """NotionRateLimitError.retry_after=42 → surfaced in result + rendered."""
    from brain_notion_client import NotionRateLimitError

    exc = NotionRateLimitError("429")
    exc.retry_after = 42
    client = FakeClient(raise_error=exc)
    r = brain_mcp_write.store_record(
        client, conn, "decisions", {"name": "X", "decision": "Y"}, cfg
    )
    assert r["status"] == "notion_error"
    assert r["error_category"] == "rate_limit"
    assert r["retry_after"] == 42
    md = brain_mcp_write.format_store_result(r, "decisions")
    assert "42 seconds" in md


def test_store_record_notion_rate_limit_without_retry_after_uses_default(conn, cfg):
    """NotionRateLimitError without retry_after → format uses default, no crash."""
    from brain_notion_client import NotionRateLimitError

    client = FakeClient(raise_error=NotionRateLimitError("429"))
    r = brain_mcp_write.store_record(
        client, conn, "decisions", {"name": "X", "decision": "Y"}, cfg
    )
    assert r["status"] == "notion_error"
    assert r["error_category"] == "rate_limit"
    assert r["retry_after"] is None
    md = brain_mcp_write.format_store_result(r, "decisions")
    assert "Retry in" in md
    assert "seconds" in md


def test_store_record_bad_category(conn, cfg):
    client = FakeClient()
    r = brain_mcp_write.store_record(client, conn, "nope", {"name": "X"}, cfg)
    assert r["status"] == "bad_category"
    assert not client.create_calls


def test_store_record_ok_not_mirrored_when_upsert_fails(conn, cfg, monkeypatch):
    """Notion succeeded, mirror upsert raised → status=ok_not_mirrored, page_id kept."""
    client = FakeClient(page_id="nid-mirror-fail")

    def boom(*_a, **_kw):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(brain_sync, "upsert_page", boom)

    r = brain_mcp_write.store_record(
        client, conn, "decisions", {"name": "X", "decision": "Y"}, cfg
    )
    assert r["status"] == "ok_not_mirrored"
    assert r["notion_page_id"] == "nid-mirror-fail"
    assert "disk I/O error" in r["warning"]
    md = brain_mcp_write.format_store_result(r, "decisions")
    assert "in Notion but local mirror lagged" in md
    assert "nid-mirror-fail" in md


def test_store_record_ok_not_mirrored_when_map_page_to_row_fails(
    conn, cfg, monkeypatch
):
    """map_page_to_row raise (boundary: failure earlier than upsert) → ok_not_mirrored."""
    client = FakeClient(page_id="nid-map-fail")

    def boom(*_a, **_kw):
        raise KeyError("missing column")

    monkeypatch.setattr(brain_sync, "map_page_to_row", boom)

    r = brain_mcp_write.store_record(
        client, conn, "decisions", {"name": "X", "decision": "Y"}, cfg
    )
    assert r["status"] == "ok_not_mirrored"
    assert r["notion_page_id"] == "nid-map-fail"
    assert "missing column" in r["warning"]


def test_store_record_missing_required_field(conn, cfg):
    """web_cache builder raises ValueError on missing url/content."""
    client = FakeClient()
    r = brain_mcp_write.store_record(
        client,
        conn,
        "web_cache",
        {"name": "x", "content": "y"},
        cfg,  # no url
    )
    assert r["status"] == "bad_fields"
    assert not client.create_calls


# ---- Format result -----------------------------------------------------


def test_format_result_ok():
    md = brain_mcp_write.format_store_result(
        {
            "status": "ok",
            "notion_page_id": "n1",
            "source_project_hash": "h" * 16,
        },
        "decisions",
    )
    assert "**Stored**" in md
    assert "n1" in md


def test_format_result_scrub_block():
    md = brain_mcp_write.format_store_result(
        {
            "status": "scrub_blocked",
            "issues": [
                {
                    "detector": "emails",
                    "severity": "block",
                    "match": "a@b.com",
                    "hint": "remove",
                }
            ],
        },
        "decisions",
    )
    assert "Scrubbing blocked" in md


def test_format_result_notion_error():
    """Legacy error payload (no `category`) renders via brain_fallback's unknown path."""
    md = brain_mcp_write.format_store_result(
        {"status": "notion_error", "error": "timeout"}, "patterns"
    )
    assert "timeout" in md or "Notion error" in md


def test_format_result_typo_category_falls_back_to_unknown():
    """Typo `category` (instead of `error_category`) → 'unknown' renderer.

    Previously a defensive fallback `or result.get('category')` would silently
    accept the wrong key. Now removed: typos surface as 'unknown' rendering.
    """
    md = brain_mcp_write.format_store_result(
        {"status": "notion_error", "category": "auth", "error": "401"}, "decisions"
    )
    assert "auth failed" not in md
    assert "Notion error" in md or "401" in md


# ---- Handler dispatch --------------------------------------------------


@pytest.fixture
def handlers_env(tmp_path, monkeypatch):
    """Enabled brain config + fresh DB + stubbed NotionClient class."""
    db_path = tmp_path / "brain.db"
    brain_sync.open_brain_db(str(db_path)).close()
    monkeypatch.setenv("FAKE_BRAIN_TOKEN", "tok")
    monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")

    import brain_config

    fake_cfg = {
        "enabled": True,
        "local_mirror_path": str(db_path),
        "notion_integration_token_env": "FAKE_BRAIN_TOKEN",
        "project_names": [],
        "private_url_patterns": [],
        "database_ids": {
            "decisions": "db-dec",
            "web_cache": "db-wc",
            "patterns": "db-pat",
            "gotchas": "db-got",
        },
    }
    monkeypatch.setattr(brain_config, "load_brain", lambda: fake_cfg)
    monkeypatch.setattr(brain_config, "get_brain_mirror_path", lambda: str(db_path))
    handlers = _load_brain_handlers()

    # Stub the NotionClient inside handlers' reference
    import brain_notion_client

    recorded: list[dict] = []

    class Stub:
        def __init__(self, *a, **kw):
            pass

        def pages_create(self, *, parent, properties, children=None):
            page = _fake_notion_response(
                page_id=f"nid-{len(recorded) + 1}",
                database_id=parent["database_id"],
                properties=properties,
            )
            recorded.append({"parent": parent, "properties": properties})
            return page

        def pages_retrieve(self, page_id):
            raise KeyError(page_id)

        def search(self, **_kw):
            return {"results": [], "has_more": False}

    monkeypatch.setattr(brain_notion_client, "NotionClient", Stub)

    return {"handlers": handlers, "calls": recorded, "cfg": fake_cfg}


def test_handler_brain_store_decision_happy(handlers_env):
    h = handlers_env["handlers"]
    out = h.handle_tool(
        "brain_store_decision",
        {
            "name": "Use pgbouncer",
            "decision": "adopt",
            "context": "pools",
            "rationale": "lower latency",
        },
    )
    assert "**Stored**" in out or "Stored" in out
    assert len(handlers_env["calls"]) == 1


def test_handler_brain_cache_web_happy(handlers_env):
    h = handlers_env["handlers"]
    out = h.handle_tool(
        "brain_cache_web",
        {
            "url": "https://python.org/3.12",
            "content": "3.12 release notes",
            "name": "Py 3.12",
        },
    )
    assert "Stored" in out
    assert handlers_env["calls"][0]["parent"] == {"database_id": "db-wc"}


def test_handler_brain_store_pattern_happy(handlers_env):
    h = handlers_env["handlers"]
    out = h.handle_tool(
        "brain_store_pattern",
        {
            "name": "Mixin composition",
            "description": "split service class",
            "confidence": "tested",
        },
    )
    assert "Stored" in out


def test_handler_brain_store_gotcha_happy(handlers_env):
    h = handlers_env["handlers"]
    out = h.handle_tool(
        "brain_store_gotcha",
        {
            "name": "FTS5 dash",
            "description": "dash is a column qualifier in FTS5 MATCH",
            "severity": "high",
        },
    )
    assert "Stored" in out


def test_handler_brain_store_missing_required_field(handlers_env):
    h = handlers_env["handlers"]
    out = h.handle_tool("brain_store_decision", {"decision": "x"})  # no name
    assert "required" in out or "Invalid" in out or "empty" in out
