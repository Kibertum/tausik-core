"""Sign/verify envelopes for canonical receipts.

v15-crypto-sign-verify-lib: glue between crypto_keys (project keypair),
crypto_receipt (canonical bytes) and crypto_ed25519 (RFC 8032 math).

Envelope format (tausik-signed/v1):
    {
      "envelope": "tausik-signed/v1",
      "receipt": {...},                  # schema tausik-receipt/v1
      "signature": {
        "algorithm": "ed25519",
        "key_fingerprint": "<16 hex>",   # sha256/16 of the public key
        "value": "<128 hex>"             # 64-byte ed25519 signature
      }
    }

The signature is computed over canonical_bytes(receipt) — never over the
envelope itself.
"""

from __future__ import annotations

from typing import Any

import crypto_ed25519 as ed25519
import crypto_keys
from crypto_receipt import ReceiptError, canonical_bytes

ENVELOPE_SCHEMA = "tausik-signed/v1"


class SignError(Exception):
    """Signing/verification precondition failure (not a bad signature)."""


def sign_receipt(project_dir: str, receipt: dict[str, Any]) -> dict[str, Any]:
    """Sign a receipt with the project key. Raises SignError without a key."""
    try:
        seed = crypto_keys.load_seed(project_dir)
    except crypto_keys.KeyError_ as e:
        raise SignError(str(e)) from e
    try:
        payload = canonical_bytes(receipt)
    except ReceiptError as e:
        raise SignError(f"receipt is not canonicalizable: {e}") from e
    public = ed25519.public_from_seed(seed)
    signature = ed25519.sign(seed, payload)
    return {
        "envelope": ENVELOPE_SCHEMA,
        "receipt": receipt,
        "signature": {
            "algorithm": "ed25519",
            "key_fingerprint": crypto_keys.fingerprint(public),
            "value": signature.hex(),
        },
    }


def verify_receipt(
    envelope: dict[str, Any],
    *,
    public: bytes | None = None,
    project_dir: str | None = None,
) -> bool:
    """True iff the envelope's signature matches its receipt.

    Key resolution order: explicit `public` bytes > project keystore at
    `project_dir`. Returns False on any structural defect — a verifier
    must never crash on attacker-controlled input.
    """
    if public is None:
        if project_dir is None:
            raise SignError("verify_receipt needs either public= or project_dir=")
        try:
            public = crypto_keys.load_public(project_dir)
        except crypto_keys.KeyError_ as e:
            raise SignError(str(e)) from e

    if not isinstance(envelope, dict) or envelope.get("envelope") != ENVELOPE_SCHEMA:
        return False
    receipt = envelope.get("receipt")
    sig_block = envelope.get("signature")
    if not isinstance(receipt, dict) or not isinstance(sig_block, dict):
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
        payload = canonical_bytes(receipt)
    except ReceiptError:
        return False
    return ed25519.verify(public, payload, signature)
