"""TAUSIK BackendEventsChainMixin — hash-chain sealing/verify/anchor DB ops.

v16r-audit-hashchain. Separated from backend_crud to keep files under 400
lines. Relies on the composed backend's ``_q`` / ``_ex`` / ``_ins``.

Sealing is lazy and monotonic: events are inserted normally (by Python
event_add OR by SQL audit triggers) with NULL chain hashes, then sealed in
a single id-ordered pass on demand (verify / anchor). Sealed rows are
append-only evidence — never rewritten — so the running prev for new rows
trusts the stored entry_hash; independent recomputation in
events_chain.verify_chain is what catches tampering of sealed rows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import events_chain
from tausik_utils import utcnow_iso

# Event columns that feed canonical_event_bytes plus the chain/id columns.
_EVENT_COLS = (
    "id, entity_type, entity_id, action, actor, details, created_at, prev_hash, entry_hash"
)


class BackendEventsChainMixin:
    """Hash-chain sealing, verification and ed25519 anchoring. Mixed into SQLiteBackend."""

    if TYPE_CHECKING:

        def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
        def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...
        def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def begin_tx(self) -> None: ...
        def commit_tx(self) -> None: ...
        def rollback_tx(self) -> None: ...

    # --- chain reads ---

    def events_all_ordered(self) -> list[dict[str, Any]]:
        """Every event, ascending id — the canonical chain order for verify."""
        return self._q(f"SELECT {_EVENT_COLS} FROM events ORDER BY id ASC")

    # --- sealing ---

    def events_seal(self) -> dict[str, Any]:
        """Seal the unsealed tail (id > last sealed id) atomically. Idempotent.

        Returns {sealed, head_id, head_hash, total}. Truly O(unsealed): reads
        only the last sealed row + the pending tail. All UPDATEs run inside one
        BEGIN IMMEDIATE so a crash mid-seal leaves the chain unchanged, and
        concurrent seals serialize. Using `id > last_sealed_id` also acts as a
        watermark: a NULL row injected BEFORE the sealed frontier is never
        sealed (laundered) — verify_chain reports it as broken instead.
        """
        last = self._q1(
            "SELECT id, entry_hash FROM events WHERE entry_hash IS NOT NULL "
            "ORDER BY id DESC LIMIT 1"
        )
        prev = last["entry_hash"] if last else events_chain.GENESIS_V1
        last_id = last["id"] if last else 0
        pending = self._q(
            f"SELECT {_EVENT_COLS} FROM events WHERE entry_hash IS NULL AND id > ? ORDER BY id ASC",
            (last_id,),
        )
        head_id: int | None = last["id"] if last else None
        head_hash: str | None = prev if last else None
        sealed = 0
        if pending:
            self.begin_tx()
            try:
                for r in pending:
                    eh = events_chain.entry_hash(prev, r)
                    self._ex(
                        "UPDATE events SET prev_hash=?, entry_hash=? WHERE id=?",
                        (prev, eh, r["id"]),
                    )
                    prev = eh
                    sealed += 1
                    head_id = r["id"]
                self.commit_tx()
            except Exception:
                self.rollback_tx()
                raise
            head_hash = prev
        count_row = self._q1("SELECT COUNT(*) AS c FROM events")
        total = count_row["c"] if count_row else 0
        return {
            "sealed": sealed,
            "head_id": head_id,
            "head_hash": head_hash,
            "total": total,
        }

    # --- verification ---

    def events_verify(self, *, seal: bool = True) -> dict[str, Any]:
        """Seal pending rows (unless seal=False) then recompute & compare.

        Returns events_chain.verify_chain's verdict augmented with the
        number of rows sealed in this pass.
        """
        sealed = 0
        if seal:
            sealed = self.events_seal()["sealed"]
        verdict = events_chain.verify_chain(self.events_all_ordered())
        verdict["sealed_now"] = sealed
        return verdict

    # --- ed25519 anchor ---

    def events_anchor_insert(
        self, *, head_id: int, head_hash: str, event_count: int, envelope_json: str
    ) -> int:
        return self._ins(
            "INSERT INTO events_anchor(head_id, head_hash, event_count, "
            "envelope_json, created_at) VALUES(?,?,?,?,?)",
            (head_id, head_hash, event_count, envelope_json, utcnow_iso()),
        )

    def events_anchor_latest(self) -> dict[str, Any] | None:
        return self._q1(
            "SELECT id, head_id, head_hash, event_count, envelope_json, "
            "created_at FROM events_anchor ORDER BY id DESC LIMIT 1"
        )
