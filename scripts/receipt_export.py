"""Portable receipt export — verifiable outside SQLite (v15-receipt-export).

Wraps a stored tausik-signed/v1 envelope together with the project public
key into a self-contained artifact:

    {
      "export": "tausik-receipt-export/v1",
      "envelope": {...},                 # tausik-signed/v1, untouched
      "public_key": "ed25519:<64 hex>",  # crypto_keys encoding
      "key_fingerprint": "<16 hex>"
    }

Anyone holding the file can re-verify the ed25519 signature with the
embedded key and compare the fingerprint against an out-of-band channel
(`tausik key show`, PR description, CI variable). Trust anchoring is
deliberately out of scope — the artifact proves integrity, the
fingerprint comparison proves origin.

AND THAT CAVEAT USED TO STOP HERE, in a docstring the person running the command
never reads. MEASURED: a receipt for a task nobody ran, signed with a key generated
three lines earlier and embedded in the artifact, came back `VALID ed25519 signature`
with exit code 0. The paragraph above was right and the verdict did not carry it.

So the verdict now distinguishes the two facts it was conflating:

  * INTEGRITY — the signature matches the key in the file. Real and useful: the
    payload was not edited after signing. Says nothing about who signed.
  * ORIGIN — the signature matches a key the VERIFIER chose, passed explicitly or
    found in a local keystore. Only this answers "is this receipt ours".

`verify_export` returns both, and integrity-only leaves the CLI with a non-zero exit
so a pipeline using it as a gate fails closed rather than accepting a forgery. A key
that travels with what it certifies is not a root of trust, and a tool that prints
otherwise is worse than one that refuses.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

EXPORT_SCHEMA = "tausik-receipt-export/v1"


class ExportError(Exception):
    """Export construction/parsing failure (not a bad signature)."""


def build_export(envelope: dict[str, Any], public: bytes) -> dict[str, Any]:
    """Self-contained export dict from a stored envelope + public key."""
    import crypto_keys

    if not isinstance(envelope, dict) or "receipt" not in envelope:
        raise ExportError("not a signed receipt envelope")
    return {
        "export": EXPORT_SCHEMA,
        "envelope": envelope,
        "public_key": f"ed25519:{public.hex()}",
        "key_fingerprint": crypto_keys.fingerprint(public),
    }


def default_export_path(project_dir: str, envelope: dict[str, Any]) -> str:
    """.tausik/receipts/<task>-<sha8|nogit>.json (slug sanitized)."""
    receipt = envelope.get("receipt") or {}
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", str(receipt.get("task_slug") or "receipt"))
    sha = str(receipt.get("git_sha") or "")[:8] or "nogit"
    out_dir = os.path.join(project_dir, ".tausik", "receipts")
    return os.path.join(out_dir, f"{slug}-{sha}.json")


def write_export(export: dict[str, Any], path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(export, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return path


def verify_export(
    data: Any,
    *,
    public: bytes | None = None,
) -> tuple[bool, str, bool]:
    """(valid, detail, trusted_key) for a parsed export artifact — no DB, no keystore.

    `trusted_key` is the third value and the point of this function: True when the key
    came from the CALLER, False when it came out of the artifact. It describes the
    key's PROVENANCE, not the outcome — an explicit key with a bad signature is still
    a decided question, and reporting it as undecided would hide a real refusal.

    With the embedded key the signature still proves the payload was not edited, and
    proves nothing about who signed it: a forged receipt carrying its own fresh key
    verifies perfectly.

    Key resolution: explicit `public` overrides the embedded key. Structural defects
    raise ExportError so callers can distinguish "garbage file" (exit 2) from "real
    artifact, bad signature" (exit 1).
    """
    if not isinstance(data, dict) or data.get("export") != EXPORT_SCHEMA:
        raise ExportError(f"not a {EXPORT_SCHEMA} artifact")
    envelope = data.get("envelope")
    if not isinstance(envelope, dict):
        raise ExportError("artifact has no envelope")

    trusted_key = public is not None
    if public is None:
        raw_key = data.get("public_key")
        if not isinstance(raw_key, str) or not raw_key.startswith("ed25519:"):
            raise ExportError("artifact has no usable embedded public_key")
        try:
            public = bytes.fromhex(raw_key.split(":", 1)[1])
        except ValueError as e:
            raise ExportError(f"corrupt embedded public_key: {e}") from e
        if len(public) != 32:
            raise ExportError("embedded public_key is not 32 bytes")

    import crypto_keys
    import crypto_sign

    fp = crypto_keys.fingerprint(public)
    if not crypto_sign.verify_receipt(envelope, public=public):
        # `trusted_key` stays whatever it was: it describes where the key CAME FROM,
        # not whether the signature matched. Collapsing it to False on a bad signature
        # would say "origin unchecked" about a check the caller explicitly asked for.
        return (
            False,
            f"INVALID signature against key {fp} — payload or signature modified",
            trusted_key,
        )
    if trusted_key:
        return True, f"VALID ed25519 signature against the key you supplied (key {fp})", True
    return (
        True,
        f"INTEGRITY ONLY — the signature matches the key INSIDE the file (key {fp}). "
        "That proves the payload was not edited after signing, and nothing about who "
        f"signed it: anyone can sign a fabricated receipt with their own key. To prove "
        f"origin, compare {fp} with `tausik key show` on the issuing project, or re-run "
        "with --pub.",
        False,
    )
