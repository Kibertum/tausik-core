"""Three refusals, three next steps: STALE, FAILED, NOT FOUND.

A refusal to close used to say WHY and leave the reader to infer WHAT NEXT, and
two very different next steps read alike: "the evidence was valid, the tree or
the gates or the clock moved — re-run verify" and "the check did not pass — fix
the code". Borrowed from ai-review-gate.mjs (github.com/kiaquila/unicorn-hub,
MIT), where a moved head is a skip with an explanation, not a failure.

STALE never becomes a silent success: it is still a refusal, only with a
different next step. Every refusal point — the verify handle, the receipt
rules, and the close without a handle — goes through `head`.
"""

from __future__ import annotations

from typing import Any

STALE, FAILED, NOT_FOUND = "STALE", "FAILED", "NOT FOUND"

_HEADS = {
    STALE: "STALE — the evidence was valid, but the tree, the gates or the clock moved; "
    "next: re-run verify.",
    FAILED: "FAILED — the check did not prove this close; next: fix the cause, then verify.",
    NOT_FOUND: "NOT FOUND — there is no evidence for this task to redeem; next: run verify "
    "and present the handle it prints.",
}

#: Handle/receipt refusals that are about TIME or CHANGE, not about a failure.
_STALE_MARKERS = (
    "expired at",
    "already spent",
    "no readable expiry",
    "nonce does not match",
    "have changed since",
    "gate set changed since",
)
#: Refusals that say the presented thing is not evidence for THIS task at all.
_NOT_FOUND_MARKERS = (
    "is not a handle",
    "no verify run #",
    "but you are closing",
    "receipt is signed for task",
)


def classify(reason: str) -> str:
    """The kind of a handle or receipt refusal, read from its own text."""
    if any(m in reason for m in _STALE_MARKERS):
        return STALE
    if any(m in reason for m in _NOT_FOUND_MARKERS):
        return NOT_FOUND
    return FAILED


def head(kind: str) -> str:
    return _HEADS[kind]


def labelled(reason: str) -> str:
    """`reason` with its kind and next step in front; idempotent."""
    if reason.startswith(tuple(_HEADS.values())):
        return reason
    return f"{head(classify(reason))} {reason}"


def last_run_kind(be: Any, slug: str) -> tuple[str, str]:
    """Why a close without a handle found no fresh green run: (kind, detail)."""
    try:
        row = be._q1(  # ruff-not-enabled: SLF001 — read-only
            "SELECT id, exit_code, ran_at FROM verification_runs WHERE task_slug=? "
            "ORDER BY id DESC LIMIT 1",
            (slug,),
        )
    except Exception:  # noqa: BLE001 — the refusal stands either way
        row = None
    if not row:
        return NOT_FOUND, "no verify run was ever recorded for this task"
    if int(row.get("exit_code") or 0) != 0:
        return FAILED, f"the last verify run #{row['id']} ({row['ran_at']}) did not pass"
    return STALE, (
        f"the last verify run #{row['id']} ({row['ran_at']}) passed, but it is older than "
        "the cache window or the files it covered have changed"
    )
