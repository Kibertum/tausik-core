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

Current schema (RECEIPT_SCHEMA): see build_receipt() signature.
"""

from __future__ import annotations

import json
from typing import Any

RECEIPT_SCHEMA = "tausik-receipt/v3"

# v1 receipts (pre-l26-verify-git-diff-wire) carry no declared-scope fields.
# They remain cryptographically valid — verification re-canonicalizes the
# stored payload rather than rebuilding it from this module — but a reader
# must treat their scope as UNVERIFIED, not as complete.
LEGACY_RECEIPT_SCHEMA = "tausik-receipt/v1"

# v2 receipts (pre-v2-verify-receipt-as-argument) name neither the files they
# covered nor the gate set that ran. They stay cryptographically valid, and the
# freshness-lookup path still accepts them — but a receipt PRESENTED as the
# proof behind a close has to answer "over what?" and "with which gates?", and a
# v2 receipt cannot. `missing_v3_fields` names what is absent so the refusal can
# say so instead of returning a bare "invalid".
V3_REQUIRED_FIELDS = ("files", "gate_signature", "expires_at")


class ReceiptError(Exception):
    """Receipt construction/serialization failure."""


def missing_v3_fields(receipt: dict[str, Any]) -> list[str]:
    """Which v3 self-description fields this receipt does not carry.

    Empty list = the receipt states its own coverage and can be validated as a
    presented document. A non-empty list is the reason a handle redemption
    refuses, and it is quoted verbatim in that refusal: "unknown" must be
    reported as unknown, never rounded down to "complete" (#226) nor up to
    "tampered".

    Presence is judged by VALUE, not by key: `build_receipt` writes `None` for
    an unsupplied field rather than omitting it, so a key-only check would read
    a receipt that admits it knows nothing as fully specified.
    """
    if not isinstance(receipt, dict):
        return list(V3_REQUIRED_FIELDS)
    missing: list[str] = []
    for field in V3_REQUIRED_FIELDS:
        value = receipt.get(field)
        if value is None or (field == "files" and not value):
            missing.append(field)
    return missing


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
    configured_gates_count: int | None = None,
    files: list[str] | None = None,
    gate_signature: str | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    """Assemble a schema-v3 receipt dict.

    `gates` entries are reduced to the signable triple
    {name, passed, severity}; free-form gate output stays OUT of the
    receipt (it is bulky and non-deterministic).

    v2 adds the declared-scope fields (l26-verify-git-diff-wire). A receipt
    states what its gates covered, so it must also state whether that coverage
    was known to be complete. `declared_scope_status` is therefore never
    omitted: a caller that supplies nothing yields "unknown", never a silent
    absence that a reader could mistake for full coverage.

    `configured_gates_count` (risk-gate-coverage-configured-count-in-check) is
    the number of gates CONFIGURED for the trigger at verify time — the
    denominator the risk model's gate_coverage factor needs. `gates` above lists
    only the gates that RAN (skipped ones are excluded by design), so without
    this the denominator had to be recomputed from the CURRENT config at
    task-done — and a trust-tier flip between verify and done made it a different
    number, i.e. the factor compared two different gate sets. Capturing it here
    binds numerator and denominator to the same verify-time source.

    This does NOT bump RECEIPT_SCHEMA. The declared-scope fields warranted a
    v1->v2 bump because they changed what a receipt ASSERTS (a v1 receipt's scope
    is UNVERIFIED, not complete). This field asserts nothing new about coverage
    completeness — it is auxiliary telemetry for the risk model, and a receipt
    lacking it is not "wrong", it just has no verify-time count and the reader
    falls back to a recompute. Verification is version-agnostic (it
    re-canonicalizes the stored bytes, never branching on the schema string or
    field set), so old v2 receipts without the field stay valid and new v2
    receipts carrying it verify identically. A None value is included in the
    canonical form exactly like `files_hash`.

    v3 (v2-verify-receipt-as-argument) adds `files`, `gate_signature` and
    `expires_at` — and unlike `configured_gates_count` these DO warrant a schema
    bump, by the same rule that justified v1->v2: they change what a receipt
    ASSERTS. A v2 receipt carries `files_hash`, an opaque digest that can be
    COMPARED but not READ: it cannot tell a reader which paths it covered, so
    the security-sensitivity predicate could not be applied to it and the gate
    set behind it could not be named. With these three the receipt states its own
    coverage, its own gate set and its own expiry, which is what lets `task done`
    validate a PRESENTED receipt instead of searching for a fresh row.

    `gate_signature` is the same 16-hex digest that goes into the cache
    `command` (`verify_cache.resolve_gate_signature`), not a second computation
    of it — a signature the receipt derived independently could agree with the
    receipt and disagree with the row that authorized it.

    `expires_at` moves the freshness window INSIDE the signed document (SEP-2567:
    a durability policy the model cannot see is not a policy). It is signed, so
    it cannot be extended after the fact without breaking the signature.
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
        # int|None — never a float (canonical bytes reject those). None marks a
        # receipt built without a verify-time count; the risk model falls back.
        "configured_gates_count": (
            int(configured_gates_count) if configured_gates_count is not None else None
        ),
        # v3 self-description. Sorted for byte-stable canonical output and so a
        # reader's set comparison never depends on the caller's ordering — the
        # cache command sorts the same list for the same reason.
        "files": sorted(str(f) for f in files) if files else None,
        "gate_signature": str(gate_signature) if gate_signature else None,
        "expires_at": str(expires_at) if expires_at else None,
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
