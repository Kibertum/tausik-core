"""v42 post-migration backfill — stable slugs for existing decisions and memory
(state-git-stable-ids).

Separated from backend_migrations.py to keep that file under 400 lines, and from
the SQL migration because the slug is a Python transliteration a stock SQLite
cannot produce. Runs over the migrated rows in ascending id order — the order is
load-bearing: it is what makes dedup suffixes (`-2`, `-3`) resolve to the same
slug on every machine for the same historical data. Idempotent via the meta flag
``v42_slugs_backfilled``; the UNIQUE index is created only AFTER every row has a
slug (creating it earlier would fail on the all-NULL column).
"""

from __future__ import annotations

import logging
import sqlite3

from slug_util import first_line, make_slug

logger = logging.getLogger("tausik.migrations")


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    try:
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.Error:
        return False
    return column in cols


def maybe_backfill_v42(conn: sqlite3.Connection) -> int:
    """Give every slug-less decision and memory row a stable slug. Returns rows filled.

    No-op (returns 0) when the meta flag is already set or the slug columns are
    absent (migration not yet applied). Best-effort: logs and swallows errors so
    a backfill hiccup never blocks DB open — the slug is not load-bearing for DB
    operation until export/import is wired (a later task).
    """
    try:
        already = conn.execute("SELECT value FROM meta WHERE key='v42_slugs_backfilled'").fetchone()
    except sqlite3.Error:
        already = None
    if already:
        return 0
    if not _column_exists(conn, "decisions", "slug") or not _column_exists(conn, "memory", "slug"):
        return 0
    # Guard on the columns the backfill READS, not just the one it writes: a
    # minimal/stub `decisions`/`memory` (migration-fixture tests that only need
    # the ALTER target to exist) lacks them, and a SELECT over a missing column
    # would raise mid-transaction. No-op cleanly instead.
    if not _column_exists(conn, "decisions", "decision"):
        return 0
    if not _column_exists(conn, "memory", "title") or not _column_exists(
        conn, "memory", "created_at"
    ):
        return 0

    filled = 0
    try:
        # BEGIN before the reads so the whole backfill shares one snapshot: a row
        # inserted concurrently mid-backfill cannot be skipped yet have the flag
        # committed over it.
        conn.execute("BEGIN IMMEDIATE")

        # `taken` seeds from any slug already present (forward inserts that landed
        # before the flag was set), so the backfill never collides with them.
        taken: set[str] = set()
        for (slug,) in conn.execute(
            "SELECT slug FROM decisions WHERE slug IS NOT NULL AND slug != ''"
        ).fetchall():
            taken.add(slug)

        # Decisions — slug from the decision's first non-empty line. id ASC.
        for row_id, decision in conn.execute(
            "SELECT id, decision FROM decisions WHERE slug IS NULL OR slug = '' ORDER BY id ASC"
        ).fetchall():
            slug = make_slug(
                first_line(decision or ""),
                fallback=f"decision-{row_id}",
                taken=taken,
            )
            taken.add(slug)
            conn.execute("UPDATE decisions SET slug=? WHERE id=?", (slug, row_id))
            filled += 1

        # Memory has its own slug namespace (a separate directory / unique index),
        # so it starts from a fresh `taken`.
        taken = set()
        for (slug,) in conn.execute(
            "SELECT slug FROM memory WHERE slug IS NOT NULL AND slug != ''"
        ).fetchall():
            taken.add(slug)

        # Memory — slug from title. id ASC.
        for row_id, title, created_at in conn.execute(
            "SELECT id, title, created_at FROM memory "
            "WHERE slug IS NULL OR slug = '' ORDER BY id ASC"
        ).fetchall():
            slug = make_slug(
                title or "",
                fallback=f"memory-{row_id}",
                taken=taken,
            )
            taken.add(slug)
            conn.execute("UPDATE memory SET slug=? WHERE id=?", (slug, row_id))
            filled += 1

        # Only now, with every row filled, is a UNIQUE index constructible. IF NOT
        # EXISTS so a fresh DB (which reached here over zero rows) and a re-run are
        # both safe.
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_decisions_slug ON decisions(slug)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_slug ON memory(slug)")
        conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('v42_slugs_backfilled', '1')")
        # A prior failed run may have left an error marker; success clears it so a
        # recovered migration doesn't keep flagging a problem that no longer exists.
        conn.execute("DELETE FROM meta WHERE key='v42_slugs_backfill_error'")
        conn.commit()
    except sqlite3.Error as e:
        # NOT a warning to be lost in the log: a failed identity migration must be
        # LOUD (zero tolerance for silent errors). The success flag was never
        # committed, so this re-runs on every DB open — record a durable, queryable
        # marker so `doctor`/`status` surface it instead of it failing forever unseen.
        logger.error("v42 slug backfill FAILED (re-runs on next open): %s", e)
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        try:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('v42_slugs_backfill_error', ?)",
                (str(e),),
            )
            conn.commit()
        except sqlite3.Error:
            pass  # if we cannot even record the marker, the ERROR log is the floor
        # Rollback undid every UPDATE and the success flag was not committed —
        # report 0, not the in-loop counter, so no caller believes rows were filled.
        return 0
    return filled
