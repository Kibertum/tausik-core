"""Tests for the v34 event hash-chain backfill (maybe_backfill_v34).

CRITICAL coverage gap (flagged by review): maybe_backfill_v34 is a one-shot,
irreversible migration that SHA-256-seals every historical event row and sets
the meta flag 'v34_backfilled'. A silent regression corrupts the audit chain
on upgrade. See scripts/backend_migrations_v34.py and scripts/events_chain.py.

Each test builds a minimal in-memory schema (events + meta) rather than the
full DB so the chain logic is exercised in isolation.
"""

from __future__ import annotations

import sqlite3

import events_chain
from backend_migrations_v34 import maybe_backfill_v34

# Content fields that define a sealable event, mirroring events_chain._CONTENT_FIELDS.
_CONTENT = ("entity_type", "entity_id", "action", "details", "actor", "created_at")


def _conn(*, with_chain_cols: bool = True) -> sqlite3.Connection:
    """In-memory DB with a meta table and an events table.

    `with_chain_cols=False` omits entry_hash/prev_hash to simulate a DB where
    migration v34 has not yet added the columns.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    chain = ", entry_hash TEXT, prev_hash TEXT" if with_chain_cols else ""
    # ddl-parity: historical — предмет теста в том, что колонок цепочки ещё
    # нет либо они пусты; канонный events сделал бы бэкфилл нечем проверять.
    conn.execute(
        "CREATE TABLE events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "entity_type TEXT, entity_id TEXT, action TEXT, actor TEXT, "
        "details TEXT, created_at TEXT" + chain + ")"
    )
    return conn


def _add_event(
    conn: sqlite3.Connection,
    *,
    action: str,
    details: str | None = None,
    entity_id: str = "t1",
    created_at: str = "2026-01-01T00:00:00Z",
    entry_hash: str | None = None,
    prev_hash: str | None = None,
    with_chain_cols: bool = True,
) -> None:
    if with_chain_cols:
        conn.execute(
            "INSERT INTO events (entity_type, entity_id, action, actor, details, "
            "created_at, entry_hash, prev_hash) VALUES (?,?,?,?,?,?,?,?)",
            ("task", entity_id, action, "agent", details, created_at, entry_hash, prev_hash),
        )
    else:
        conn.execute(
            "INSERT INTO events (entity_type, entity_id, action, actor, details, "
            "created_at) VALUES (?,?,?,?,?,?)",
            ("task", entity_id, action, "agent", details, created_at),
        )
    # Commit so no implicit transaction is left open: in production the events
    # were inserted+committed in prior sessions before the v34 migration runs,
    # and maybe_backfill_v34 issues its own BEGIN IMMEDIATE on a clean conn.
    conn.commit()


def _content_dicts(conn: sqlite3.Connection) -> list[dict]:
    """Event content (id-ascending) as dicts suitable for events_chain helpers."""
    rows = conn.execute(
        "SELECT id, entity_type, entity_id, action, actor, details, created_at, "
        "prev_hash, entry_hash FROM events ORDER BY id ASC"
    ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r[0],
                "entity_type": r[1],
                "entity_id": r[2],
                "action": r[3],
                "actor": r[4],
                "details": r[5],
                "created_at": r[6],
                "prev_hash": r[7],
                "entry_hash": r[8],
            }
        )
    return out


def _stored_links(conn: sqlite3.Connection) -> list[tuple]:
    return [
        (r[0], r[1])
        for r in conn.execute("SELECT prev_hash, entry_hash FROM events ORDER BY id ASC").fetchall()
    ]


def _meta_flag(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key='v34_backfilled'").fetchone()
    return row[0] if row else None


# --- AC-1: correctness — chain from GENESIS_V1, right count --------------------


def test_seals_unsealed_chain_from_genesis():
    conn = _conn()
    _add_event(conn, action="created")
    _add_event(conn, action="status_changed", details="planning->active")
    _add_event(conn, action="log_added", details="note")

    sealed = maybe_backfill_v34(conn)

    assert sealed == 3
    # Stored links match the pure recomputation anchored at GENESIS_V1.
    expected = events_chain.compute_links(_content_dicts(conn))
    assert _stored_links(conn) == expected
    # First row's prev_hash is the genesis constant, not NULL.
    assert _stored_links(conn)[0][0] == events_chain.GENESIS_V1
    # Domain check: the sealed chain verifies clean end-to-end.
    assert events_chain.verify_chain(_content_dicts(conn))["status"] == "ok"


# --- AC-2: idempotency — second run is a no-op, flag set ----------------------


def test_second_run_is_noop_and_sets_flag():
    conn = _conn()
    _add_event(conn, action="created")
    _add_event(conn, action="log_added", details="x")

    first = maybe_backfill_v34(conn)
    assert first == 2
    assert _meta_flag(conn) == "1"
    links_after_first = _stored_links(conn)

    second = maybe_backfill_v34(conn)
    assert second == 0
    # Hashes are untouched by the second pass.
    assert _stored_links(conn) == links_after_first


# --- AC-3: no-op when flag already present ------------------------------------


def test_noop_when_flag_preset_leaves_events_unsealed():
    conn = _conn()
    conn.execute("INSERT INTO meta(key, value) VALUES('v34_backfilled', '1')")
    _add_event(conn, action="created")

    sealed = maybe_backfill_v34(conn)

    assert sealed == 0
    # The preset flag short-circuits before any sealing — rows stay unsealed.
    assert _stored_links(conn) == [(None, None)]


# --- AC-4: negative/boundary — events table lacks chain columns ---------------


def test_noop_without_chain_columns_does_not_raise():
    conn = _conn(with_chain_cols=False)
    _add_event(conn, action="created", with_chain_cols=False)

    sealed = maybe_backfill_v34(conn)

    assert sealed == 0
    # Migration not applied → flag must NOT be set (so a later real backfill runs).
    assert _meta_flag(conn) is None


# --- AC-5: mixed — pre-sealed first row anchors the unsealed tail -------------


def test_mixed_uses_stored_hash_as_prev_for_unsealed_tail():
    conn = _conn()
    # First row already sealed with an arbitrary (non-genesis) stored hash.
    anchor = "deadbeef" * 8  # 64 hex chars, stands in for a real entry_hash
    _add_event(conn, action="created", entry_hash=anchor, prev_hash=events_chain.GENESIS_V1)
    _add_event(conn, action="log_added", details="second")
    _add_event(conn, action="log_added", details="third")

    sealed = maybe_backfill_v34(conn)

    assert sealed == 2  # only the two unsealed rows
    stored = _stored_links(conn)
    # Pre-sealed row is left exactly as it was.
    assert stored[0] == (events_chain.GENESIS_V1, anchor)
    # The first unsealed row chains off the STORED hash, not GENESIS.
    content = _content_dicts(conn)
    expected_second = events_chain.entry_hash(anchor, content[1])
    assert stored[1] == (anchor, expected_second)
    # Third chains off the second.
    expected_third = events_chain.entry_hash(expected_second, content[2])
    assert stored[2] == (expected_second, expected_third)


# --- AC-6: empty events table — no-op count, flag still set -------------------


def test_empty_events_table_sets_flag_returns_zero():
    conn = _conn()

    sealed = maybe_backfill_v34(conn)

    assert sealed == 0
    # An empty (but migrated) DB is considered backfilled — flag set to avoid
    # re-scanning on every subsequent open.
    assert _meta_flag(conn) == "1"


# --- Rollback path: mid-loop error seals nothing, reports 0 -------------------


def test_midloop_error_rolls_back_and_returns_zero(monkeypatch):
    conn = _conn()
    _add_event(conn, action="created")
    _add_event(conn, action="log_added", details="second")

    # Fail on the SECOND event so the first row's UPDATE is already in the open
    # transaction and must be rolled back.
    real_entry_hash = events_chain.entry_hash
    calls = {"n": 0}

    def flaky_entry_hash(prev, event):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise sqlite3.OperationalError("injected mid-backfill failure")
        return real_entry_hash(prev, event)

    monkeypatch.setattr(events_chain, "entry_hash", flaky_entry_hash)

    sealed = maybe_backfill_v34(conn)

    # Reports 0 — NOT the 1 row it processed before the failure.
    assert sealed == 0
    # Flag unset so a later run retries the whole backfill.
    assert _meta_flag(conn) is None
    # Rollback undid the first row's partial seal — both rows stay unsealed.
    assert _stored_links(conn) == [(None, None), (None, None)]
