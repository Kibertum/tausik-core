"""v34 post-migration backfill — seal the historical event hash-chain.

Separated from backend_migrations.py to keep that file under 400 lines.
The chain cannot be computed in pure SQL (no sha256 / JSON canonicalization
in stock SQLite), so backfill runs in Python over the migrated rows, in
ascending id order, anchored at events_chain.GENESIS_V1. Idempotent via the
meta flag 'v34_backfilled'.
"""

from __future__ import annotations

import logging
import sqlite3

import events_chain

logger = logging.getLogger("tausik.migrations")


def maybe_backfill_v34(conn: sqlite3.Connection) -> int:
    """Seal every unsealed event into the chain. Returns rows sealed.

    No-op (returns 0) when the meta flag is already set or the events table
    lacks the v34 columns (migration not yet applied). Best-effort: logs and
    swallows errors so a backfill hiccup never blocks DB open.
    """
    try:
        already = conn.execute("SELECT value FROM meta WHERE key='v34_backfilled'").fetchone()
    except sqlite3.Error:
        already = None
    if already:
        return 0
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
    except sqlite3.Error:
        return 0
    if "entry_hash" not in cols or "prev_hash" not in cols:
        return 0

    # Read positionally — do NOT mutate conn.row_factory (the caller shares
    # this connection and may rely on tuple rows).
    sealed = 0
    try:
        # BEGIN before the SELECT so the read+write share one snapshot: an
        # event inserted concurrently mid-backfill cannot be skipped yet have
        # the v34_backfilled flag committed over it.
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            "SELECT id, entity_type, entity_id, action, actor, details, "
            "created_at, entry_hash FROM events ORDER BY id ASC"
        ).fetchall()
        prev = events_chain.GENESIS_V1
        for row in rows:
            row_id, stored_entry_hash = row[0], row[7]
            if stored_entry_hash is None:
                event = {
                    "entity_type": row[1],
                    "entity_id": row[2],
                    "action": row[3],
                    "actor": row[4],
                    "details": row[5],
                    "created_at": row[6],
                }
                eh = events_chain.entry_hash(prev, event)
                conn.execute(
                    "UPDATE events SET prev_hash=?, entry_hash=? WHERE id=?",
                    (prev, eh, row_id),
                )
                prev = eh
                sealed += 1
            else:
                prev = stored_entry_hash
        conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('v34_backfilled', '1')")
        conn.commit()
    except sqlite3.Error as e:
        logger.warning("v34 event-chain backfill failed: %s", e)
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        # Rollback undid every UPDATE in this transaction and the flag was not
        # committed — report 0 sealed, not the partial in-loop counter, so the
        # caller never believes rows were sealed when none were committed.
        return 0
    return sealed
