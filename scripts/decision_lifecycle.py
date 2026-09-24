"""A decision has a life: what it turned down, and what later replaced it.

1.10, story D (decisions-have-no-lifecycle) — the 1.8 users' complaint "the
framework does not record bad decisions", measured. In session #267: 384
decisions, about 100 naming a rejected alternative only in prose, 33 reversing
an earlier one only in prose, and ONE supersedes edge. A reversed decision stayed
a live instruction forever, and "was this already tried?" was answered by
reading every text in turn.

WHAT THIS ADDS, on the tables that exist:
  * `rejected` — alternatives turned down, a JSON list in `decisions.rejected`
    (v66), each "option :: why". Searchable, not prose. NEVER required: a
    decision without alternatives exists, and forcing the field would breed
    invented ones.
  * supersession — an edge `supersedes` in `memory_edges`, the store memory
    already uses (memory_supersedes). It needs a reason; an unexplained
    reversal is the prose problem again.
  * the list — `decisions --status active|superseded|all`, `--task`,
    `--rejected QUERY`. A superseded decision is never deleted: it leaves the
    active list and the memory block, and stays findable with who replaced it.
"""

from __future__ import annotations

import json
from typing import Any

from tausik_utils import ServiceError

STATUSES = ("all", "active", "superseded")


def normalize_rejected(items: list[str] | None) -> str | None:
    """JSON for the column, or None; empty entries are refused, not dropped."""
    if not items:
        return None
    clean = [str(i).strip() for i in items]
    if any(not i for i in clean):
        raise ServiceError("--rejected takes 'option :: why'; an empty entry is not an option")
    return json.dumps(clean, ensure_ascii=False)


def rejected_of(row: dict[str, Any]) -> list[str]:
    try:
        value = json.loads(row.get("rejected") or "[]")
    except ValueError:
        return []
    return [str(v) for v in value] if isinstance(value, list) else []


def _require_reason(old_id: int, reason: str | None) -> None:
    if not (reason or "").strip():
        raise ServiceError(
            f"superseding decision #{old_id} needs a reason (--because or --rationale): "
            "an unexplained reversal is the prose problem this replaces"
        )


def supersede(svc: Any, new_id: int, old_id: int, reason: str | None) -> str:
    """Link `new_id` supersedes `old_id`; refuses a missing target or reason."""
    _require_reason(old_id, reason)
    if not svc.be.decision_get(old_id):
        raise ServiceError(f"Decision #{old_id} not found")
    svc.memory_link("decision", new_id, "decision", old_id, "supersedes", created_by="decide")
    return f" Supersedes #{old_id}."


def check_before_write(svc: Any, supersedes: int | None, reason: str | None) -> None:
    """Refuse a supersession that cannot be written BEFORE the new decision exists."""
    if supersedes is None:
        return
    _require_reason(supersedes, reason)
    if not svc.be.decision_get(supersedes):
        raise ServiceError(f"Decision #{supersedes} not found")


def _superseder_map(be: Any) -> dict[int, int]:
    """target decision id -> the live decision that supersedes it, in ONE query.

    The per-row graph lookup cost one query per decision (session #267 review:
    up to 10,000 for `--task`). Same rule as memory_supersedes: a valid edge,
    and a superseder that still exists.
    """
    edges = be._q(  # noqa: SLF001 — read-only, the backend's own helper
        "SELECT e.source_id AS s, e.target_id AS t FROM memory_edges e "
        "JOIN decisions d ON d.id = e.source_id WHERE e.relation='supersedes' "
        "AND e.source_type='decision' AND e.target_type='decision' AND e.valid_to IS NULL "
        "ORDER BY e.created_at"
    )
    return {int(r["t"]): int(r["s"]) for r in edges}


def listing(
    svc: Any,
    n: int = 20,
    status: str = "all",
    task: str | None = None,
    rejected: str | None = None,
) -> list[dict[str, Any]]:
    """Decisions with `superseded_by` and `rejected` filled, filtered as asked."""
    if status not in STATUSES:
        raise ServiceError(f"--status must be one of {', '.join(STATUSES)}")
    pool = n if status == "all" and not task and not rejected else max(n, 10_000)
    rows = svc.be.decision_list(pool)
    superseders = _superseder_map(svc.be)
    out: list[dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        if task and row.get("task_slug") != task:
            continue
        row["rejected"] = "; ".join(rejected_of(row))
        if rejected and rejected.lower() not in row["rejected"].lower():
            continue
        row["superseded_by"] = superseders.get(int(row["id"]))
        if status == "active" and row["superseded_by"]:
            continue
        if status == "superseded" and not row["superseded_by"]:
            continue
        out.append(row)
        if len(out) >= n:
            break
    return out
