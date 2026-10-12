"""Integrity checks for vendored external skills (vendor-lock-integrity).

The .lock file recorded a sha256 of every downloaded tarball and then never
read it back: sync_deps decided "up-to-date" on the ref string alone. A digest
compared against nothing is not a check, so this module adds the missing half —
an *expected* digest declared in skills.json, plus a loud signal when a spec
pins a mutable branch and declares no digest at all.

Pure functions over bytes and strings: no network, no filesystem, no printing.
"""

from __future__ import annotations

import hashlib
import re

# A ref we can treat as immutable enough to skip the warning: a full commit SHA.
# Tags are *conventionally* stable but git lets them move, so they warn too —
# unless the spec declares a digest, which settles the question outright.
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def tarball_digest(tarball: bytes) -> str:
    """sha256 hex of a downloaded tarball."""
    return hashlib.sha256(tarball).hexdigest()


def is_pinned_ref(ref: str) -> bool:
    """True when the ref alone identifies one immutable artifact."""
    return bool(_COMMIT_SHA.match(ref or ""))


def digest_mismatch(name: str, actual: str, expected: str | None) -> str | None:
    """Error text when a declared digest does not match, else None.

    Returning text rather than raising keeps sync_deps' per-skill error handling
    intact: one bad dependency must not abort the whole bootstrap.
    """
    if not expected:
        return None
    # Case-insensitive: hexdigest() is always lower-case, but the expected
    # value is hand-copied into skills.json and plenty of tools render hashes
    # upper-case. A pin that matches byte-for-byte must not fail on casing.
    if actual.strip().lower() == expected.strip().lower():
        return None
    return (
        f"integrity check FAILED for '{name}': downloaded tarball is "
        f"sha256:{actual}, but skills.json declares sha256:{expected}. "
        f"Refusing to unpack — the artifact is not what this repo pinned."
    )


def mutable_ref_warning(name: str, repo: str, ref: str, expected: str | None) -> str | None:
    """Warning text when nothing pins this dependency to a fixed artifact."""
    if expected or is_pinned_ref(ref):
        return None
    return (
        f"  WARNING: '{name}' tracks {repo}@{ref}, a moving target, and declares "
        f"no sha256. Whatever that ref points to at download time is executed "
        f'from your scripts/ tree. Pin it: add "sha256" to skills.json.'
    )


def sha_change_note(previous: str | None, actual: str) -> dict[str, str] | None:
    """Record that a re-sync brought different bytes than the lock remembered."""
    if not previous or previous.strip().lower() == actual.strip().lower():
        return None
    return {"from": previous, "to": actual}
