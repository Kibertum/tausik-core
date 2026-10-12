"""Promote an existing project record to the shared store — shown first, then written.

Measured in session #189: the shared store held 2,498 decisions from one import
and 14 memories from three projects; this project, with 426 memories and 270
decisions, had written nothing to it. Three of the 14 were about TAUSIK itself,
written by a CONSUMER. The cause was mechanical: `--global` exists only at
creation, so sharing a record already written meant typing it again.

THE ACT STAYS EXPLICIT. Decision #221's classifier decided on its own what to
publish and sent six internal decisions out; nothing here guesses. `promote`
prints exactly what will leave the project — the whole text, not a title — and
writes only with `--yes`. The shared store is not redacted: secrets and PII go
verbatim, and the preview says so.

PROVENANCE SURVIVES: `origin_project` is this project's label and `origin_slug`
is the local record's stable slug, so the shared row says where it came from,
and promoting the same record twice is refused instead of duplicated.
"""

from __future__ import annotations

import json
from typing import Any

from tausik_utils import ServiceError

_WARNING = (
    "The shared store is NOT redacted: what is shown goes verbatim, secrets and PII "
    "included, and every project on this machine can read it."
)


def _local(svc: Any, kind: str, rid: int) -> dict[str, Any]:
    row = svc.be.memory_get(rid) if kind == "memory" else svc.be.decision_get(rid)
    if not row:
        raise ServiceError(f"{kind.capitalize()} #{rid} not found in this project")
    return dict(row)


def preview(svc: Any, kind: str, rid: int) -> list[str]:
    """What would leave the project, line by line."""
    from knowledge_write import origin_label

    row = _local(svc, kind, rid)
    lines = [f"Promote {kind} #{rid} to the shared store — this is what will be copied:"]
    if kind == "memory":
        lines += [f"  type:    {row['type']}", f"  title:   {row['title']}"]
        lines += ["  content:"] + [f"    {ln}" for ln in (row.get("content") or "").splitlines()]
        tags = json.loads(row["tags"]) if row.get("tags") else []
        lines.append(f"  tags:    {', '.join(tags) or '-'}")
    else:
        lines += [f"  decision:  {row['decision']}", f"  rationale: {row.get('rationale') or '-'}"]
    lines.append(f"  origin:  {origin_label()} / {row.get('slug') or '-'}")
    lines.append(_WARNING)
    return lines


def _already_there(conn: Any, table: str, origin: str, slug: str | None) -> bool:
    if not slug:
        return False
    row = conn.execute(
        f"SELECT 1 FROM {table} WHERE origin_project=? AND origin_slug=?", (origin, slug)
    ).fetchone()
    return row is not None


def promote(svc: Any, kind: str, rid: int) -> str:
    """Copy the record into the shared store; refuse a second copy of the same one."""
    from knowledge_write import _open_or_fail, origin_label, write_decision, write_memory

    row = _local(svc, kind, rid)
    table = "memory" if kind == "memory" else "decisions"
    conn = _open_or_fail()
    try:
        if _already_there(conn, table, origin_label(), row.get("slug")):
            raise ServiceError(
                f"{kind.capitalize()} #{rid} is already in the shared store "
                f"({origin_label()} / {row.get('slug')}); not copied twice"
            )
    finally:
        conn.close()
    if kind == "memory":
        tags = json.loads(row["tags"]) if row.get("tags") else None
        return write_memory(row["type"], row["title"], row["content"], tags, row.get("slug"))
    return write_decision(row["decision"], row.get("rationale"), row.get("slug"))
