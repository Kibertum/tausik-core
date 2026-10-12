"""Context-pressure numbers with a basis (SENAR 1.5 §9.4; 1.10, story E).

Two things live here. `summary()` turns `session recompute` rows into the
figures a threshold's basis is written from — median, p90, maximum active
minutes and the share of sessions above the threshold — so the basis in
`docs/*/session-active-time.md` is the output of a command, dated, and not a
number typed from memory (convention #673). `note_crossing()` records the
moment a session crosses its advisory threshold as an event, once per session
(§9.4(d): a crossed target is recorded, not quietly passed); it never refuses.

A threshold of 0 or below means the signal is off: nothing is printed and
nothing is recorded.
"""

from __future__ import annotations

from typing import Any

CROSSED = "session_threshold_crossed"


def summary(rows: list[dict[str, Any]], threshold: int) -> dict[str, Any]:
    """Median, p90, max active minutes and the share of sessions above `threshold`."""
    active = sorted(int(r.get("active_minutes") or 0) for r in rows)
    if not active:
        return {"sessions": 0}
    n = len(active)

    def pct(p: float) -> int:
        return active[min(n - 1, int(p * n))]

    median = active[n // 2] if n % 2 else (active[n // 2 - 1] + active[n // 2]) // 2
    over = sum(1 for a in active if threshold > 0 and a > threshold)
    return {
        "sessions": n,
        "median_active": median,
        "p90_active": pct(0.9),
        "max_active": active[-1],
        "threshold": threshold,
        "over_threshold": over,
    }


def note_crossing(be: Any, session_id: int, active: int, threshold: int) -> bool:
    """Record the first crossing of `threshold` by this session. True if recorded now."""
    if threshold <= 0:
        return False
    for ev in be.events_list(entity_type="session", entity_id=str(session_id)):
        if ev.get("action") == CROSSED:
            return False
    be.event_add(
        "session",
        str(session_id),
        CROSSED,
        f'{{"active":{active},"threshold":{threshold}}}',
    )
    return True
