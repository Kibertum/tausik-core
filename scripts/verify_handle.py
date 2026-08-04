"""Explicit state handle for a verify run — minting and fail-closed redemption.

v2-verify-receipt-as-argument, following decision #218 and SEP-2567
("Sessionless MCP via Explicit State Handles", Final): a server that needs
state across tool calls returns an identifier from one tool and accepts it as
a parameter on the next, instead of hiding the link in a session or in a
time-window search.

WHAT THIS REPLACES. `task done` used to prove verify-first by SEARCHING
`verification_runs` for a row that was green, matched the files_hash, matched
the gate signature and was younger than 600 s. Three properties of that search
were defects rather than features:
  - the agent learned about a substantive refusal ("you declared a subset of
    what git says changed") as a CACHE MISS, because miss was the only word the
    lookup had;
  - freshness was a clock window owned by the server, invisible to the model
    (SEP-2567: "A policy only in server documentation is not visible to the
    model");
  - two processes with different in-memory module state computed "fresh"
    differently.
Here `verify` mints a handle, prints it, and `task done --verify-handle` looks
up EXACTLY that row. The refusals below each say what is wrong.

WHAT THIS IS NOT. The handle is not an authorization token and the receipt is
not a bearer document. The project signing key lives inside the working tree
(docs/ru/receipts.md), so an agent can mint any signature it likes; nothing
here pretends otherwise. The handle's job is to make the link between "I
verified" and "I am closing" EXPLICIT and checkable, and to make replay
countable — not to keep a determined agent out. That is why every property the
old search checked is RE-CHECKED here against live state (files re-hashed off
disk, gate signature recomputed from the live config) rather than trusted from
the presented document: SEP-2322 requires exactly this of any state the client
carries ("servers MUST always validate that state, as the client is an
untrusted intermediary").

WHY THE NONCE IS NOT IN THE RECEIPT. The receipt is exportable
(`tausik receipt show`, receipt_export.py) and is meant to be shown. The nonce
is the half of the handle that is not derivable from the run id, so putting it
in the receipt would publish it with every export. It lives in its own column.
"""

from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from verify_constants import DEFAULT_HANDLE_TTL_S

# `<run_id>.<nonce>` — a dot, because run ids are decimal and the nonce is hex,
# so no separator can occur inside either half.
HANDLE_SEP = "."

# SEP-2567: "at least 128 bits of cryptographically secure entropy".
NONCE_BYTES = 16
NONCE_HEX_LEN = NONCE_BYTES * 2


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> int:
    """Execute one statement and commit ONLY if we opened the transaction.

    THIS IS NOT A MICRO-OPTIMISATION. The MCP server hands every tool call to
    its own thread over ONE shared `sqlite3.Connection`
    (`project_backend.SQLiteBackend`, opened `check_same_thread=False`) with no
    mutex in the dispatch path. `SQLiteBackend.begin_tx` opens a BEGIN
    IMMEDIATE, and `_ex`/`_ins` commit only when no such transaction is open —
    for good reason. A bare `conn.commit()` here would commit whatever is
    pending on the connection, including a half-written `task_done` from a
    CONCURRENT call that has already set status='done' but has not yet finished
    its cascade. If that call then raised, its `rollback_tx` would undo only
    what was written after our commit, leaving a task marked done with none of
    the writes that justify it.

    `conn.in_transaction` sampled BEFORE the statement is what distinguishes
    the two cases: True means somebody else's transaction is already open, so
    our write joins it and lands with THEIR commit — which is the correct
    semantics, since our write is part of the close they are performing. The
    backend's own `_in_tx` flag is not consulted because this module is handed
    a bare connection by the CLI, the hooks and the tests alike, and only one
    of those routes has a backend to ask.

    Returns `cur.rowcount` — the caller's answer for `redeem`.
    """
    caller_owns_tx = bool(conn.in_transaction)
    cur = conn.execute(sql, params)
    if not caller_owns_tx:
        conn.commit()
    return int(cur.rowcount or 0)


def parse_iso(value: str | None) -> datetime | None:
    """ISO-8601 (with trailing Z) -> aware datetime; None when unparseable.

    Callers treat None as "cannot establish this timestamp", which every one of
    them turns into a REFUSAL — never into "no expiry".
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def compute_expires_at(ran_at: str, ttl_s: int = DEFAULT_HANDLE_TTL_S) -> str:
    """The expiry stamped into the receipt, derived from the run's own ran_at.

    Anchored to `ran_at` rather than to "now" so the signed expiry and the row
    it describes cannot disagree — receipt emission happens a few milliseconds
    after the insert, and an expiry that drifted from its run would make the
    two documents tell slightly different stories about the same event.
    """
    base = parse_iso(ran_at) or _utcnow()
    return _iso(base + timedelta(seconds=max(0, int(ttl_s))))


def mint_handle(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    expires_at: str,
) -> str:
    """Attach a fresh nonce to `run_id` and return `<run_id>.<nonce>`.

    Overwrites any previous nonce on the row and clears `handle_redeemed_at`,
    so a re-minted handle is spendable — the redeem-once rule binds a NONCE,
    not a row id, and a stale redemption stamp would make the new handle
    unusable for a reason no message could explain.

    NO PRODUCTION CALLER RE-MINTS TODAY, and saying so is more useful than
    implying otherwise: every `tausik verify` INSERTs a new row and mints
    against `lastrowid`, so the overwrite branch is reached only by tests. It
    is written this way as a property of the function rather than an
    assumption about its callers — a future caller that does re-mint gets
    correct behaviour instead of a silently unusable handle.
    """
    nonce = secrets.token_hex(NONCE_BYTES)
    _write(
        conn,
        "UPDATE verification_runs SET handle_nonce = ?, handle_expires_at = ?, "
        "handle_redeemed_at = NULL WHERE id = ?",
        (nonce, expires_at, int(run_id)),
    )
    return f"{int(run_id)}{HANDLE_SEP}{nonce}"


def parse_handle(handle: str | None) -> tuple[int, str] | None:
    """`<run_id>.<nonce>` -> (run_id, nonce); None when the shape is wrong.

    Shape is checked before any database access so a malformed handle cannot
    become a query, and so the nonce length requirement is enforced on the way
    in rather than being assumed of whatever is stored.
    """
    if not handle or not isinstance(handle, str):
        return None
    raw = handle.strip()
    if raw.count(HANDLE_SEP) != 1:
        return None
    left, nonce = raw.split(HANDLE_SEP, 1)
    if not left.isdigit():
        return None
    # Case carries no information in hex, but the stored value is always what
    # `secrets.token_hex` produced — lowercase — and the comparison is
    # byte-for-byte. Without this, a nonce that travelled through anything that
    # uppercases hex would be refused as "does not match" while being correct.
    nonce = nonce.lower()
    if len(nonce) != NONCE_HEX_LEN:
        return None
    try:
        int(nonce, 16)
    except ValueError:
        return None
    return int(left), nonce


class HandleVerdict:
    """Outcome of presenting a handle. `ok` False always carries a `reason`.

    A tiny class rather than a tuple because the caller needs three things
    (verdict, human-readable reason, the row it validated) and a 3-tuple at
    five call sites is how the third element ends up silently dropped.
    """

    __slots__ = ("ok", "reason", "run", "files")

    def __init__(
        self,
        ok: bool,
        reason: str,
        run: dict[str, Any] | None = None,
        files: list[str] | None = None,
    ) -> None:
        self.ok = ok
        self.reason = reason
        self.run = run
        self.files = files or []

    def __repr__(self) -> str:  # pragma: no cover — diagnostics only
        return f"HandleVerdict(ok={self.ok!r}, reason={self.reason!r})"


def _row_to_dict(row: Any, columns: tuple[str, ...]) -> dict[str, Any]:
    """sqlite3.Row or tuple -> dict, without depending on `conn.row_factory`.

    Connections reach this module from the CLI, the MCP handlers, the hooks and
    the tests, and they do not agree on a row factory. Indexing by position is
    the one access both shapes support.
    """
    return {name: row[i] for i, name in enumerate(columns)}


_RUN_COLUMNS = (
    "id",
    "task_slug",
    "scope",
    "command",
    "exit_code",
    "summary",
    "files_hash",
    "ran_at",
    "duration_ms",
    "receipt_json",
    "handle_nonce",
    "handle_expires_at",
    "handle_redeemed_at",
)


def load_run_for_handle(conn: sqlite3.Connection, run_id: int) -> dict[str, Any] | None:
    """The verification_runs row a handle points at, or None."""
    row = conn.execute(
        f"SELECT {', '.join(_RUN_COLUMNS)} FROM verification_runs WHERE id = ?",
        (int(run_id),),
    ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row, _RUN_COLUMNS)


def redeem(conn: sqlite3.Connection, run_id: int, nonce: str) -> bool:
    """Spend the handle. True iff THIS call was the one that spent it.

    Atomic by construction: the `handle_redeemed_at IS NULL` predicate lives in
    the UPDATE, so two concurrent `task done` calls presenting the same handle
    cannot both see an unspent row and both proceed. `rowcount` is the answer —
    a read-then-write would reintroduce exactly the race the predicate closes.
    The nonce is part of the WHERE so a redemption cannot be aimed at a row by
    id alone.
    """
    return (
        _write(
            conn,
            "UPDATE verification_runs SET handle_redeemed_at = ? "
            "WHERE id = ? AND handle_nonce = ? AND handle_redeemed_at IS NULL",
            (_iso(_utcnow()), int(run_id), nonce),
        )
        == 1
    )
