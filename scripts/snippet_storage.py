"""CRUD helpers for the dedicated snippets store (v15-snippet-table).

Thin functional layer over the ``snippets`` table + ``fts_snippets`` FTS5 index
created by backend_schema_snippets.SNIPPETS_SQL / migration v37. No service-layer
state: every function takes a live sqlite3.Connection.

Dedup contract: ``add_snippet`` is idempotent on ``code_hash`` — re-adding an
identical snippet returns the existing row id and inserts nothing. The caller
computes the hash (the AST detector normalizes before hashing); this layer only
stores and retrieves.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from tausik_utils import utcnow_iso

_COLUMNS = (
    "id",
    "hash",
    "language",
    "code",
    "source_file",
    "source_lines",
    "taxonomy_kind",
    "fts_rank",
    "created_at",
)


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(zip(_COLUMNS, row))


def add_snippet(
    conn: sqlite3.Connection,
    *,
    code_hash: str,
    language: str,
    code: str,
    source_file: str | None = None,
    source_lines: str | None = None,
    taxonomy_kind: str | None = None,
    fts_rank: float | None = None,
    created_at: str | None = None,
) -> int:
    """Insert a snippet, deduping on ``code_hash``. Returns the row id.

    If a snippet with the same hash already exists, NO new row is inserted and
    the existing id is returned (idempotent ingest). INSERT OR IGNORE + reselect
    keeps this race-tolerant: a concurrent caller losing the UNIQUE(hash) race
    still gets the winner's id rather than an IntegrityError.
    """
    conn.execute(
        "INSERT OR IGNORE INTO snippets("
        "hash, language, code, source_file, source_lines, taxonomy_kind, "
        "fts_rank, created_at) VALUES(?,?,?,?,?,?,?,?)",
        (
            code_hash,
            language,
            code,
            source_file,
            source_lines,
            taxonomy_kind,
            fts_rank,
            created_at or utcnow_iso(),
        ),
    )
    conn.commit()
    # Reselect rather than trust lastrowid: on a dedup hit the INSERT is a no-op
    # and lastrowid is undefined, but the row is guaranteed to exist either way.
    row = get_by_hash(conn, code_hash)
    assert row is not None  # just inserted or pre-existing
    return int(row["id"])


def get_snippet(conn: sqlite3.Connection, snippet_id: int) -> dict[str, Any] | None:
    """Fetch one snippet by id, or None if it does not exist."""
    row = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM snippets WHERE id=?", (snippet_id,)
    ).fetchone()
    return _row_to_dict(row)


def get_by_hash(conn: sqlite3.Connection, code_hash: str) -> dict[str, Any] | None:
    """Fetch one snippet by its content hash, or None."""
    row = conn.execute(
        f"SELECT {', '.join(_COLUMNS)} FROM snippets WHERE hash=?", (code_hash,)
    ).fetchone()
    return _row_to_dict(row)


def _fts_quote(query: str) -> str:
    """Wrap a user query as a single FTS5 phrase so operator chars never raise.

    FTS5 treats unquoted input as a query expression — a stray '"' or a bare
    'AND' would be a syntax error. Doubling internal quotes and wrapping the
    whole thing in quotes makes any input a literal phrase match.
    """
    return '"' + query.replace('"', '""') + '"'


_MAX_LIMIT = 200


def search_snippets(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Full-text search over code/source_file/taxonomy_kind. Best matches first.

    The query is matched as a single literal PHRASE (see ``_fts_quote``), so
    multi-word input matches an adjacent sequence, not independent tokens. An
    empty or whitespace-only query returns []. A query that matches nothing
    returns [] (never raises). ``limit`` is clamped to [1, 200].
    """
    if not query or not query.strip():
        return []
    limit = max(1, min(limit, _MAX_LIMIT))
    rows = conn.execute(
        f"SELECT s.{', s.'.join(_COLUMNS)} FROM fts_snippets f "
        "JOIN snippets s ON s.id = f.rowid "
        "WHERE fts_snippets MATCH ? ORDER BY f.rank LIMIT ?",
        (_fts_quote(query), limit),
    ).fetchall()
    return [d for d in (_row_to_dict(r) for r in rows) if d is not None]


def delete_snippet(conn: sqlite3.Connection, snippet_id: int) -> bool:
    """Delete a snippet by id. Returns True if a row was removed, else False."""
    cur = conn.execute("DELETE FROM snippets WHERE id=?", (snippet_id,))
    conn.commit()
    return cur.rowcount > 0


def count_snippets(conn: sqlite3.Connection) -> int:
    """Total number of stored snippets."""
    return int(conn.execute("SELECT COUNT(*) FROM snippets").fetchone()[0])
