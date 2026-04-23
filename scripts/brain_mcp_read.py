"""Brain MCP read-path helpers — local FTS5 first, Notion API fallback.

Pure functions used by the tausik-brain MCP handlers. No MCP runtime is
imported here, so everything is directly unit-testable.

Design contract:
  - `search_with_fallback`: hit local bm25 index; if local has fewer than
    `limit` hits AND a Notion client is available AND fallback is enabled,
    query the Notion `/search` endpoint and merge with dedup by
    `notion_page_id`. A network failure in the fallback never raises —
    the local result is returned with a warning string.
  - `get_with_fallback`: local lookup by id; on miss, use Notion
    `pages.retrieve` if client is available; normalized to the same
    shape as local hits.
  - `format_record` / `format_search_results`: markdown renderers shared
    by both tools.

Design reference: references/brain-db-schema.md §6 (search ergonomics).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

import brain_search
import brain_sync

CATEGORIES = ("decisions", "web_cache", "patterns", "gotchas")

_SNIPPET_MAX_CHARS = 240


def _canonical_id(nid: str | None) -> str:
    if not nid:
        return ""
    return nid.replace("-", "").lower()


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


def _row_to_normalized(category: str, row: dict) -> dict:
    """Turn a `map_page_to_row` dict into the search/format shape.

    Mirrors the contract of `brain_search._normalize_row` so the output
    is interchangeable with local hits downstream (format_record).
    """
    body_field = {
        "decisions": "context",
        "web_cache": "content",
        "patterns": "description",
        "gotchas": "description",
    }[category]
    body = row.get(body_field) or ""
    snippet = body[:_SNIPPET_MAX_CHARS] + (
        "..." if len(body) > _SNIPPET_MAX_CHARS else ""
    )

    out: dict[str, Any] = {
        "category": category,
        "notion_page_id": row.get("notion_page_id", ""),
        "name": row.get("name", ""),
        "snippet": snippet,
        "score": 0.0,
        "tags": _parse_json_list(row.get("tags")),
        "stack": _parse_json_list(row.get("stack")),
        "source_project_hash": row.get("source_project_hash", ""),
        "last_edited_time": row.get("last_edited_time", ""),
        "source": "notion",
    }
    if category == "decisions":
        out["date"] = row.get("date_value")
    elif category == "web_cache":
        out["url"] = row.get("url")
        out["domain"] = row.get("domain")
        out["fetched_at"] = row.get("fetched_at")
    elif category == "patterns":
        out["date"] = row.get("date_value")
        out["confidence"] = row.get("confidence")
    elif category == "gotchas":
        out["date"] = row.get("date_value")
        out["severity"] = row.get("severity")
        out["evidence_url"] = row.get("evidence_url")
    return out


# ---- Notion fallback --------------------------------------------------


def _categorize_page(page: dict, cat_by_db: dict[str, str]) -> str | None:
    parent = page.get("parent") or {}
    parent_db = _canonical_id(parent.get("database_id"))
    return cat_by_db.get(parent_db)


def search_notion(
    client: Any,
    query: str,
    database_ids: dict,
    categories: list[str],
    limit: int,
) -> list[dict]:
    """Call Notion /search, keep pages whose parent is one of our brain DBs."""
    cat_by_db: dict[str, str] = {}
    for cat in categories:
        db_id = (database_ids or {}).get(cat)
        if db_id:
            cat_by_db[_canonical_id(db_id)] = cat
    if not cat_by_db:
        return []

    resp = client.search(
        query=query,
        filter={"value": "page", "property": "object"},
        page_size=min(max(limit * 2, 5), 100),
    )
    out: list[dict] = []
    for page in resp.get("results", []):
        if page.get("object") != "page":
            continue
        category = _categorize_page(page, cat_by_db)
        if category is None:
            continue
        try:
            row = brain_sync.map_page_to_row(category, page)
        except (KeyError, ValueError):
            continue
        out.append(_row_to_normalized(category, row))
        if len(out) >= limit:
            break
    return out


def search_with_fallback(
    conn: sqlite3.Connection,
    client: Any | None,
    query: str,
    *,
    categories: list[str] | None = None,
    limit: int = 10,
    database_ids: dict | None = None,
    enable_fallback: bool = True,
) -> dict:
    """Local search, merged with Notion fallback on shortfall. Never raises."""
    if limit < 1:
        return {"results": [], "warnings": ["limit must be >= 1"]}

    try:
        local = brain_search.search_local(
            conn, query, categories=categories, limit=limit
        )
    except Exception as e:  # noqa: BLE001
        return {"results": [], "warnings": [f"local search failed: {e}"]}

    warnings: list[str] = []
    remote: list[dict] = []
    should_fallback = (
        enable_fallback
        and client is not None
        and bool(database_ids)
        and len(local) < limit
    )
    if should_fallback:
        try:
            remote = search_notion(
                client,
                query,
                database_ids or {},
                categories or list(CATEGORIES),
                limit,
            )
        except Exception as e:  # noqa: BLE001
            warnings.append(f"Notion fallback failed: {e}; showing local results only")

    seen = {r["notion_page_id"] for r in local if r.get("notion_page_id")}
    merged: list[dict] = list(local)
    for r in remote:
        pid = r.get("notion_page_id")
        if pid and pid not in seen:
            merged.append(r)
            seen.add(pid)

    return {"results": merged[:limit], "warnings": warnings}


def get_with_fallback(
    conn: sqlite3.Connection,
    client: Any | None,
    notion_page_id: str,
    category: str,
    *,
    enable_fallback: bool = True,
) -> tuple[dict | None, list[str]]:
    """Local get; fall back to Notion pages.retrieve. Never raises."""
    warnings: list[str] = []
    try:
        local = brain_search.get_by_id(conn, category, notion_page_id)
    except ValueError as e:
        return None, [str(e)]
    except Exception as e:  # noqa: BLE001
        return None, [f"local get failed: {e}"]
    if local is not None:
        return local, warnings

    if not enable_fallback or client is None:
        return None, warnings

    try:
        page = client.pages_retrieve(notion_page_id)
    except Exception as e:  # noqa: BLE001
        warnings.append(f"Notion fallback failed: {e}")
        return None, warnings

    try:
        row = brain_sync.map_page_to_row(category, page)
    except (KeyError, ValueError) as e:
        warnings.append(f"Notion page shape unexpected: {e}")
        return None, warnings
    return _row_to_normalized(category, row), warnings


# ---- Markdown rendering ----------------------------------------------


def _badge_line(rec: dict) -> str:
    category = rec.get("category") or "unknown"
    badges = [f"_[{category}]_"]
    if category == "patterns" and rec.get("confidence"):
        badges.append(f"_{rec['confidence']}_")
    if category == "gotchas" and rec.get("severity"):
        badges.append(f"_{rec['severity']}_")
    return " ".join(badges)


def _category_extras(rec: dict) -> list[str]:
    category = rec.get("category")
    extras: list[str] = []
    if category == "web_cache" and rec.get("url"):
        extras.append(f"URL: {rec['url']}")
    if category == "gotchas" and rec.get("evidence_url"):
        extras.append(f"Evidence: {rec['evidence_url']}")
    return extras


def _footer(rec: dict) -> str:
    parts = [f"id: `{rec.get('notion_page_id') or '?'}`"]
    if rec.get("source_project_hash"):
        parts.append(f"project: `{rec['source_project_hash']}`")
    if rec.get("last_edited_time"):
        parts.append(f"edited: {rec['last_edited_time']}")
    if rec.get("source") == "notion":
        parts.append("source: notion")
    return "— " + " | ".join(parts)


def format_record(rec: dict) -> str:
    """Single normalized record → markdown block."""
    name = rec.get("name") or "(untitled)"
    lines = [f"## {name}  {_badge_line(rec)}"]
    extras = _category_extras(rec)
    if extras:
        lines.append("")
        lines.extend(extras)
    snippet = rec.get("snippet")
    if snippet:
        lines.append("")
        lines.append(snippet)
    lines.append("")
    lines.append(_footer(rec))
    return "\n".join(lines)


def format_search_results(
    results: list[dict], warnings: list[str], *, query: str | None = None
) -> str:
    """List of records (+ warnings) → markdown."""
    parts: list[str] = []
    if not results:
        header = "_No matches._"
        if query:
            header = f"_No matches for `{query}`._"
        parts.append(header)
    else:
        parts.extend(format_record(r) for r in results)
    if warnings:
        parts.append("---")
        parts.append("**Warnings:**")
        parts.extend(f"- {w}" for w in warnings)
    return "\n\n".join(parts)
