"""Tests for brain pull-sync (Notion → local SQLite mirror)."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import brain_sync  # noqa: E402


# --- Helpers ---------------------------------------------------------


class _FakeNotionClient:
    """Records iter_database_query calls and returns pre-queued page batches."""

    def __init__(self):
        self._queues: dict[str, list[list[dict]]] = {}
        self.calls: list[dict] = []
        self.error: Exception | None = None

    def queue(self, database_id: str, pages: list[dict]) -> None:
        self._queues.setdefault(database_id, []).append(list(pages))

    def iter_database_query(self, database_id, *, filter=None, sorts=None):
        self.calls.append(
            {"database_id": database_id, "filter": filter, "sorts": sorts}
        )
        if self.error is not None:
            raise self.error
        batches = self._queues.get(database_id, [])
        if not batches:
            return
        batch = batches.pop(0)
        for page in batch:
            yield page


def _page_decision(
    *,
    pid: str,
    name: str,
    edited: str,
    tags=None,
    generalizable: bool = True,
    hash_="a" * 16,
) -> dict:
    return {
        "id": pid,
        "created_time": edited,
        "last_edited_time": edited,
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": name}]},
            "Context": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "ctx"}],
            },
            "Decision": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "dec"}],
            },
            "Rationale": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "why"}],
            },
            "Tags": {
                "type": "multi_select",
                "multi_select": [{"name": t} for t in (tags or [])],
            },
            "Stack": {"type": "multi_select", "multi_select": []},
            "Date": {"type": "date", "date": {"start": "2026-04-23"}},
            "Source Project Hash": {
                "type": "rich_text",
                "rich_text": [{"plain_text": hash_}],
            },
            "Generalizable": {"type": "checkbox", "checkbox": generalizable},
        },
    }


@pytest.fixture
def conn(tmp_path):
    c = brain_sync.open_brain_db(str(tmp_path / "brain.db"))
    yield c
    c.close()


# --- Mapping ---------------------------------------------------------


def test_map_decision_reads_all_types():
    page = _page_decision(
        pid="page-1",
        name="Use urllib",
        edited="2026-04-23T10:00:00.000Z",
        tags=["architecture", "dx"],
    )
    row = brain_sync.map_page_to_row("decisions", page)
    assert row["notion_page_id"] == "page-1"
    assert row["name"] == "Use urllib"
    assert row["context"] == "ctx"
    assert row["decision"] == "dec"
    assert row["rationale"] == "why"
    assert json.loads(row["tags"]) == ["architecture", "dx"]
    assert json.loads(row["stack"]) == []
    assert row["date_value"] == "2026-04-23"
    assert row["generalizable"] == 1
    assert row["last_edited_time"] == "2026-04-23T10:00:00.000Z"


def test_map_decision_generalizable_false_becomes_zero():
    page = _page_decision(pid="p", name="n", edited="x", generalizable=False)
    row = brain_sync.map_page_to_row("decisions", page)
    assert row["generalizable"] == 0


def test_map_web_cache():
    page = {
        "id": "wc-1",
        "created_time": "2026-04-23T10:00:00Z",
        "last_edited_time": "2026-04-23T10:00:00Z",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Doc"}]},
            "URL": {"type": "url", "url": "https://example.com/a"},
            "Query": {"type": "rich_text", "rich_text": []},
            "Content": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "part1"}, {"plain_text": "part2"}],
            },
            "Fetched At": {
                "type": "date",
                "date": {"start": "2026-04-23T09:00:00Z"},
            },
            "TTL Days": {"type": "number", "number": 90},
            "Domain": {"type": "select", "select": {"name": "example.com"}},
            "Tags": {
                "type": "multi_select",
                "multi_select": [{"name": "docs"}],
            },
            "Source Project Hash": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "h1h1h1h1h1h1h1h1"}],
            },
            "Content Hash": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "c0c0c0c0c0c0c0c0"}],
            },
        },
    }
    row = brain_sync.map_page_to_row("web_cache", page)
    assert row["url"] == "https://example.com/a"
    assert row["content"] == "part1part2"
    assert row["ttl_days"] == 90
    assert row["domain"] == "example.com"
    assert json.loads(row["tags"]) == ["docs"]
    assert row["fetched_at"] == "2026-04-23T09:00:00Z"
    assert row["content_hash"] == "c0c0c0c0c0c0c0c0"


def test_map_web_cache_default_ttl_when_missing():
    page = {
        "id": "wc-2",
        "created_time": "x",
        "last_edited_time": "x",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "n"}]},
            "Source Project Hash": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "h"}],
            },
            "Content Hash": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "c"}],
            },
            "Fetched At": {"type": "date", "date": {"start": "x"}},
        },
    }
    row = brain_sync.map_page_to_row("web_cache", page)
    assert row["ttl_days"] == 30


def test_map_pattern_and_gotcha_confidence_severity():
    pattern_page = {
        "id": "pat-1",
        "created_time": "x",
        "last_edited_time": "x",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "P"}]},
            "Description": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "desc"}],
            },
            "When to Use": {"type": "rich_text", "rich_text": []},
            "Example": {"type": "rich_text", "rich_text": []},
            "Tags": {"type": "multi_select", "multi_select": []},
            "Stack": {"type": "multi_select", "multi_select": []},
            "Source Project Hash": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "h"}],
            },
            "Confidence": {"type": "select", "select": {"name": "proven"}},
        },
    }
    row = brain_sync.map_page_to_row("patterns", pattern_page)
    assert row["confidence"] == "proven"

    gotcha_page = {
        "id": "got-1",
        "created_time": "x",
        "last_edited_time": "x",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "G"}]},
            "Description": {"type": "rich_text", "rich_text": []},
            "Wrong Way": {"type": "rich_text", "rich_text": []},
            "Right Way": {"type": "rich_text", "rich_text": []},
            "Tags": {"type": "multi_select", "multi_select": []},
            "Stack": {"type": "multi_select", "multi_select": []},
            "Source Project Hash": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "h"}],
            },
            "Severity": {"type": "select", "select": {"name": "high"}},
            "Evidence URL": {"type": "url", "url": "https://ex.com/i"},
        },
    }
    row2 = brain_sync.map_page_to_row("gotchas", gotcha_page)
    assert row2["severity"] == "high"
    assert row2["evidence_url"] == "https://ex.com/i"


def test_map_unknown_category_raises():
    with pytest.raises(ValueError):
        brain_sync.map_page_to_row("bogus", {"id": "x"})


# --- upsert_page column whitelist (SQL-injection defense) ------------


def _minimal_decision_row() -> dict:
    return {
        "notion_page_id": "page-1",
        "name": "d1",
        "context": "",
        "decision": "x",
        "rationale": "",
        "tags": "[]",
        "stack": "[]",
        "date_value": None,
        "source_project_hash": "abc123",
        "generalizable": 1,
        "superseded_by": None,
        "last_edited_time": "2026-04-24T10:00:00.000Z",
        "created_time": "2026-04-24T10:00:00.000Z",
    }


def test_upsert_page_rejects_unknown_column(conn):
    row = _minimal_decision_row()
    row["DROP TABLE brain_decisions--"] = "pwned"
    with pytest.raises(ValueError) as exc:
        brain_sync.upsert_page(conn, "decisions", row)
    assert "Rejected unknown column" in str(exc.value)
    assert "DROP TABLE" in str(exc.value)


def test_upsert_page_rejects_unknown_category(conn):
    with pytest.raises(ValueError) as exc:
        brain_sync.upsert_page(conn, "bogus", {"notion_page_id": "x"})
    assert "Unknown category" in str(exc.value)


def test_allowed_cols_matches_schema():
    """Schema-drift guard: _ALLOWED_COLS_OF must exactly match the columns
    declared for each brain_<category> table in brain_schema.SCHEMA_SQL.
    If a future migration adds a column to the schema and the mapper starts
    emitting it, this test fails BEFORE upsert_page silently starts raising
    ValueError at runtime."""
    import re

    import brain_schema

    schema_sql = brain_schema.SCHEMA_SQL
    # Match `CREATE TABLE IF NOT EXISTS <name> ( ... );` blocks.
    table_re = re.compile(
        r"CREATE TABLE IF NOT EXISTS\s+(brain_\w+)\s*\((.*?)\);",
        re.DOTALL,
    )
    tables = {m.group(1): m.group(2) for m in table_re.finditer(schema_sql)}

    for category, table_name in brain_sync._TABLE_OF.items():
        assert table_name in tables, f"Missing schema for {table_name}"
        body = tables[table_name]
        cols: set[str] = set()
        for line in body.splitlines():
            s = line.strip().rstrip(",")
            if not s:
                continue
            # Skip CHECK(...) continuation lines and mid-column constraints.
            if s.startswith(("CHECK", ")", "FOREIGN KEY")):
                continue
            name = s.split()[0].strip()
            # First token of a column decl is the column name.
            if name.isidentifier():
                cols.add(name)
        # `id` is auto-increment PK, never inserted by upsert.
        expected = cols - {"id"}
        actual = brain_sync._ALLOWED_COLS_OF[category]
        assert expected == actual, (
            f"{category}: schema has {expected - actual or '-'} "
            f"not in whitelist; whitelist has {actual - expected or '-'} "
            f"not in schema"
        )


def test_upsert_page_accepts_schema_exact_columns(conn):
    brain_sync.upsert_page(conn, "decisions", _minimal_decision_row())
    out = conn.execute(
        "SELECT notion_page_id, decision FROM brain_decisions"
    ).fetchone()
    assert out["notion_page_id"] == "page-1"
    assert out["decision"] == "x"


def test_upsert_page_accepts_subset_of_columns(conn):
    """map_page_to_row does not emit every column; the whitelist MUST
    allow subset-rows that happen to omit columns with DB defaults."""
    row = _minimal_decision_row()
    # Drop columns that have DB defaults — simulates a mapper that chose
    # not to emit them. generalizable has DEFAULT 1, stack has DEFAULT '[]'.
    del row["stack"]
    del row["generalizable"]
    brain_sync.upsert_page(conn, "decisions", row)
    out = conn.execute("SELECT stack, generalizable FROM brain_decisions").fetchone()
    assert out["stack"] == "[]"
    assert out["generalizable"] == 1


# --- sync_category ---------------------------------------------------


def test_sync_category_empty_db_pulls_without_filter(conn):
    client = _FakeNotionClient()
    client.queue(
        "db-1",
        [
            _page_decision(pid="p-1", name="A", edited="2026-04-23T10:00:00Z"),
            _page_decision(pid="p-2", name="B", edited="2026-04-23T11:00:00Z"),
        ],
    )
    result = brain_sync.sync_category(client, conn, "db-1", "decisions")
    assert result == {
        "fetched": 2,
        "upserted": 2,
        "last_edited_time": "2026-04-23T11:00:00Z",
    }
    # No filter on initial pull
    assert client.calls[0]["filter"] is None
    assert client.calls[0]["sorts"] == [
        {"timestamp": "last_edited_time", "direction": "ascending"}
    ]

    rows = conn.execute(
        "SELECT notion_page_id, name FROM brain_decisions ORDER BY notion_page_id"
    ).fetchall()
    assert [(r[0], r[1]) for r in rows] == [("p-1", "A"), ("p-2", "B")]


def test_sync_category_second_run_uses_last_pull_at_filter(conn):
    client = _FakeNotionClient()
    client.queue(
        "db-1",
        [_page_decision(pid="p-1", name="A", edited="2026-04-23T10:00:00Z")],
    )
    brain_sync.sync_category(client, conn, "db-1", "decisions")

    # Second run: queue a newer page, expect filter to reference first edit time
    client.queue(
        "db-1",
        [_page_decision(pid="p-2", name="B", edited="2026-04-23T12:00:00Z")],
    )
    brain_sync.sync_category(client, conn, "db-1", "decisions")

    second_call = client.calls[1]
    assert second_call["filter"] == {
        "timestamp": "last_edited_time",
        "last_edited_time": {"on_or_after": "2026-04-23T10:00:00Z"},
    }


def test_sync_category_upserts_same_page_id(conn):
    client = _FakeNotionClient()
    client.queue(
        "db-1",
        [_page_decision(pid="p-1", name="Original", edited="2026-04-23T10:00:00Z")],
    )
    brain_sync.sync_category(client, conn, "db-1", "decisions")

    client.queue(
        "db-1",
        [_page_decision(pid="p-1", name="Rewritten", edited="2026-04-23T11:00:00Z")],
    )
    brain_sync.sync_category(client, conn, "db-1", "decisions")

    rows = conn.execute(
        "SELECT name FROM brain_decisions WHERE notion_page_id='p-1'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "Rewritten"


def test_sync_category_updates_sync_state_on_success(conn):
    client = _FakeNotionClient()
    client.queue(
        "db-1",
        [_page_decision(pid="p-1", name="A", edited="2026-04-23T10:00:00Z")],
    )
    brain_sync.sync_category(client, conn, "db-1", "decisions")

    state = conn.execute(
        "SELECT last_pull_at, last_error, last_error_at FROM sync_state WHERE category='decisions'"
    ).fetchone()
    assert state["last_pull_at"] == "2026-04-23T10:00:00Z"
    assert state["last_error"] is None
    assert state["last_error_at"] is None


def test_sync_category_records_error_and_reraises(conn):
    class _Boom(Exception):
        pass

    client = _FakeNotionClient()
    client.error = _Boom("network exploded")
    with pytest.raises(_Boom):
        brain_sync.sync_category(client, conn, "db-1", "decisions")

    state = conn.execute(
        "SELECT last_pull_at, last_error FROM sync_state WHERE category='decisions'"
    ).fetchone()
    assert state is not None
    assert "network exploded" in state["last_error"]


def test_sync_category_empty_result_leaves_last_pull_at_none(conn):
    client = _FakeNotionClient()
    client.queue("db-1", [])
    result = brain_sync.sync_category(client, conn, "db-1", "decisions")
    assert result["fetched"] == 0
    assert result["last_edited_time"] is None
    state = conn.execute(
        "SELECT last_pull_at, last_error FROM sync_state WHERE category='decisions'"
    ).fetchone()
    assert state["last_pull_at"] is None
    assert state["last_error"] is None


# --- sync_all --------------------------------------------------------


def test_sync_all_runs_all_four_categories(conn):
    client = _FakeNotionClient()
    client.queue(
        "db-dec",
        [_page_decision(pid="d-1", name="D", edited="2026-04-23T10:00:00Z")],
    )
    client.queue("db-wc", [])
    client.queue("db-pat", [])
    client.queue("db-got", [])

    db_ids = {
        "decisions": "db-dec",
        "web_cache": "db-wc",
        "patterns": "db-pat",
        "gotchas": "db-got",
    }
    results = brain_sync.sync_all(client, conn, db_ids)
    assert set(results.keys()) == {"decisions", "web_cache", "patterns", "gotchas"}
    assert results["decisions"]["fetched"] == 1
    assert results["web_cache"]["fetched"] == 0


def test_sync_all_reports_missing_database_id(conn):
    client = _FakeNotionClient()
    db_ids = {
        "decisions": "db-dec",
        "web_cache": "",
        "patterns": "db-pat",
        "gotchas": "db-got",
    }
    client.queue("db-dec", [])
    client.queue("db-pat", [])
    client.queue("db-got", [])

    results = brain_sync.sync_all(client, conn, db_ids)
    assert "error" in results["web_cache"]
    assert results["decisions"].get("fetched") == 0


def test_sync_all_continues_after_one_category_fails(conn):
    class _Boom(Exception):
        pass

    class _SelectiveClient(_FakeNotionClient):
        def iter_database_query(self, database_id, *, filter=None, sorts=None):
            if database_id == "db-dec":
                raise _Boom("decisions blew up")
            yield from super().iter_database_query(
                database_id, filter=filter, sorts=sorts
            )

    client = _SelectiveClient()
    client.queue("db-wc", [])
    client.queue("db-pat", [])
    client.queue("db-got", [])

    db_ids = {
        "decisions": "db-dec",
        "web_cache": "db-wc",
        "patterns": "db-pat",
        "gotchas": "db-got",
    }
    results = brain_sync.sync_all(client, conn, db_ids)
    assert "error" in results["decisions"]
    assert results["web_cache"].get("fetched") == 0
    assert results["patterns"].get("fetched") == 0
    assert results["gotchas"].get("fetched") == 0
