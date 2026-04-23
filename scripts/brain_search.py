"""Brain local FTS5 search — fast offline path over the SQLite mirror.

Works directly on the `brain_*` + `fts_brain_*` virtual tables created
by brain_schema.apply_schema. Notion network I/O is NOT required.

Search ranks results with bm25 (lower = more relevant) across all
enabled categories, returning a normalized dict per hit.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

CATEGORIES = ("decisions", "web_cache", "patterns", "gotchas")

# table, fts_table, snippet column (0-based index into fts columns)
_TABLES: dict[str, dict[str, Any]] = {
    "decisions": {
        "table": "brain_decisions",
        "fts": "fts_brain_decisions",
        # fts columns: name, context, decision, rationale, tags
        "snippet_col": 1,  # context
    },
    "web_cache": {
        "table": "brain_web_cache",
        "fts": "fts_brain_web_cache",
        # fts columns: name, url, query, content, domain, tags
        "snippet_col": 3,  # content
    },
    "patterns": {
        "table": "brain_patterns",
        "fts": "fts_brain_patterns",
        # fts columns: name, description, when_to_use, example, tags
        "snippet_col": 1,  # description
    },
    "gotchas": {
        "table": "brain_gotchas",
        "fts": "fts_brain_gotchas",
        # fts columns: name, description, wrong_way, right_way, tags
        "snippet_col": 1,  # description
    },
}

SNIPPET_MARK_OPEN = "["
SNIPPET_MARK_CLOSE = "]"
SNIPPET_ELLIPSIS = "..."
SNIPPET_TOKENS = 32


def sanitize_fts_query(query: str) -> str:
    """Wrap query as an FTS5 phrase query, escaping embedded quotes.

    FTS5 treats `-`, `:`, `*`, AND, OR, NOT as operators; wrapping the
    whole query in double quotes turns it into a phrase match, neutralizing
    the operators. Inner `"` is escaped as `""` per SQL convention.
    """
    q = query.strip()
    if not q:
        return ""
    escaped = q.replace('"', '""')
    return f'"{escaped}"'


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(value, list):
        return []
    return [str(x) for x in value if x]


def _normalize_row(category: str, row: sqlite3.Row, snippet: str, score: float) -> dict:
    out: dict[str, Any] = {
        "category": category,
        "notion_page_id": row["notion_page_id"],
        "name": row["name"],
        "snippet": snippet,
        "score": score,
        "tags": _parse_json_list(row["tags"]),
        "stack": _parse_json_list(row["stack"]) if _has_col(row, "stack") else [],
        "source_project_hash": row["source_project_hash"],
        "last_edited_time": row["last_edited_time"],
    }
    if category == "decisions":
        out["date"] = row["date_value"]
    elif category == "web_cache":
        out["url"] = row["url"]
        out["domain"] = row["domain"]
        out["fetched_at"] = row["fetched_at"]
    elif category == "patterns":
        out["date"] = row["date_value"]
        out["confidence"] = row["confidence"]
    elif category == "gotchas":
        out["date"] = row["date_value"]
        out["severity"] = row["severity"]
        out["evidence_url"] = row["evidence_url"]
    return out


def _has_col(row: sqlite3.Row, name: str) -> bool:
    try:
        row[name]
    except (IndexError, KeyError):
        return False
    return True


def _search_category(
    conn: sqlite3.Connection,
    category: str,
    safe_query: str,
) -> list[dict]:
    meta = _TABLES[category]
    table = meta["table"]
    fts = meta["fts"]
    snippet_col = meta["snippet_col"]

    sql = f"""
        SELECT t.*,
               snippet({fts}, ?, ?, ?, ?, ?) AS _snippet,
               bm25({fts}) AS _score
        FROM {fts} f
        JOIN {table} t ON t.id = f.rowid
        WHERE {fts} MATCH ?
        ORDER BY _score ASC
    """
    params = (
        snippet_col,
        SNIPPET_MARK_OPEN,
        SNIPPET_MARK_CLOSE,
        SNIPPET_ELLIPSIS,
        SNIPPET_TOKENS,
        safe_query,
    )
    rows = conn.execute(sql, params).fetchall()
    return [
        _normalize_row(category, r, r["_snippet"], float(r["_score"])) for r in rows
    ]


def search_local(
    conn: sqlite3.Connection,
    query: str,
    *,
    categories: list[str] | tuple[str, ...] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Search the local brain mirror. Returns normalized dicts sorted by relevance."""
    safe = sanitize_fts_query(query)
    if not safe:
        return []
    cats = (
        [c for c in categories if c in _TABLES]
        if categories is not None
        else list(CATEGORIES)
    )
    if not cats:
        return []
    if limit < 0 or offset < 0:
        raise ValueError("limit and offset must be non-negative")

    merged: list[dict] = []
    for category in cats:
        merged.extend(_search_category(conn, category, safe))

    merged.sort(key=lambda r: r["score"])
    if offset:
        merged = merged[offset:]
    return merged[:limit]


def get_by_id(
    conn: sqlite3.Connection,
    category: str,
    notion_page_id: str,
) -> dict | None:
    """Exact lookup by category + notion_page_id."""
    if category not in _TABLES:
        raise ValueError(f"Unknown category: {category!r}")
    table = _TABLES[category]["table"]
    row = conn.execute(
        f"SELECT * FROM {table} WHERE notion_page_id = ?", (notion_page_id,)
    ).fetchone()
    if row is None:
        return None
    return _normalize_row(category, row, snippet="", score=0.0)
