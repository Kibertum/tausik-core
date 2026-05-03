"""Brain local FTS5 search — fast offline path over the SQLite mirror.

Works directly on the `brain_*` + `fts_brain_*` virtual tables created
by brain_schema.apply_schema. Notion network I/O is NOT required.

Search ranks results with bm25 (lower = more relevant) across all
enabled categories, returning a normalized dict per hit.

Optional ``prefer_stack`` (used by MCP ``brain_search``) widens the local
candidate pool and lets callers apply ``apply_prefer_stack_ranking`` after
merging with Notion hits — entries whose ``stack`` overlaps preferred labels
get a score bonus (lower effective rank).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

# bm25 is lower = better; subtract boost so preferred-stack rows rank higher.
_STACK_MATCH_BONUS = 3.0
_MAX_STACK_BONUS = 15.0

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


def prefer_stack_nonempty(prefer_stack: list[str] | None) -> bool:
    """True if any non-whitespace preferred stack hint is present."""
    if not prefer_stack:
        return False
    return any(str(p).strip() for p in prefer_stack)


def _prefer_stack_normalized(prefer_stack: list[str] | None) -> list[str]:
    if not prefer_stack:
        return []
    return [str(p).strip().lower() for p in prefer_stack if str(p).strip()]


def stack_boost_for_row(rec: dict, prefer_norm: list[str]) -> float:
    """Positive boost subtracted from bm25 ``score`` for ranking (larger = better position)."""
    if not prefer_norm:
        return 0.0
    stacks: list[str] = []
    for s in rec.get("stack") or []:
        if isinstance(s, str) and s.strip():
            stacks.append(s.strip().lower())
    if not stacks:
        return 0.0
    bonus = 0.0
    matched_prefs: set[str] = set()
    for pref in prefer_norm:
        if pref in matched_prefs:
            continue
        for st in stacks:
            if pref == st or pref in st or st in pref:
                bonus += _STACK_MATCH_BONUS
                matched_prefs.add(pref)
                break
    return min(bonus, _MAX_STACK_BONUS)


def apply_prefer_stack_ranking(
    rows: list[dict], prefer_stack: list[str] | None
) -> list[dict]:
    """Sort by bm25 score with stack overlap bonus; stable tie-break on page id."""
    if not rows:
        return rows
    pn = _prefer_stack_normalized(prefer_stack)
    if not pn:
        return rows

    def sort_key(r: dict) -> tuple[float, str]:
        raw = float(r.get("score") or 0)
        eff = raw - stack_boost_for_row(r, pn)
        return (eff, str(r.get("notion_page_id") or ""))

    return sorted(rows, key=sort_key)


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
    prefer_stack: list[str] | None = None,
) -> list[dict]:
    """Search the local brain mirror. Returns normalized dicts sorted by bm25 only.

    When ``prefer_stack`` is set, returns up to ``min(limit * 5, 100)`` rows so a
    caller can rerank with :func:`apply_prefer_stack_ranking` without dropping
    better stack matches that bm25 ranked lower.
    """
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

    out_cap = limit
    if prefer_stack_nonempty(prefer_stack):
        out_cap = min(max(limit * 5, limit), 100)

    merged: list[dict] = []
    for category in cats:
        merged.extend(_search_category(conn, category, safe))

    merged.sort(key=lambda r: r["score"])
    if offset:
        merged = merged[offset:]
    return merged[:out_cap]


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
