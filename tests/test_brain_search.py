"""Tests for brain local FTS5 search."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import brain_search  # noqa: E402
import brain_sync  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    c = brain_sync.open_brain_db(str(tmp_path / "brain.db"))
    yield c
    c.close()


# --- Helpers ---------------------------------------------------------


def _insert_decision(
    conn,
    *,
    pid: str,
    name: str,
    context: str = "",
    decision: str = "",
    rationale: str = "",
    tags=(),
    stack=(),
    hash_="a" * 16,
    edited: str = "2026-04-23T10:00:00Z",
    date_val: str | None = "2026-04-23",
    generalizable: int = 1,
):
    conn.execute(
        """INSERT INTO brain_decisions(
            notion_page_id, name, context, decision, rationale,
            tags, stack, date_value, source_project_hash,
            generalizable, last_edited_time, created_time)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pid,
            name,
            context,
            decision,
            rationale,
            __import__("json").dumps(list(tags)),
            __import__("json").dumps(list(stack)),
            date_val,
            hash_,
            generalizable,
            edited,
            edited,
        ),
    )
    conn.commit()


def _insert_web_cache(
    conn,
    *,
    pid,
    name,
    content,
    url="https://ex.com/a",
    query_text="",
    domain="ex.com",
    tags=(),
    hash_="a" * 16,
    edited="2026-04-23T10:00:00Z",
    content_hash="c" * 16,
):
    conn.execute(
        """INSERT INTO brain_web_cache(
            notion_page_id, name, url, query, content, fetched_at,
            ttl_days, domain, tags, source_project_hash, content_hash,
            last_edited_time, created_time)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pid,
            name,
            url,
            query_text,
            content,
            edited,
            30,
            domain,
            __import__("json").dumps(list(tags)),
            hash_,
            content_hash,
            edited,
            edited,
        ),
    )
    conn.commit()


def _insert_pattern(
    conn,
    *,
    pid,
    name,
    description,
    when_to_use="",
    example="",
    tags=(),
    stack=(),
    hash_="a" * 16,
    edited="2026-04-23T10:00:00Z",
    confidence="tested",
):
    conn.execute(
        """INSERT INTO brain_patterns(
            notion_page_id, name, description, when_to_use, example,
            tags, stack, source_project_hash, date_value, confidence,
            last_edited_time, created_time)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pid,
            name,
            description,
            when_to_use,
            example,
            __import__("json").dumps(list(tags)),
            __import__("json").dumps(list(stack)),
            hash_,
            "2026-04-23",
            confidence,
            edited,
            edited,
        ),
    )
    conn.commit()


def _insert_gotcha(
    conn,
    *,
    pid,
    name,
    description,
    wrong_way="",
    right_way="",
    tags=(),
    stack=(),
    hash_="a" * 16,
    edited="2026-04-23T10:00:00Z",
    severity="medium",
):
    conn.execute(
        """INSERT INTO brain_gotchas(
            notion_page_id, name, description, wrong_way, right_way,
            tags, stack, source_project_hash, date_value, severity,
            evidence_url, last_edited_time, created_time)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pid,
            name,
            description,
            wrong_way,
            right_way,
            __import__("json").dumps(list(tags)),
            __import__("json").dumps(list(stack)),
            hash_,
            "2026-04-23",
            severity,
            None,
            edited,
            edited,
        ),
    )
    conn.commit()


# --- Query sanitization ---------------------------------------------


def test_sanitize_empty():
    assert brain_search.sanitize_fts_query("") == ""
    assert brain_search.sanitize_fts_query("   ") == ""


def test_sanitize_wraps_in_quotes():
    assert brain_search.sanitize_fts_query("hello") == '"hello"'


def test_sanitize_escapes_embedded_quotes():
    assert brain_search.sanitize_fts_query('a "b" c') == '"a ""b"" c"'


def test_sanitize_neutralizes_dash_and_colon():
    # these would otherwise be FTS5 operators / column qualifiers
    out = brain_search.sanitize_fts_query("foo-bar:baz")
    assert out == '"foo-bar:baz"'


# --- Empty / no-op cases --------------------------------------------


def test_search_empty_query_returns_empty_list(conn):
    assert brain_search.search_local(conn, "") == []
    assert brain_search.search_local(conn, "   ") == []


def test_search_with_no_data_returns_empty(conn):
    assert brain_search.search_local(conn, "anything") == []


def test_search_with_empty_categories_returns_empty(conn):
    _insert_decision(conn, pid="d1", name="Anything", context="ctx")
    assert brain_search.search_local(conn, "Anything", categories=[]) == []


def test_search_negative_limit_raises(conn):
    with pytest.raises(ValueError):
        brain_search.search_local(conn, "x", limit=-1)
    with pytest.raises(ValueError):
        brain_search.search_local(conn, "x", offset=-1)


# --- Hit in each category --------------------------------------------


def test_search_finds_decision(conn):
    _insert_decision(
        conn,
        pid="d1",
        name="Use urllib",
        context="HTTP client choice",
        decision="stdlib urllib",
        tags=["architecture", "dx"],
    )
    out = brain_search.search_local(conn, "urllib")
    assert len(out) == 1
    r = out[0]
    assert r["category"] == "decisions"
    assert r["notion_page_id"] == "d1"
    assert r["name"] == "Use urllib"
    assert r["tags"] == ["architecture", "dx"]
    assert r["date"] == "2026-04-23"
    assert isinstance(r["score"], float)


def test_search_finds_web_cache(conn):
    _insert_web_cache(
        conn,
        pid="wc1",
        name="Notion Docs",
        content="create a page endpoint",
        url="https://dev.notion.com/docs",
        domain="dev.notion.com",
    )
    out = brain_search.search_local(conn, "endpoint")
    assert len(out) == 1
    r = out[0]
    assert r["category"] == "web_cache"
    assert r["url"] == "https://dev.notion.com/docs"
    assert r["domain"] == "dev.notion.com"


def test_search_finds_pattern(conn):
    _insert_pattern(
        conn,
        pid="p1",
        name="Mixin composition",
        description="split large service into mixins",
        when_to_use="when class >400 lines",
        confidence="proven",
    )
    out = brain_search.search_local(conn, "mixins")
    assert len(out) == 1
    assert out[0]["confidence"] == "proven"


def test_search_finds_gotcha(conn):
    _insert_gotcha(
        conn,
        pid="g1",
        name="FTS5 dash trap",
        description="dash is column qualifier in FTS5 MATCH",
        severity="high",
    )
    out = brain_search.search_local(conn, "dash")
    assert len(out) == 1
    assert out[0]["severity"] == "high"


# --- Cross-category ranking -----------------------------------------


def test_search_combines_categories_sorted_by_bm25(conn):
    _insert_decision(conn, pid="d1", name="Doc1", context="alpha beta gamma")
    _insert_pattern(conn, pid="p1", name="Doc2", description="alpha")
    _insert_gotcha(conn, pid="g1", name="Doc3", description="alpha zeta")
    out = brain_search.search_local(conn, "alpha")
    assert len(out) == 3
    scores = [r["score"] for r in out]
    assert scores == sorted(scores)  # ascending (lower = more relevant)


def test_search_categories_filter(conn):
    _insert_decision(conn, pid="d1", name="Doc1", context="alpha")
    _insert_pattern(conn, pid="p1", name="Doc2", description="alpha")
    out = brain_search.search_local(conn, "alpha", categories=["decisions"])
    assert len(out) == 1
    assert out[0]["category"] == "decisions"


def test_search_unknown_category_ignored(conn):
    _insert_decision(conn, pid="d1", name="Doc", context="alpha")
    out = brain_search.search_local(conn, "alpha", categories=["decisions", "bogus"])
    assert len(out) == 1


def test_search_limit_and_offset(conn):
    for i in range(5):
        _insert_decision(
            conn,
            pid=f"d{i}",
            name=f"Doc {i}",
            context=f"alpha text {i}",
        )
    page1 = brain_search.search_local(conn, "alpha", limit=2, offset=0)
    page2 = brain_search.search_local(conn, "alpha", limit=2, offset=2)
    page3 = brain_search.search_local(conn, "alpha", limit=2, offset=4)
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1
    ids = {r["notion_page_id"] for r in page1 + page2 + page3}
    assert len(ids) == 5


# --- Snippet rendering ----------------------------------------------


def test_search_snippet_marks_match(conn):
    _insert_decision(
        conn,
        pid="d1",
        name="Doc",
        context="surrounding text with the target word in it",
    )
    out = brain_search.search_local(conn, "target")
    assert "[target]" in out[0]["snippet"]


# --- Cyrillic and special chars -------------------------------------


def test_search_cyrillic_works(conn):
    _insert_decision(
        conn,
        pid="d1",
        name="Решение",
        context="Использовать urllib вместо requests",
    )
    out = brain_search.search_local(conn, "Использовать")
    assert len(out) == 1
    assert out[0]["name"] == "Решение"


def test_search_query_with_dash_does_not_crash(conn):
    _insert_gotcha(
        conn,
        pid="g1",
        name="Marker",
        description="some-hyphenated-phrase appears here",
    )
    out = brain_search.search_local(conn, "some-hyphenated-phrase")
    assert len(out) == 1


def test_search_query_with_inner_quotes_does_not_crash(conn):
    _insert_decision(
        conn,
        pid="d1",
        name="Doc",
        context='the "quoted" phrase inside',
    )
    out = brain_search.search_local(conn, 'the "quoted" phrase')
    assert len(out) == 1


def test_search_query_with_colon_does_not_crash(conn):
    _insert_pattern(
        conn,
        pid="p1",
        name="Env var",
        description="use name: value syntax",
    )
    out = brain_search.search_local(conn, "name: value")
    assert len(out) == 1


# --- get_by_id ------------------------------------------------------


def test_get_by_id_hit(conn):
    _insert_decision(
        conn,
        pid="d1",
        name="Doc",
        context="x",
        tags=["a"],
        stack=["python"],
    )
    r = brain_search.get_by_id(conn, "decisions", "d1")
    assert r is not None
    assert r["notion_page_id"] == "d1"
    assert r["tags"] == ["a"]
    assert r["stack"] == ["python"]
    assert r["score"] == 0.0


def test_get_by_id_miss(conn):
    assert brain_search.get_by_id(conn, "decisions", "missing") is None


def test_get_by_id_unknown_category_raises(conn):
    with pytest.raises(ValueError):
        brain_search.get_by_id(conn, "bogus", "x")
