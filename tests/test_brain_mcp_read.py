"""Tests for brain_mcp_read — local-first search/get with Notion fallback."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import brain_mcp_read  # noqa: E402
import brain_sync  # noqa: E402


# ---- Fixtures -------------------------------------------------------------


@pytest.fixture
def conn(tmp_path):
    c = brain_sync.open_brain_db(str(tmp_path / "brain.db"))
    yield c
    c.close()


def _insert_decision(conn, *, pid, name, context, hash_="a" * 16):
    conn.execute(
        """INSERT INTO brain_decisions(notion_page_id, name, context, decision,
           rationale, tags, stack, date_value, source_project_hash, generalizable,
           last_edited_time, created_time) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pid,
            name,
            context,
            "",
            "",
            "[]",
            "[]",
            "2026-04-23",
            hash_,
            1,
            "2026-04-23T10:00:00Z",
            "2026-04-23T10:00:00Z",
        ),
    )
    conn.commit()


def _insert_web_cache(conn, *, pid, name, content, url="https://ex.com"):
    conn.execute(
        """INSERT INTO brain_web_cache(notion_page_id, name, url, query, content,
           fetched_at, ttl_days, domain, tags, source_project_hash, content_hash,
           last_edited_time, created_time) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pid,
            name,
            url,
            "",
            content,
            "2026-04-23T10:00:00Z",
            30,
            "ex.com",
            "[]",
            "a" * 16,
            "c" * 16,
            "2026-04-23T10:00:00Z",
            "2026-04-23T10:00:00Z",
        ),
    )
    conn.commit()


def _notion_page(*, page_id, db_id, name, context="", category="decisions"):
    """Minimal Notion page JSON matching brain_sync.map_page_to_row expectations."""
    title_prop = {"title": [{"plain_text": name}]}
    base_props: dict = {
        "Name": title_prop,
        "Source Project Hash": {"rich_text": [{"plain_text": "p" * 16}]},
        "Tags": {"multi_select": []},
        "Stack": {"multi_select": []},
    }
    if category == "decisions":
        base_props.update(
            {
                "Context": {"rich_text": [{"plain_text": context}]},
                "Decision": {"rich_text": []},
                "Rationale": {"rich_text": []},
                "Date": {"date": None},
                "Generalizable": {"checkbox": True},
                "Superseded By": {"url": None},
            }
        )
    elif category == "web_cache":
        base_props.update(
            {
                "URL": {"url": "https://ex.com"},
                "Query": {"rich_text": []},
                "Content": {"rich_text": [{"plain_text": context}]},
                "Fetched At": {"date": {"start": "2026-04-23"}},
                "TTL Days": {"number": 30},
                "Domain": {"select": {"name": "ex.com"}},
                "Content Hash": {"rich_text": [{"plain_text": "c" * 16}]},
            }
        )
    elif category == "patterns":
        base_props.update(
            {
                "Description": {"rich_text": [{"plain_text": context}]},
                "When to Use": {"rich_text": []},
                "Example": {"rich_text": []},
                "Date": {"date": None},
                "Confidence": {"select": {"name": "tested"}},
            }
        )
    elif category == "gotchas":
        base_props.update(
            {
                "Description": {"rich_text": [{"plain_text": context}]},
                "Wrong Way": {"rich_text": []},
                "Right Way": {"rich_text": []},
                "Date": {"date": None},
                "Severity": {"select": {"name": "high"}},
                "Evidence URL": {"url": None},
            }
        )
    return {
        "object": "page",
        "id": page_id,
        "parent": {"database_id": db_id},
        "properties": base_props,
        "last_edited_time": "2026-04-23T10:00:00Z",
        "created_time": "2026-04-23T10:00:00Z",
    }


class FakeClient:
    """Minimal NotionClient stand-in for fallback tests."""

    def __init__(self, *, search_results=None, retrieve_map=None, raise_on=None):
        self.search_results = search_results or []
        self.retrieve_map = retrieve_map or {}
        self.raise_on = raise_on or set()
        self.search_calls: list[dict] = []
        self.retrieve_calls: list[str] = []

    def search(self, **kwargs):
        self.search_calls.append(kwargs)
        if "search" in self.raise_on:
            raise ConnectionError("network down")
        return {"results": list(self.search_results), "has_more": False}

    def pages_retrieve(self, page_id):
        self.retrieve_calls.append(page_id)
        if "retrieve" in self.raise_on:
            raise ConnectionError("network down")
        if page_id not in self.retrieve_map:
            raise KeyError(f"not found: {page_id}")
        return self.retrieve_map[page_id]


# ---- search_with_fallback -------------------------------------------------


def test_search_local_only_no_fallback_when_client_none(conn):
    _insert_decision(
        conn, pid="id1", name="Pgbouncer adoption", context="chose pgbouncer"
    )
    out = brain_mcp_read.search_with_fallback(
        conn, client=None, query="pgbouncer", limit=10
    )
    assert len(out["results"]) == 1
    assert out["results"][0]["notion_page_id"] == "id1"
    assert out["warnings"] == []


def test_search_fallback_triggers_when_local_short(conn):
    # Empty local; should fall back
    db_decisions = "db-dec-0000-0000-0000-000000000000"
    page = _notion_page(
        page_id="remote1",
        db_id=db_decisions,
        name="Remote decision",
        context="something",
    )
    client = FakeClient(search_results=[page])
    out = brain_mcp_read.search_with_fallback(
        conn,
        client=client,
        query="decision",
        limit=10,
        database_ids={
            "decisions": db_decisions,
            "web_cache": "",
            "patterns": "",
            "gotchas": "",
        },
    )
    assert len(out["results"]) == 1
    assert out["results"][0]["notion_page_id"] == "remote1"
    assert out["results"][0]["source"] == "notion"
    assert client.search_calls, "Notion search should have been called"


def test_search_fallback_dedup_prefers_local(conn):
    """Local hit with same notion_page_id as remote → remote is dropped."""
    pid = "shared-id-1"
    db_decisions = "db-dec-xxxx"
    _insert_decision(conn, pid=pid, name="Local name", context="pgbouncer local")
    page = _notion_page(
        page_id=pid, db_id=db_decisions, name="Remote name", context="pgbouncer"
    )
    client = FakeClient(search_results=[page])
    out = brain_mcp_read.search_with_fallback(
        conn,
        client=client,
        query="pgbouncer",
        limit=10,
        database_ids={"decisions": db_decisions},
    )
    assert len(out["results"]) == 1
    assert out["results"][0]["name"] == "Local name"  # local won


def test_search_fallback_network_error_returns_local_with_warning(conn):
    _insert_decision(conn, pid="id1", name="A", context="match")
    client = FakeClient(raise_on={"search"})
    out = brain_mcp_read.search_with_fallback(
        conn,
        client=client,
        query="match",
        limit=10,
        database_ids={"decisions": "db1"},
    )
    assert len(out["results"]) == 1
    assert out["results"][0]["notion_page_id"] == "id1"
    assert any("Notion fallback failed" in w for w in out["warnings"])


def test_search_no_fallback_when_local_meets_limit(conn):
    for i in range(5):
        _insert_decision(conn, pid=f"id{i}", name=f"Decision {i}", context="match here")
    client = FakeClient(search_results=[])
    out = brain_mcp_read.search_with_fallback(
        conn,
        client=client,
        query="match",
        limit=3,
        database_ids={"decisions": "db1"},
    )
    assert len(out["results"]) == 3
    assert not client.search_calls, "should not hit Notion when local meets limit"


def test_search_fallback_disabled_flag(conn):
    client = FakeClient(search_results=[])
    out = brain_mcp_read.search_with_fallback(
        conn,
        client=client,
        query="nothing",
        limit=10,
        database_ids={"decisions": "db1"},
        enable_fallback=False,
    )
    assert out["results"] == []
    assert not client.search_calls


def test_search_fallback_skips_pages_outside_brain_dbs(conn):
    our_db = "brain-db-000"
    foreign_db = "other-db-xxx"
    our_page = _notion_page(page_id="ours", db_id=our_db, name="Ours", context="hi")
    foreign_page = _notion_page(
        page_id="foreign", db_id=foreign_db, name="NotOurs", context="hi"
    )
    client = FakeClient(search_results=[foreign_page, our_page])
    out = brain_mcp_read.search_with_fallback(
        conn,
        client=client,
        query="hi",
        limit=10,
        database_ids={"decisions": our_db},
    )
    assert len(out["results"]) == 1
    assert out["results"][0]["notion_page_id"] == "ours"


def test_search_category_filter_passes_through_local(conn):
    _insert_decision(conn, pid="dec1", name="Decision match", context="m")
    _insert_web_cache(conn, pid="wc1", name="Webcache match", content="m")
    out = brain_mcp_read.search_with_fallback(
        conn,
        client=None,
        query="match",
        categories=["decisions"],
        limit=10,
    )
    assert len(out["results"]) == 1
    assert out["results"][0]["category"] == "decisions"


def test_search_invalid_limit(conn):
    out = brain_mcp_read.search_with_fallback(conn, client=None, query="x", limit=0)
    assert out["results"] == []
    assert out["warnings"]


def test_search_empty_query_returns_empty(conn):
    _insert_decision(conn, pid="id1", name="A", context="b")
    out = brain_mcp_read.search_with_fallback(conn, client=None, query="   ", limit=10)
    assert out["results"] == []


def test_search_dash_normalization_in_db_ids(conn):
    """database_ids may include dashes; parent.database_id may not (or vice-versa)."""
    db_with_dashes = "12345678-1234-1234-1234-123456789012"
    db_no_dashes = "12345678123412341234123456789012"
    page = _notion_page(
        page_id="remote1",
        db_id=db_no_dashes,  # parent has no dashes
        name="Remote",
        context="hi",
    )
    client = FakeClient(search_results=[page])
    out = brain_mcp_read.search_with_fallback(
        conn,
        client=client,
        query="hi",
        limit=10,
        database_ids={"decisions": db_with_dashes},  # config has dashes
    )
    assert len(out["results"]) == 1


# ---- get_with_fallback ----------------------------------------------------


def test_get_local_hit_no_fallback(conn):
    _insert_decision(conn, pid="id1", name="Local", context="c")
    client = FakeClient()
    rec, warnings = brain_mcp_read.get_with_fallback(conn, client, "id1", "decisions")
    assert rec is not None
    assert rec["name"] == "Local"
    assert not client.retrieve_calls
    assert warnings == []


def test_get_fallback_to_notion_on_local_miss(conn):
    page = _notion_page(
        page_id="remote1", db_id="db1", name="Remote", context="body text"
    )
    client = FakeClient(retrieve_map={"remote1": page})
    rec, warnings = brain_mcp_read.get_with_fallback(
        conn, client, "remote1", "decisions"
    )
    assert rec is not None
    assert rec["name"] == "Remote"
    assert rec["source"] == "notion"
    assert client.retrieve_calls == ["remote1"]


def test_get_notion_error_returns_warning(conn):
    client = FakeClient(raise_on={"retrieve"})
    rec, warnings = brain_mcp_read.get_with_fallback(
        conn, client, "remote1", "decisions"
    )
    assert rec is None
    assert any("Notion fallback failed" in w for w in warnings)


def test_get_unknown_category_returns_error(conn):
    rec, warnings = brain_mcp_read.get_with_fallback(
        conn, None, "id1", "not_a_category"
    )
    assert rec is None
    assert warnings and "Unknown category" in warnings[0]


def test_get_miss_no_client(conn):
    rec, warnings = brain_mcp_read.get_with_fallback(conn, None, "id1", "decisions")
    assert rec is None
    assert warnings == []


def test_get_fallback_disabled(conn):
    page = _notion_page(page_id="remote1", db_id="db1", name="Remote", context="b")
    client = FakeClient(retrieve_map={"remote1": page})
    rec, warnings = brain_mcp_read.get_with_fallback(
        conn, client, "remote1", "decisions", enable_fallback=False
    )
    assert rec is None
    assert not client.retrieve_calls


# ---- Markdown rendering ---------------------------------------------------


def test_format_record_basic_shape():
    rec = {
        "category": "decisions",
        "notion_page_id": "abc-123",
        "name": "Pgbouncer",
        "snippet": "chose pgbouncer for conn pooling",
        "source_project_hash": "abc123",
        "last_edited_time": "2026-04-23T10:00:00Z",
    }
    md = brain_mcp_read.format_record(rec)
    assert md.startswith("## Pgbouncer  _[decisions]_")
    assert "chose pgbouncer for conn pooling" in md
    assert "id: `abc-123`" in md
    assert "project: `abc123`" in md
    assert "edited: 2026-04-23T10:00:00Z" in md


def test_format_record_web_cache_shows_url():
    rec = {
        "category": "web_cache",
        "notion_page_id": "wc1",
        "name": "Python 3.12 release notes",
        "snippet": "summary",
        "url": "https://python.org/3.12",
        "source_project_hash": "h",
    }
    md = brain_mcp_read.format_record(rec)
    assert "URL: https://python.org/3.12" in md


def test_format_record_pattern_shows_confidence_badge():
    rec = {
        "category": "patterns",
        "notion_page_id": "p1",
        "name": "Singleton via metaclass",
        "confidence": "proven",
        "snippet": "use when",
    }
    md = brain_mcp_read.format_record(rec)
    assert "_[patterns]_" in md
    assert "_proven_" in md


def test_format_record_gotcha_shows_severity_and_evidence():
    rec = {
        "category": "gotchas",
        "notion_page_id": "g1",
        "name": "FTS5 dash pitfall",
        "severity": "high",
        "evidence_url": "https://sqlite.org",
        "snippet": "wrap in quotes",
    }
    md = brain_mcp_read.format_record(rec)
    assert "_high_" in md
    assert "Evidence: https://sqlite.org" in md


def test_format_record_notion_source_marker():
    rec = {
        "category": "decisions",
        "notion_page_id": "r1",
        "name": "X",
        "source": "notion",
    }
    md = brain_mcp_read.format_record(rec)
    assert "source: notion" in md


def test_format_search_results_empty_with_query():
    md = brain_mcp_read.format_search_results([], [], query="pgbouncer")
    assert "No matches for `pgbouncer`" in md


def test_format_search_results_with_warnings():
    md = brain_mcp_read.format_search_results(
        [], ["Notion fallback failed: timeout"], query="x"
    )
    assert "**Warnings:**" in md
    assert "- Notion fallback failed: timeout" in md


def test_format_search_results_multiple():
    recs = [
        {
            "category": "decisions",
            "notion_page_id": "d1",
            "name": "Decision one",
            "snippet": "s1",
        },
        {
            "category": "patterns",
            "notion_page_id": "p1",
            "name": "Pattern one",
            "snippet": "s2",
            "confidence": "tested",
        },
    ]
    md = brain_mcp_read.format_search_results(recs, [])
    assert "Decision one" in md
    assert "Pattern one" in md
    assert "_tested_" in md


def test_format_record_preserves_cyrillic():
    rec = {
        "category": "decisions",
        "notion_page_id": "ru1",
        "name": "Решение: использовать pgbouncer",
        "snippet": "выбрали pgbouncer из-за латентности",
        "source_project_hash": "h",
    }
    md = brain_mcp_read.format_record(rec)
    assert "Решение" in md
    assert "латентности" in md


# ---- _row_to_normalized internals ----------------------------------------


def test_row_to_normalized_parses_tags_json():
    row = {
        "notion_page_id": "x",
        "name": "n",
        "context": "c",
        "tags": json.dumps(["a", "b"]),
        "stack": json.dumps(["python"]),
        "source_project_hash": "h",
        "last_edited_time": "t",
    }
    out = brain_mcp_read._row_to_normalized("decisions", row)
    assert out["tags"] == ["a", "b"]
    assert out["stack"] == ["python"]
    assert out["source"] == "notion"


def test_row_to_normalized_snippet_truncation():
    long_body = "x" * 500
    row = {"notion_page_id": "x", "name": "n", "context": long_body}
    out = brain_mcp_read._row_to_normalized("decisions", row)
    assert out["snippet"].endswith("...")
    assert len(out["snippet"]) <= brain_mcp_read._SNIPPET_MAX_CHARS + 3
