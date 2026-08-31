"""Entries a live `supersedes` edge has already retired, kept out of the tail.

THE DEFECT (memory-tail-shows-a-superseded-entry-next-to-its-replacement, found
in session #191 while reading a commit of that same session). The dynamic block
of CLAUDE.md prints the newest five memories BY AGE and asks the graph nothing.
So it printed, two lines apart, "#441 ADR inventory recounted by machine:
thirteen accepted, seven assessed" and "#432 ADR inventory: twelve accepted,
three assessed" — while `memory#441 --[supersedes]--> memory#432` had existed
since the session that wrote both.

WHY THAT IS EXPENSIVE HERE SPECIFICALLY. The tail is the FIRST thing a fresh
agent reads; it is injected into the context at session start. Two mutually
exclusive facts about one subject arrive with no sign of which is alive. The bad
outcome is not "reads the wrong one" but "believes the OLD one, because the rest
of the history corroborates it" — measured: the count "twelve accepted" is why
`four-accepted-adrs-were-never-assessed` treated four ADRs as unassessed instead
of ten.

THE MECHANISM EXISTED AND THE CONSUMER DID NOT ASK. `memory lint` has reported
`superseded` findings from these very edges since v15p; the renderer simply
never called anything. That is the same shape as the commit-trigger gates whose
only consumer was dead — a repair, not a new capability.

WHAT COUNTS AS RETIRED. An incoming `supersedes` edge FROM A LIVE ENTRY. The
liveness of the SOURCE is the whole condition: if the replacement was itself
archived, the older entry is the best knowledge left and hiding it would leave
the subject unrepresented. `edge_list` already excludes soft-invalidated edges
(`valid_to`), so an edge somebody retracted stops hiding anything.

CHAINS NEED NO RECURSION. With `A supersedes B supersedes C`, B is retired by a
live A and C is retired by a live B — B being hidden from a rendered list is not
the same as B being archived, and the predicate is asked per entry. Only A
survives, which is the answer, arrived at without walking the graph.

FAIL-OPEN, AND THAT IS THE STRICT DIRECTION. Any failure to read the graph
answers "not superseded", so the tail degrades to exactly what it printed before
this module existed. These aggregates are documented as never breaking their
caller — the session-start hook and the CLAUDE.md refresh — and the failure mode
here costs a stale line in a recap, never a lost live fact. A fail-closed
version would silently drop knowledge whenever the graph hiccupped, which is the
opposite of what the tail is for.
"""

from __future__ import annotations

from typing import Any, Callable

SUPERSEDES = "supersedes"

# `edge_list(n=...)` caps a LIST; asked about ONE node it is a per-node bound.
# 200 is not a display budget — it is "more edges than one memory will ever
# carry", so the answer is not quietly wrong on a heavily linked entry.
_EDGES_PER_NODE = 200


Memo = dict["tuple[str, int]", "int | None"]


def as_int(value: Any) -> int | None:
    """`value` as an int, or None when it is not one. Ids arrive from rows."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def superseder_of(be: Any, node_type: str, node_id: Any, memo: Memo | None = None) -> int | None:
    """Id of the LIVE entry that supersedes `node_id`, or None.

    None on every doubt — no id, no readable graph, a superseder that is gone or
    archived — because None means "print it", and printing a live fact one line
    too long is cheaper than hiding one that is still true.
    """
    nid = as_int(node_id)
    if nid is None:
        return None
    key = (node_type, nid)
    if memo is not None and key in memo:
        return memo[key]
    result = _lookup(be, node_type, nid)
    if memo is not None:
        memo[key] = result
    return result


def _lookup(be: Any, node_type: str, nid: int) -> int | None:
    try:
        edges = be.edge_list(
            node_type=node_type, node_id=nid, relation=SUPERSEDES, n=_EDGES_PER_NODE
        )
    except Exception:  # noqa: BLE001 — an unreadable graph retires nothing
        return None
    for edge in edges or []:
        try:
            target_id, source_id = int(edge["target_id"]), int(edge["source_id"])
        except (KeyError, TypeError, ValueError):
            continue
        # `edge_list` returns edges on BOTH sides of the node. An entry that
        # supersedes something else is not thereby superseded itself, so the
        # side matters and the type is part of the identity: memory#441 and
        # decision#441 are different nodes.
        if (edge.get("target_type") or "memory") != node_type or target_id != nid:
            continue
        if _is_live(be, edge.get("source_type") or "memory", source_id):
            return source_id
    return None


def _is_live(be: Any, node_type: str, node_id: int) -> bool:
    """Does the superseding node still stand? Archived or missing → no."""
    try:
        if node_type == "decision":
            return be.decision_get(node_id) is not None
        row = be.memory_get(node_id)
    except Exception:  # noqa: BLE001 — unreadable node retires nothing
        return False
    return bool(row) and not row.get("archived_at")


def live_head(
    be: Any,
    fetch: Callable[[int], list[dict[str, Any]]],
    node_type: str,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[int, list[int]]]:
    """The newest `limit` entries no live entry has superseded, plus what they replaced.

    `fetch(n)` returns the newest `n` rows of one section, newest first — the
    same call the section made before this filter existed.

    Returns `(rows, retired)`. `retired` maps a SURVIVING entry's id to the ids
    it pushed out of this section, so the caller can say so on the line it was
    going to print anyway. It holds only entries that actually lost a slot: rows
    beyond the quota were never going to be shown, and announcing them would
    describe a competition that did not happen.

    THE QUOTA IS REFILLED, NOT LEFT SHORT (AC3). A hidden entry frees its line
    for the next live one, so the section keeps its size instead of shrinking by
    the number of corrections the project has recorded — which would punish
    exactly the projects that maintain their memory. That needs more rows than
    the quota, so the fetch doubles until enough live rows are found or the
    store runs out. Termination is the store's, not a magic ceiling's: a fetch
    returning fewer rows than asked is the end of the section.
    """
    want = max(int(limit), 1)
    memo: Memo = {}
    kept: list[dict[str, Any]] = []
    retired: dict[int, list[int]] = {}
    while True:
        rows = fetch(want) or []
        kept, retired = [], {}
        for row in rows:
            if len(kept) >= limit:
                break
            rid = as_int(row.get("id"))
            if rid is None:
                # A row with no usable id cannot be looked up in the graph and
                # cannot be named in a `(supersedes #N)` suffix either. Print it:
                # the only alternative is dropping a live entry over a missing
                # field, which is the failure this filter must not have.
                kept.append(row)
                continue
            superseder = superseder_of(be, node_type, rid, memo)
            if superseder is None:
                kept.append(row)
            else:
                retired.setdefault(superseder, []).append(rid)
        if len(kept) >= limit or len(rows) < want:
            return kept[:limit], retired
        want *= 2
