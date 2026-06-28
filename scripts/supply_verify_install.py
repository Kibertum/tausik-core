"""Install-time supply-chain verification (v15-supplychain-verify-install).

Checks a skill's `.tausik-signature.json` (written by `tausik skill sign`)
against the publisher key pinned for the repo it came from
(`tausik skill repo trust <repo> <ed25519:hex>`).

Outcome levels, aligned with the fail-closed policy
(docs/ru/research/failclosed-gates-audit.md):

  block   signed artifact + pinned key + signature/manifest mismatch,
          OR an unparseable pinned key (a broken trust anchor must not
          silently degrade to trust-everything)
  warn    unsigned artifact (adoption-path: most repos are unsigned
          today), or signed artifact with no pinned key (TOFU hint)
  ok      signed + pinned + verified
"""

from __future__ import annotations

import os
from typing import Any

from supply_sign import SIGNATURE_FILENAME, verify_signed_dir

LEVEL_OK = "ok"
LEVEL_WARN = "warn"
LEVEL_BLOCK = "block"


def decode_pubkey(raw: Any) -> bytes:
    """'ed25519:<64 hex>' or bare hex -> 32 public-key bytes. Raises ValueError."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("empty public key")
    text = raw.strip()
    if ":" in text:
        algo, hexpart = text.split(":", 1)
        if algo != "ed25519":
            raise ValueError(f"unsupported key algorithm {algo!r}")
    else:
        hexpart = text
    key = bytes.fromhex(hexpart)  # ValueError propagates
    if len(key) != 32:
        raise ValueError(f"expected 32 key bytes, got {len(key)}")
    return key


def check_skill_signature(
    skill_src: str, repo_name: str, pinned_pubkey: str | None
) -> tuple[str, str]:
    """(level, message) for an about-to-be-installed skill directory."""
    signed = os.path.isfile(os.path.join(skill_src, SIGNATURE_FILENAME))
    if not signed:
        return LEVEL_WARN, (
            f"skill is UNSIGNED (no {SIGNATURE_FILENAME}). Installing anyway — "
            "ask the publisher to `tausik skill sign` future releases."
        )
    if not pinned_pubkey:
        return LEVEL_WARN, (
            f"skill is signed but no publisher key is pinned for repo "
            f"'{repo_name}'. Installing UNVERIFIED — pin the key from an "
            f"out-of-band channel: tausik skill repo trust {repo_name} "
            "ed25519:<64 hex>"
        )
    try:
        public = decode_pubkey(pinned_pubkey)
    except ValueError as e:
        return LEVEL_BLOCK, (
            f"pinned key for repo '{repo_name}' is unusable ({e}) — refusing "
            f"to install with a broken trust anchor. Re-pin: tausik skill "
            f"repo trust {repo_name} ed25519:<64 hex>"
        )
    valid, detail = verify_signed_dir(skill_src, public)
    if valid:
        return LEVEL_OK, f"signature verified against pinned key for '{repo_name}' — {detail}"
    return LEVEL_BLOCK, (
        f"supply-chain check FAILED for repo '{repo_name}': {detail}. "
        "Install refused — the artifact does not match what the publisher signed."
    )
