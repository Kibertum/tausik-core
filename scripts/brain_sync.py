"""Brain pull-sync: Notion → local SQLite mirror.

Pulls delta pages from each Notion database into the matching
brain_* SQLite table, using `last_edited_time` as the high-water mark.

The sync is idempotent: INSERT OR REPLACE by notion_page_id.
Failures in one category do not stop the others.

Design reference: references/brain-db-schema.md §5.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

import brain_schema

logger = logging.getLogger(__name__)

CATEGORIES = ("decisions", "web_cache", "patterns", "gotchas")

_TABLE_OF = {
    "decisions": "brain_decisions",
    "web_cache": "brain_web_cache",
    "patterns": "brain_patterns",
    "gotchas": "brain_gotchas",
}

# Exact set of columns each brain_* table accepts via upsert. Keep in sync
# with brain_schema.SCHEMA_SQL. `upsert_page` refuses any row key outside
# this whitelist — defense against an untrusted mapper ever sneaking a
# column name into the SQL string.
_ALLOWED_COLS_OF: dict[str, frozenset[str]] = {
    "decisions": frozenset(
        {
            "notion_page_id",
            "name",
            "context",
            "decision",
            "rationale",
            "tags",
            "stack",
            "date_value",
            "source_project_hash",
            "generalizable",
            "superseded_by",
            "last_edited_time",
            "created_time",
        }
    ),
    "web_cache": frozenset(
        {
            "notion_page_id",
            "name",
            "url",
            "query",
            "content",
            "fetched_at",
            "ttl_days",
            "domain",
            "tags",
            "source_project_hash",
            "content_hash",
            "last_edited_time",
            "created_time",
        }
    ),
    "patterns": frozenset(
        {
            "notion_page_id",
            "name",
            "description",
            "when_to_use",
            "example",
            "tags",
            "stack",
            "source_project_hash",
            "date_value",
            "confidence",
            "last_edited_time",
            "created_time",
        }
    ),
    "gotchas": frozenset(
        {
            "notion_page_id",
            "name",
            "description",
            "wrong_way",
            "right_way",
            "tags",
            "stack",
            "source_project_hash",
            "date_value",
            "severity",
            "evidence_url",
            "last_edited_time",
            "created_time",
        }
    ),
}


# --- DB setup ---------------------------------------------------------


def open_brain_db(path: str) -> sqlite3.Connection:
    """Open brain SQLite mirror, creating parent dirs and applying schema."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    brain_schema.apply_schema(conn)
    return conn


# --- Notion property readers -----------------------------------------


def _concat_text(items: list | None) -> str:
    if not items:
        return ""
    return "".join(item.get("plain_text", "") for item in items)


def _read_prop(page: dict, name: str) -> dict:
    return (page.get("properties") or {}).get(name) or {}


def _prop_title(page: dict, name: str) -> str:
    return _concat_text(_read_prop(page, name).get("title"))


def _prop_rich_text(page: dict, name: str) -> str:
    return _concat_text(_read_prop(page, name).get("rich_text"))


def _prop_multi_select(page: dict, name: str) -> str:
    items = _read_prop(page, name).get("multi_select") or []
    return json.dumps([x.get("name") for x in items if x.get("name")])


def _prop_select(page: dict, name: str) -> str | None:
    sel = _read_prop(page, name).get("select")
    if not sel:
        return None
    val = sel.get("name")
    return val if isinstance(val, str) else None


def _prop_date(page: dict, name: str) -> str | None:
    d = _read_prop(page, name).get("date")
    if not d:
        return None
    val = d.get("start")
    return val if isinstance(val, str) else None


def _prop_checkbox(page: dict, name: str, default: int = 0) -> int:
    val = _read_prop(page, name).get("checkbox")
    if val is None:
        return default
    return 1 if val else 0


def _prop_url(page: dict, name: str) -> str | None:
    return _read_prop(page, name).get("url") or None


def _prop_number(page: dict, name: str) -> float | int | None:
    val = _read_prop(page, name).get("number")
    return val


# --- Mappers ---------------------------------------------------------


def map_page_to_row(category: str, page: dict) -> dict:
    """Notion page JSON → row dict suitable for INSERT OR REPLACE."""
    if category not in _TABLE_OF:
        raise ValueError(f"Unknown brain category: {category!r}")
    common = {
        "notion_page_id": page["id"],
        "last_edited_time": page.get("last_edited_time") or "",
        "created_time": page.get("created_time") or "",
    }
    mapper = {
        "decisions": _map_decision,
        "web_cache": _map_web_cache,
        "patterns": _map_pattern,
        "gotchas": _map_gotcha,
    }[category]
    return {**common, **mapper(page)}


def _map_decision(page: dict) -> dict:
    return {
        "name": _prop_title(page, "Name"),
        "context": _prop_rich_text(page, "Context"),
        "decision": _prop_rich_text(page, "Decision"),
        "rationale": _prop_rich_text(page, "Rationale"),
        "tags": _prop_multi_select(page, "Tags"),
        "stack": _prop_multi_select(page, "Stack"),
        "date_value": _prop_date(page, "Date"),
        "source_project_hash": _prop_rich_text(page, "Source Project Hash"),
        "generalizable": _prop_checkbox(page, "Generalizable", default=1),
        "superseded_by": _prop_url(page, "Superseded By"),
    }


def _map_web_cache(page: dict) -> dict:
    ttl = _prop_number(page, "TTL Days")
    return {
        "name": _prop_title(page, "Name"),
        "url": _prop_url(page, "URL"),
        "query": _prop_rich_text(page, "Query"),
        "content": _prop_rich_text(page, "Content"),
        "fetched_at": _prop_date(page, "Fetched At") or "",
        "ttl_days": int(ttl) if ttl is not None else 30,
        "domain": _prop_select(page, "Domain"),
        "tags": _prop_multi_select(page, "Tags"),
        "source_project_hash": _prop_rich_text(page, "Source Project Hash"),
        "content_hash": _prop_rich_text(page, "Content Hash"),
    }


def _map_pattern(page: dict) -> dict:
    return {
        "name": _prop_title(page, "Name"),
        "description": _prop_rich_text(page, "Description"),
        "when_to_use": _prop_rich_text(page, "When to Use"),
        "example": _prop_rich_text(page, "Example"),
        "tags": _prop_multi_select(page, "Tags"),
        "stack": _prop_multi_select(page, "Stack"),
        "source_project_hash": _prop_rich_text(page, "Source Project Hash"),
        "date_value": _prop_date(page, "Date"),
        "confidence": _prop_select(page, "Confidence"),
    }


def _map_gotcha(page: dict) -> dict:
    return {
        "name": _prop_title(page, "Name"),
        "description": _prop_rich_text(page, "Description"),
        "wrong_way": _prop_rich_text(page, "Wrong Way"),
        "right_way": _prop_rich_text(page, "Right Way"),
        "tags": _prop_multi_select(page, "Tags"),
        "stack": _prop_multi_select(page, "Stack"),
        "source_project_hash": _prop_rich_text(page, "Source Project Hash"),
        "date_value": _prop_date(page, "Date"),
        "severity": _prop_select(page, "Severity"),
        "evidence_url": _prop_url(page, "Evidence URL"),
    }


# --- Upsert ----------------------------------------------------------


def upsert_page(conn: sqlite3.Connection, category: str, row: dict) -> None:
    """INSERT OR REPLACE row into the brain_<category> table by notion_page_id.

    Raises ValueError if `category` is unknown or `row` contains any column
    outside the whitelist in `_ALLOWED_COLS_OF`. The f-string is only
    interpolated with whitelisted identifiers, so even a buggy or malicious
    mapper cannot steer the SQL text.
    """
    if category not in _TABLE_OF:
        raise ValueError(f"Unknown category: {category!r}")
    allowed = _ALLOWED_COLS_OF[category]
    cols = list(row.keys())
    unknown = [c for c in cols if c not in allowed]
    if unknown:
        raise ValueError(
            f"Rejected unknown column(s) for {category!r}: {sorted(unknown)!r}"
        )
    table = _TABLE_OF[category]
    placeholders = ", ".join("?" for _ in cols)
    col_list = ", ".join(cols)
    sql = f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})"
    conn.execute(sql, [row[c] for c in cols])


# --- Sync ------------------------------------------------------------


def _get_sync_state(conn: sqlite3.Connection, category: str) -> dict | None:
    row = conn.execute(
        "SELECT last_pull_at, last_error, last_error_at FROM sync_state WHERE category=?",
        (category,),
    ).fetchone()
    return dict(row) if row else None


def _update_sync_state(
    conn: sqlite3.Connection,
    category: str,
    *,
    last_pull_at: str | None = None,
    last_error: str | None = None,
) -> None:
    err_ts = _now_iso() if last_error else None
    conn.execute(
        """INSERT INTO sync_state(category, last_pull_at, last_error, last_error_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(category) DO UPDATE SET
             last_pull_at = COALESCE(excluded.last_pull_at, sync_state.last_pull_at),
             last_error = excluded.last_error,
             last_error_at = excluded.last_error_at""",
        (category, last_pull_at, last_error, err_ts),
    )


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _make_filter(last_pull_at: str | None) -> dict | None:
    if not last_pull_at:
        return None
    return {
        "timestamp": "last_edited_time",
        "last_edited_time": {"on_or_after": last_pull_at},
    }


def sync_category(
    client: Any,
    conn: sqlite3.Connection,
    database_id: str,
    category: str,
) -> dict:
    """Pull delta for one category; return {fetched, upserted, last_edited_time}."""
    state = _get_sync_state(conn, category) or {}
    cursor = state.get("last_pull_at")
    notion_filter = _make_filter(cursor)
    sorts = [{"timestamp": "last_edited_time", "direction": "ascending"}]

    fetched = 0
    upserted = 0
    max_edited = cursor
    try:
        for page in client.iter_database_query(
            database_id, filter=notion_filter, sorts=sorts
        ):
            fetched += 1
            row = map_page_to_row(category, page)
            upsert_page(conn, category, row)
            upserted += 1
            edited = row.get("last_edited_time") or ""
            if edited and (max_edited is None or edited > max_edited):
                max_edited = edited
    except Exception as e:  # noqa: BLE001
        conn.commit()
        _update_sync_state(conn, category, last_error=str(e))
        conn.commit()
        raise

    _update_sync_state(conn, category, last_pull_at=max_edited, last_error=None)
    conn.commit()
    return {
        "fetched": fetched,
        "upserted": upserted,
        "last_edited_time": max_edited,
    }


def sync_all(
    client: Any,
    conn: sqlite3.Connection,
    database_ids: dict,
) -> dict:
    """Sync all 4 categories. One category's failure does not abort others."""
    results: dict[str, dict] = {}
    for category in CATEGORIES:
        db_id = (database_ids or {}).get(category)
        if not db_id:
            results[category] = {"error": "database_id missing"}
            continue
        try:
            results[category] = sync_category(client, conn, db_id, category)
        except Exception as e:  # noqa: BLE001
            logger.warning("sync_category(%s) failed: %s", category, e)
            results[category] = {"error": str(e)}
    return results
