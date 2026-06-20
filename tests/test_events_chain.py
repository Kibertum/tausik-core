"""v16r-audit-hashchain: event hash-chain sealing, tamper detection, anchor."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import crypto_keys  # noqa: E402
import events_chain  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402


@pytest.fixture
def be(tmp_path):
    return SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))


def _add(be, n=3):
    for i in range(n):
        be.event_add("task", f"t{i}", "created", details=f"d{i}")


# --- pure helpers ---------------------------------------------------------


def test_genesis_is_frozen():
    # Frozen contract: a change here invalidates every existing chain. Literal
    # (not recomputed) so the constant can't drift silently with the impl.
    assert (
        events_chain.GENESIS_V1
        == "396ada57109d83c07a9abf2b2f99599d907d2c109c57715dad0e43180f606840"
    )


def test_entry_hash_is_deterministic_and_link_sensitive():
    ev = {"entity_type": "task", "entity_id": "x", "action": "a", "created_at": "T"}
    h1 = events_chain.entry_hash("prevA", ev)
    assert h1 == events_chain.entry_hash("prevA", ev)  # deterministic
    assert h1 != events_chain.entry_hash("prevB", ev)  # depends on prev
    ev2 = dict(ev, action="b")
    assert h1 != events_chain.entry_hash("prevA", ev2)  # depends on content


def test_verify_chain_empty_and_unchained():
    assert events_chain.verify_chain([])["status"] == "empty"
    raw = [
        {
            "id": 1,
            "entity_type": "t",
            "entity_id": "x",
            "action": "a",
            "created_at": "T",
            "prev_hash": None,
            "entry_hash": None,
        }
    ]
    assert events_chain.verify_chain(raw)["status"] == "unchained"


# --- sealing & verify over a real backend ---------------------------------


def test_seal_then_verify_ok(be):
    _add(be, 3)
    res = be.events_seal()
    assert res["sealed"] == 3
    assert res["total"] == 3
    verdict = be.events_verify(seal=False)
    assert verdict["status"] == "ok"
    assert verdict["length"] == 3


def test_seal_is_idempotent_and_monotonic(be):
    _add(be, 2)
    first = be.events_seal()
    assert first["sealed"] == 2
    assert be.events_seal()["sealed"] == 0  # nothing left to seal
    # AC3: O(1) append — a new event seals against the existing head only,
    # linking correctly regardless of chain length.
    _add(be, 1)
    second = be.events_seal()
    assert second["sealed"] == 1
    assert be.events_verify(seal=False)["status"] == "ok"


def test_trigger_inserted_events_are_chained(be):
    # Task lifecycle events come from SQL triggers, not event_add — they must
    # still seal into the chain.
    be.epic_add("e1", "Epic")
    be.story_add("e1", "s1", "Story")
    be.task_add("s1", "task-x", "Title", role="developer")
    verdict = be.events_verify(seal=True)
    assert verdict["status"] == "ok"
    assert verdict["length"] >= 1


# --- tamper detection (NEGATIVE) ------------------------------------------


def test_tampering_sealed_event_is_detected(be):
    _add(be, 4)
    be.events_seal()
    # Mutate the content of event #2 directly, bypassing the chain.
    be._ex("UPDATE events SET details='HACKED' WHERE id=2")
    verdict = be.events_verify(seal=True)  # seal won't touch sealed rows
    assert verdict["status"] == "broken"
    assert verdict["first_break"] == 2
    assert "modified" in verdict["reason"]


def test_seal_does_not_relaunder_wiped_interior_row(be):
    # Watermark: a row behind the sealed frontier whose hashes were wiped is
    # NOT re-sealed (laundered) — verify reports it broken instead.
    _add(be, 3)
    be.events_seal()
    be._ex("UPDATE events SET prev_hash=NULL, entry_hash=NULL WHERE id=2")
    assert be.events_seal()["sealed"] == 0  # id 2 is behind frontier (id 3)
    assert be.events_verify(seal=True)["status"] == "broken"
    assert be.events_verify(seal=False)["first_break"] == 2


def test_deleting_a_sealed_event_breaks_the_link(be):
    _add(be, 4)
    be.events_seal()
    be._ex("DELETE FROM events WHERE id=2")
    verdict = be.events_verify(seal=True)
    assert verdict["status"] == "broken"
    # The break surfaces at the row whose prev_hash no longer matches.
    assert verdict["first_break"] == 3


# --- ed25519 anchor -------------------------------------------------------


def test_anchor_sign_and_verify_roundtrip(be, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    crypto_keys.init_keys(str(tmp_path))
    _add(be, 3)
    res = be.events_seal()
    env = events_chain.sign_head(
        str(tmp_path),
        head_id=res["head_id"],
        head_hash=res["head_hash"],
        event_count=res["total"],
    )
    assert events_chain.verify_anchor(env, project_dir=str(tmp_path)) is True


def test_anchor_detects_rebased_chain(be, tmp_path):
    # Even after an attacker recomputes the whole chain (so the hash-walk
    # passes again), the signed head no longer matches → mismatch.
    crypto_keys.init_keys(str(tmp_path))
    _add(be, 3)
    res = be.events_seal()
    env = events_chain.sign_head(
        str(tmp_path),
        head_id=res["head_id"],
        head_hash=res["head_hash"],
        event_count=res["total"],
    )
    # Tamper + fully re-seal (rebase): wipe hashes, mutate, recompute.
    be._ex("UPDATE events SET prev_hash=NULL, entry_hash=NULL")
    be._ex("UPDATE events SET details='HACKED' WHERE id=1")
    be.events_seal()
    assert be.events_verify(seal=False)["status"] == "ok"  # walk fooled
    new_head = {
        r["id"]: h
        for r, (_p, h) in zip(
            be.events_all_ordered(),
            events_chain.compute_links(be.events_all_ordered()),
        )
    }
    # Signature still valid (we didn't touch the key) but head_hash differs.
    assert events_chain.verify_anchor(env, project_dir=str(tmp_path)) is True
    assert new_head[res["head_id"]] != res["head_hash"]


def test_verify_anchor_rejects_tampered_envelope(be, tmp_path):
    crypto_keys.init_keys(str(tmp_path))
    _add(be, 1)
    res = be.events_seal()
    env = events_chain.sign_head(
        str(tmp_path),
        head_id=res["head_id"],
        head_hash=res["head_hash"],
        event_count=res["total"],
    )
    env["anchor"]["event_count"] = 999  # forge payload
    assert events_chain.verify_anchor(env, project_dir=str(tmp_path)) is False
