"""Bounded indexed conflict queries for the protected memory-preflight boundary."""

from __future__ import annotations

from typing import Any


def fts_or(terms: list[str]) -> str:
    return " OR ".join(f'"{term}"' for term in terms)


_LIVE_CONFLICT = (
    "AND NOT EXISTS ("
    "SELECT 1 FROM memory_edges e "
    "LEFT JOIN memory sm ON (coalesce(e.source_type,'memory')='memory' "
    "AND sm.id=e.source_id AND sm.archived_at IS NULL) "
    "LEFT JOIN decisions sd ON (e.source_type='decision' AND sd.id=e.source_id) "
    "WHERE coalesce(e.target_type,'memory')='memory' AND e.target_id=m.id "
    "AND e.relation='supersedes' AND e.valid_to IS NULL "
    "AND (sm.id IS NOT NULL OR sd.id IS NOT NULL))"
)


def has_quarantined_conflict(be: Any, terms: list[str]) -> bool:
    """Check the complete live conflict corpus without materializing it."""
    row = be._q1(
        "SELECT m.id FROM memory m JOIN fts_memory f ON m.id=f.rowid "
        "WHERE fts_memory MATCH ? AND m.archived_at IS NULL "
        "AND (m.type='dead_end' OR m.tags LIKE '%policy:active%') "
        "AND (lower(coalesce(m.title,'') || ' ' || coalesce(m.content,'') || ' ' || "
        "coalesce(m.tags,'')) LIKE '%ignore%previous%instructions%' "
        "OR lower(coalesce(m.title,'') || ' ' || coalesce(m.content,'') || ' ' || "
        "coalesce(m.tags,'')) LIKE '%ignore%prior%instructions%' "
        "OR lower(coalesce(m.title,'') || ' ' || coalesce(m.content,'') || ' ' || "
        "coalesce(m.tags,'')) LIKE '%disregard%previous%instructions%' "
        "OR lower(coalesce(m.title,'') || ' ' || coalesce(m.content,'') || ' ' || "
        "coalesce(m.tags,'')) LIKE '%disregard%prior%instructions%' "
        "OR lower(coalesce(m.title,'') || ' ' || coalesce(m.content,'') || ' ' || "
        "coalesce(m.tags,'')) LIKE '%system prompt%') " + _LIVE_CONFLICT + " LIMIT 1",
        (fts_or(terms),),
    )
    return row is not None


def live_conflict_count(be: Any, terms: list[str]) -> int:
    row = be._q1(
        "SELECT COUNT(*) AS count FROM memory m JOIN fts_memory f ON m.id=f.rowid "
        "WHERE fts_memory MATCH ? AND m.archived_at IS NULL "
        "AND (m.type='dead_end' OR m.tags LIKE '%policy:active%') " + _LIVE_CONFLICT,
        (fts_or(terms),),
    )
    return int(row["count"]) if row is not None else 0


__all__ = ["fts_or", "has_quarantined_conflict", "live_conflict_count"]
