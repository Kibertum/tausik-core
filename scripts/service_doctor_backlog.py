"""Backlog hygiene check — open tasks that no epic can reach.

The release boundary of this project is defined MECHANICALLY: "everything in
epic X". `tausik roadmap` walks epics -> stories -> tasks, and `task list
--epic` joins through the same two hops. A task that hangs off neither is
therefore invisible to BOTH — it does not show up in the roadmap, and it is
not counted when someone asks "what is left before the release".

That is not hypothetical. It has now happened twice. The first batch of four
was reattached by hand and recorded as a decision; no signal was added, and
~20 sessions later exactly four more had accumulated — including the release
capstone task and a task the gate config points at by name. The scope answer
was wrong, and wrong in the direction of UNDER-reporting, which is the
direction nobody double-checks.

The invariant this checks is epic REACHABILITY, not story attachment. Both
ways of losing it look identical from the outside:

  * task with no story at all;
  * task on a story that belongs to no epic (possible if an epic was removed
    out from under it).

Detection only — never mutates, never raises. WARN, never FAIL: `task_add`
documents a standalone task as legitimate, so this has no authority to block.
Only OPEN tasks count; a closed orphan is harmless history that no longer
moves any scope number.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

_LABEL = "Backlog hygiene"
_DEFERRED_LABEL = "Deferred AC"

# An acceptance criterion explicitly parked at closure:
#   "AC-3: DEFERRED — baseline requires future runs"
#   "AC 8 (replay benchmark) deferred: needs a before/after session"
# DEFERRED must follow the criterion reference DIRECTLY — at most a
# parenthetical and a separator in between. Anything looser is worse than no
# check at all, and that is measured, not assumed: a first cut allowing 60
# characters of slack matched four tasks of which three were false. "Deferred
# loading" is a FEATURE NAME here (MCP tool loading), and notes also say things
# like "G8+G18 deferred per rollback policy then closed" — already resolved.
# A check that cries wolf three times out of four teaches the reader to skip
# doctor entirely, which costs more than the one real finding is worth.
_DEFERRED_AC = re.compile(
    r"AC[-\s#]?\d+\s*(?:\([^)\n]*\))?\s*[:\-—]?\s*DEFERRED\b(?!\s*[-\s]?load)",
    re.IGNORECASE,
)

# The legitimate way to clear this warning without doing the work now: hand the
# criterion to a task that owns it, and record that hand-off in the notes.
#
# Without this escape the check would be unclearable — the deferral text lives
# in a CLOSED task and can never stop matching, so the warning would stand
# forever no matter what anyone did. An unclearable warning teaches its reader
# to ignore the whole report; that failure is the subject of
# `doctor-claudemd-drift-warn-never-actionable`, and repeating it here would
# trade one real finding for the credibility of every other check.
_CARRIED_FORWARD = re.compile(r"CARRIED\s+BY\s+[a-z0-9][\w-]*", re.IGNORECASE)

# Everything except `done`. A closed task is out of every scope count already,
# so orphaning it costs nothing and warning about it would be pure noise.
_OPEN_STATUSES = "planning,active,blocked,review"

# How many slugs to name inline. The point is to make the next fix actionable,
# not to reprint the backlog into a health check.
_NAMED_LIMIT = 3


class _Backlog(Protocol):
    def task_list(self, status: str | None = ...) -> list[dict[str, Any]]: ...

    def epic_list(self) -> list[dict[str, Any]]: ...


def find_deferred_acs_in_live_work(svc: _Backlog) -> list[str]:
    """Closed tasks that parked an acceptance criterion, inside a still-open epic.

    The failure this exists to catch: `v14b-baseline-token-metrics` closed on
    2026-05-06 with two criteria marked DEFERRED ("accumulates naturally"), and
    nothing ever looked again. Two and a half months later the follow-up that
    depended on them could not be satisfied at all, because the data those
    criteria were supposed to produce had never been captured. A criterion
    deferred at closure is a promise with no due date and no owner.

    Scoped to OPEN epics on purpose. Ten closed tasks in this project carry a
    deferred criterion; six belong to epics that shipped long ago and are
    archaeology, not work. Reporting all ten would produce a standing warning
    that cannot be cleared by any legitimate action — the exact pattern that
    teaches a reader to skip doctor's output entirely.
    """
    try:
        epics = svc.epic_list()
    except Exception:  # noqa: BLE001 — a health check must not crash the doctor
        return []
    open_epics = {str(e.get("slug")) for e in epics if e.get("slug") and e.get("status") != "done"}
    if not open_epics:
        return []
    out: list[str] = []
    for row in svc.task_list(status="done"):
        slug, notes = row.get("slug"), str(row.get("notes") or "")
        if not slug or row.get("epic_slug") not in open_epics:
            continue
        if _DEFERRED_AC.search(notes) and not _CARRIED_FORWARD.search(notes):
            out.append(str(slug))
    return sorted(out)


def check_deferred_acs(svc: _Backlog) -> list[tuple[str, str, str]]:
    """Doctor finding for criteria parked at closure in work still in flight."""
    parked = find_deferred_acs_in_live_work(svc)
    if not parked:
        return [("ok", _DEFERRED_LABEL, "no closed task in an open epic parked a criterion")]

    named = parked[:_NAMED_LIMIT]
    shown = ", ".join(named)
    rest = len(parked) - len(named)
    if rest > 0:
        shown += f", +{rest} more"
    return [
        (
            "warn",
            _DEFERRED_LABEL,
            f"{len(parked)} closed task(s) in an OPEN epic marked an acceptance "
            f"criterion DEFERRED — it has no owner and no due date, and the epic "
            f"can close over it: {shown}. Fix: finish the criterion, or hand it to "
            f"a task that owns it and record that — "
            f'`tausik task log <slug> "AC-N CARRIED BY <owning-slug>"`',
        )
    ]


def find_unreachable_open_tasks(svc: _Backlog) -> list[str]:
    """Slugs of open tasks that no epic can reach, sorted for stable output."""
    rows = svc.task_list(status=_OPEN_STATUSES)
    return sorted(
        str(row.get("slug")) for row in rows if not row.get("epic_slug") and row.get("slug")
    )


def check_backlog_hygiene(svc: _Backlog) -> list[tuple[str, str, str]]:
    """Doctor findings for epic-unreachable open tasks.

    Each finding is (severity, label, detail), severity in {ok, warn}.
    """
    orphans = find_unreachable_open_tasks(svc)
    if not orphans:
        return [("ok", _LABEL, "every open task is reachable from an epic")]

    named = orphans[:_NAMED_LIMIT]
    shown = ", ".join(named)
    rest = len(orphans) - len(named)
    if rest > 0:
        shown += f", +{rest} more"

    return [
        (
            "warn",
            _LABEL,
            f"{len(orphans)} open task(s) belong to no epic and are invisible to "
            f"`tausik roadmap` and to `task list --epic` — release scope counts "
            f"them as absent: {shown}. Fix: tausik task move <slug> <story>",
        )
    ]
