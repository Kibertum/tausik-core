"""Brain pull-sync: Notion → local SQLite mirror.

Pulls delta pages from each Notion database into the matching
brain_* SQLite table, using `last_edited_time` as the high-water mark.

The sync is idempotent: INSERT OR REPLACE by notion_page_id.
Failures in one category do not stop the others.

Design reference: references/brain-db-schema.md §5.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

import brain_notion_props
import brain_schema
from brain_hook_utils import parse_iso_to_epoch

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
    """Open brain SQLite mirror, creating parent dirs and applying schema.

    Enables WAL journal mode so a concurrent sync and MCP read on the
    same mirror don't deadlock each other on SQLITE_BUSY. WAL is a
    best-effort request — sqlite silently returns the prior mode for
    `:memory:` / read-only / network-share paths where WAL is unsupported,
    and we accept that without raising.
    """
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL").fetchone()
    except sqlite3.Error:
        # Filesystem or connection setup refuses WAL — continue with the
        # default rollback journal. Reads/writes still work, they just
        # serialize more aggressively.
        pass
    brain_schema.apply_schema(conn)
    return conn


# --- Notion page → row dispatcher -----------------------------------
#
# Property readers + per-category mappers live in brain_notion_props.py
# to keep this module under the 400-line filesize gate.


def map_page_to_row(category: str, page: dict) -> dict:
    """Notion page JSON → row dict suitable for INSERT OR REPLACE."""
    if category not in _TABLE_OF:
        raise ValueError(f"Unknown brain category: {category!r}")
    common = {
        "notion_page_id": page["id"],
        "last_edited_time": page.get("last_edited_time") or "",
        "created_time": page.get("created_time") or "",
    }
    mapper = brain_notion_props.MAPPERS_BY_CATEGORY[category]
    return {**common, **mapper(page)}


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
    """Build a Notion filter that excludes the boundary page.

    `after` is strict `>` in Notion's API — the page that set the cursor
    last sync is not re-fetched. Two pages edited at the exact same ms
    could in theory slip past, but Notion's `last_edited_time` changes on
    any edit, so the only way a missed page stays missed is if no one
    touches it again — which means its content is already in the mirror.
    """
    if not last_pull_at:
        return None
    return {
        "timestamp": "last_edited_time",
        "last_edited_time": {"after": last_pull_at},
    }


def _iso_epoch(s: str) -> float:
    """Parse a Notion ISO timestamp to UTC epoch seconds.

    Used to pick the maximum edited time across a batch without hitting
    the lexicographic pitfall: `"...10:00:00Z"` > `"...10:00:00.000Z"`
    under ASCII comparison but they're the SAME moment. Unparseable
    values sort last (treated as oldest).
    """
    if not s:
        return float("-inf")
    e = parse_iso_to_epoch(s)
    return e if e is not None else float("-inf")


def sync_category(
    client: Any,
    conn: sqlite3.Connection,
    database_id: str,
    category: str,
) -> dict:
    """Pull delta for one category; return {fetched, upserted, last_edited_time}.

    Atomicity: every upsert in the batch plus the `sync_state` cursor
    bump live in a single transaction that commits on success. On
    failure mid-batch we rollback the partial upserts and then, in a
    separate (best-effort) tx, record the error into `sync_state` so the
    next `tausik brain status` surfaces it.
    """
    state = _get_sync_state(conn, category) or {}
    cursor = state.get("last_pull_at")
    notion_filter = _make_filter(cursor)
    sorts = [{"timestamp": "last_edited_time", "direction": "ascending"}]

    fetched = 0
    upserted = 0
    max_edited = cursor
    max_edited_epoch = _iso_epoch(cursor or "")
    # sqlite3's default isolation_level="" auto-BEGINs on the first DML,
    # which is the `upsert_page` INSERT OR REPLACE inside the loop below.
    # The `conn.rollback()` in the except branch relies on that implicit
    # transaction being open — if a future refactor moves a DML earlier
    # (e.g. into _get_sync_state), re-check the rollback boundary.
    try:
        for page in client.iter_database_query(
            database_id, filter=notion_filter, sorts=sorts
        ):
            fetched += 1
            row = map_page_to_row(category, page)
            upsert_page(conn, category, row)
            upserted += 1
            edited = row.get("last_edited_time") or ""
            if edited:
                edited_epoch = _iso_epoch(edited)
                if edited_epoch > max_edited_epoch:
                    max_edited = edited
                    max_edited_epoch = edited_epoch
        _update_sync_state(conn, category, last_pull_at=max_edited, last_error=None)
        conn.commit()
    except Exception as e:  # noqa: BLE001
        conn.rollback()
        try:
            _update_sync_state(conn, category, last_error=str(e))
            conn.commit()
        except sqlite3.Error:
            # Error-state write is best-effort — if the DB itself is now
            # broken we've already failed, no point raising a second time.
            pass
        raise
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
