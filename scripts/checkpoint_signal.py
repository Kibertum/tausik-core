"""The checkpoint counter (SENAR 9.3) is DERIVED from the journal, not maintained.

Factor 5 of 12-factor agents, taken on in 1.10: execution state is computed from
the domain record instead of being kept beside it. Until 1.10 the MCP server
incremented `meta.tool_call_count` on every MCP call and a handoff zeroed it —
a second copy of a number the ledger already holds, which drifted: it counted
MCP calls only (not the shell or file tools), and in 1.8 a handoff reset it as
a side effect nobody asked for.

Now: calls since the last checkpoint = the session's `usage_events` count
(`session_capacity_summary`, one row per tool call written by the PostToolUse
hook) minus the count the session's last handoff recorded when it was written
(`calls_at_write`). Writing a handoff IS the reset, and it is a recorded fact
rather than a mutation.

What is still stored is display state only: the last ten-call bucket a warning
was printed for (`checkpoint_warn_bucket`), so the advice does not repeat on
every call. The count itself is never stored.
"""

from __future__ import annotations

import json
from typing import Any

CHECKPOINT_THRESHOLD = 40
_BUCKET_KEY = "checkpoint_warn_bucket"


def calls_now(be: Any) -> int | None:
    """Tool calls recorded for the open session, or None when none is open."""
    summary = be.session_capacity_summary(0)
    if summary.get("session") is None:
        return None
    return int(summary.get("used") or 0)


def calls_since_checkpoint(be: Any) -> int | None:
    """Calls since the open session's last handoff; None when no session is open."""
    now = calls_now(be)
    if now is None:
        return None
    current = be.session_current()
    base = 0
    raw = current.get("handoff") if current else None
    if raw:
        try:
            base = int(json.loads(raw).get("calls_at_write") or 0)
        except (ValueError, TypeError, AttributeError):
            base = 0
    return max(0, now - base)


def checkpoint_advice(be: Any, threshold: int = CHECKPOINT_THRESHOLD) -> str:
    """A one-line advisory when the derived count crosses a new ten-call bucket."""
    if threshold <= 0:
        return ""  # 0 switches the signal off
    n = calls_since_checkpoint(be)
    if n is None:
        return ""
    if n < threshold:
        if be.meta_get(_BUCKET_KEY):
            be.meta_set(_BUCKET_KEY, "0")
        return ""
    bucket = n // 10
    try:
        last = int(be.meta_get(_BUCKET_KEY) or 0)
    except (ValueError, TypeError):
        last = 0
    if bucket <= last:
        return ""
    be.meta_set(_BUCKET_KEY, str(bucket))
    return (
        f"\n⚠ SENAR Rule 9.3: {n} tool calls since the last checkpoint "
        f"(derived from the session's usage events). Consider /checkpoint."
    )


def no_session_note(be: Any) -> str:
    """Said aloud when there is no session to count against (never a silent zero)."""
    return (
        "checkpoint counter: no open session — tool calls are not attributed, "
        "so calls since the last checkpoint are unmeasured"
        if calls_now(be) is None
        else ""
    )
