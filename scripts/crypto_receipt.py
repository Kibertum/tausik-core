"""Canonical verification receipt — deterministic bytes for signing.

v15-crypto-canonical-receipt: a receipt is the signable record of one
verification run. The same logical receipt must always serialize to the
same bytes, or signatures become unverifiable across replatforms.

Canonical form (JCS / RFC 8785 spirit, restricted profile):
  - keys sorted lexicographically at every level
  - separators "," / ":" with no whitespace
  - ensure_ascii=True (byte-stable across locales)
  - only None/bool/int/str and nested dict/list allowed — floats are
    REJECTED (two platforms may render them differently), as are NaN/Inf
    and any non-JSON type. Timestamps are ISO-8601 strings.

Schema v1 (RECEIPT_SCHEMA): see build_receipt() signature.
"""

from __future__ import annotations

import json
from typing import Any

RECEIPT_SCHEMA = "tausik-receipt/v2"

# v1 receipts (pre-l26-verify-git-diff-wire) carry no declared-scope fields.
# They remain cryptographically valid — verification re-canonicalizes the
# stored payload rather than rebuilding it from this module — but a reader
# must treat their scope as UNVERIFIED, not as complete.
LEGACY_RECEIPT_SCHEMA = "tausik-receipt/v1"


class ReceiptError(Exception):
    """Receipt construction/serialization failure."""


def build_receipt(
    *,
    task_slug: str,
    git_sha: str | None,
    scope: str,
    gates: list[dict[str, Any]],
    passed: bool,
    ran_at: str,
    files_hash: str | None = None,
    key_fingerprint: str | None = None,
    declared_scope_status: str | None = None,
    undeclared_files: list[str] | None = None,
    undeclared_count: int | None = None,
) -> dict[str, Any]:
    """Assemble a schema-v2 receipt dict.

    `gates` entries are reduced to the signable triple
    {name, passed, severity}; free-form gate output stays OUT of the
    receipt (it is bulky and non-deterministic).

    v2 adds the declared-scope fields (l26-verify-git-diff-wire). A receipt
    states what its gates covered, so it must also state whether that coverage
    was known to be complete. `declared_scope_status` is therefore never
    omitted: a caller that supplies nothing yields "unknown", never a silent
    absence that a reader could mistake for full coverage.
    """
    if not task_slug:
        raise ReceiptError("task_slug is required")
    if not ran_at:
        raise ReceiptError("ran_at is required (ISO-8601 UTC string)")
    slim_gates: list[dict[str, Any]] = [
        {
            "name": str(g.get("name", "")),
            "passed": bool(g.get("passed", False)),
            "severity": str(g.get("severity", "warn")),
        }
        for g in gates
    ]
    slim_gates.sort(key=lambda g: str(g["name"]))
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "task_slug": task_slug,
        "git_sha": git_sha,
        "scope": scope,
        "gates": slim_gates,
        "passed": bool(passed),
        "ran_at": ran_at,
        "files_hash": files_hash,
        "key_fingerprint": key_fingerprint,
        # Sorted for byte-stable canonical output; the count is the untruncated
        # total, so a capped listing never understates the divergence.
        "declared_scope_status": str(declared_scope_status or "unknown"),
        "undeclared_files": sorted(str(f) for f in (undeclared_files or [])),
        "undeclared_count": int(
            undeclared_count if undeclared_count is not None else len(undeclared_files or [])
        ),
    }
    return receipt


def _check_canonicalizable(value: Any, path: str = "$") -> None:
    """Reject anything that cannot serialize byte-identically everywhere."""
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        raise ReceiptError(
            f"{path}: float values are not allowed in canonical receipts "
            "(platform-dependent rendering) — use str or scaled int"
        )
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise ReceiptError(f"{path}: non-string dict key {k!r}")
            _check_canonicalizable(v, f"{path}.{k}")
        return
    if isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _check_canonicalizable(v, f"{path}[{i}]")
        return
    raise ReceiptError(f"{path}: type {type(value).__name__} is not JSON-canonicalizable")


def canonical_bytes(receipt: dict[str, Any]) -> bytes:
    """Deterministic UTF-8/ASCII bytes of a receipt — the signing payload."""
    _check_canonicalizable(receipt)
    return json.dumps(
        receipt,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
