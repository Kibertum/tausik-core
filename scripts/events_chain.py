"""Hash-chain immutability for the audit `events` table.

v16r-audit-hashchain: each event row carries the entry_hash of the
previous row (prev_hash) plus its own entry_hash, forming a tamper-evident
chain. Reordering, deleting or mutating any historical event breaks the
linkage and is detected by `verify_chain`.

Design:
  - genesis: a fixed constant (GENESIS_V1) — keyless and deterministic so
    the chain backfills offline during migration v34.
  - entry_hash(i) = sha256(prev_hash(i) || canonical_event_bytes(event_i)),
    chained by ascending row id. id itself is NOT hashed (it is positional);
    the content tuple (entity_type, entity_id, action, details, actor,
    created_at) is.
  - O(1) append: a new event reads only the current head's entry_hash
    (PK DESC LIMIT 1) and links to it.

ed25519 anchor (optional, project-key bound):
  - `sign_head` signs {schema, head_id, head_hash, event_count} with the
    project ed25519 key (v15-crypto-keymgmt). Storing a signed head makes
    pre-anchor tampering detectable even by an attacker who recomputes the
    whole chain — they cannot forge the signature. Keyless projects skip
    anchoring; chain verification still works.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import crypto_ed25519 as ed25519
import crypto_keys
from crypto_receipt import ReceiptError, canonical_bytes

# Fixed genesis: the prev_hash of the very first event. Bumping this string
# would invalidate every existing chain, so it is frozen at v1.
GENESIS_V1 = hashlib.sha256(b"tausik-events-genesis/v1").hexdigest()

ANCHOR_SCHEMA = "tausik-events-anchor/v1"

# The event columns that define an entry's signable content, in canonical
# order. id is excluded (positional); prev_hash/entry_hash are excluded
# (they are derived, not content).
_CONTENT_FIELDS = ("entity_type", "entity_id", "action", "details", "actor", "created_at")


class ChainError(Exception):
    """Hash-chain precondition failure (not a tampering verdict)."""


def canonical_event_bytes(event: dict[str, Any]) -> bytes:
    """Deterministic ASCII bytes of an event's signable content.

    Only `_CONTENT_FIELDS` participate. Missing fields canonicalize as
    null so a row with details=NULL and a row with details='' hash
    differently — both are content-significant.
    """
    payload = {k: event.get(k) for k in _CONTENT_FIELDS}
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def entry_hash(prev_hash: str, event: dict[str, Any]) -> str:
    """The chained hash of one event given its predecessor's entry_hash."""
    h = hashlib.sha256()
    h.update(prev_hash.encode("ascii"))
    h.update(b"\x00")  # domain separator between link and content
    h.update(canonical_event_bytes(event))
    return h.hexdigest()


def compute_links(events: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Compute (prev_hash, entry_hash) for an ordered event list.

    `events` must be sorted by ascending id. Returns one tuple per event.
    Pure — does not touch the DB. Used by both the migration backfill and
    `verify_chain`.
    """
    out: list[tuple[str, str]] = []
    prev = GENESIS_V1
    for ev in events:
        eh = entry_hash(prev, ev)
        out.append((prev, eh))
        prev = eh
    return out


def verify_chain(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute the chain and compare against stored hashes.

    `events` must be ordered by ascending id and each dict must carry the
    stored `prev_hash`/`entry_hash` (NULL allowed only for an all-unchained
    legacy DB, which reports status='unchained').

    Returns:
      {status: 'ok'|'broken'|'unchained'|'empty', length: int,
       first_break: int|None, reason: str|None}
    first_break is the row id of the earliest mismatch.
    """
    if not events:
        return {"status": "empty", "length": 0, "first_break": None, "reason": None}

    stored = [(e.get("prev_hash"), e.get("entry_hash")) for e in events]
    if all(p is None and h is None for p, h in stored):
        return {
            "status": "unchained",
            "length": len(events),
            "first_break": None,
            "reason": "no events carry chain hashes (pre-v34 / unbackfilled DB)",
        }

    expected = compute_links(events)
    for ev, (exp_prev, exp_hash), (got_prev, got_hash) in zip(events, expected, stored):
        if got_prev != exp_prev or got_hash != exp_hash:
            return {
                "status": "broken",
                "length": len(events),
                "first_break": ev.get("id"),
                "reason": (
                    "entry_hash mismatch — content was modified"
                    if got_prev == exp_prev
                    else "prev_hash mismatch — a row was inserted, deleted or reordered"
                ),
            }
    return {"status": "ok", "length": len(events), "first_break": None, "reason": None}


# --- ed25519 anchor -------------------------------------------------------


def _anchor_payload(head_id: int, head_hash: str, event_count: int) -> dict[str, Any]:
    return {
        "schema": ANCHOR_SCHEMA,
        "head_id": head_id,
        "head_hash": head_hash,
        "event_count": event_count,
    }


def sign_head(
    project_dir: str, *, head_id: int, head_hash: str, event_count: int
) -> dict[str, Any]:
    """Sign the current chain head with the project ed25519 key.

    Raises crypto_keys.KeyError_ when the project has no key (caller decides
    whether that is a hard error or a skip). Returns a signed envelope dict
    suitable for JSON storage in events_anchor.envelope_json.
    """
    seed = crypto_keys.load_seed(project_dir)
    payload = _anchor_payload(head_id, head_hash, event_count)
    try:
        body = canonical_bytes(payload)
    except ReceiptError as e:  # pragma: no cover - payload is always canonical
        raise ChainError(f"anchor payload not canonicalizable: {e}") from e
    public = ed25519.public_from_seed(seed)
    signature = ed25519.sign(seed, body)
    return {
        "envelope": ANCHOR_SCHEMA,
        "anchor": payload,
        "signature": {
            "algorithm": "ed25519",
            "key_fingerprint": crypto_keys.fingerprint(public),
            "value": signature.hex(),
        },
    }


def verify_anchor(
    envelope: dict[str, Any],
    *,
    public: bytes | None = None,
    project_dir: str | None = None,
) -> bool:
    """True iff the anchor envelope's signature matches its payload.

    Never raises on attacker-controlled input — returns False on any
    structural defect. Key resolution: explicit `public` > project keystore.
    """
    if public is None:
        if project_dir is None:
            raise ChainError("verify_anchor needs either public= or project_dir=")
        try:
            public = crypto_keys.load_public(project_dir)
        except crypto_keys.KeyError_ as e:
            raise ChainError(str(e)) from e

    if not isinstance(envelope, dict) or envelope.get("envelope") != ANCHOR_SCHEMA:
        return False
    anchor = envelope.get("anchor")
    sig_block = envelope.get("signature")
    if not isinstance(anchor, dict) or not isinstance(sig_block, dict):
        return False
    if sig_block.get("algorithm") != "ed25519":
        return False
    value = sig_block.get("value")
    if not isinstance(value, str):
        return False
    try:
        signature = bytes.fromhex(value)
    except ValueError:
        return False
    try:
        body = canonical_bytes(anchor)
    except ReceiptError:
        return False
    return ed25519.verify(public, body, signature)
