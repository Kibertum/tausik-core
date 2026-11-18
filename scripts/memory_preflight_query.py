"""Bounded indexed conflict queries for the protected memory-preflight boundary."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
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

# Underscore keeps protected_kind atoms (remote_operation) intact. Splitting on
# "_" turned "remote_operation" into "remote"+"operation" and flooded FTS OR
# matches across unrelated dead_ends (MEMORY_CONFLICT_OVERFLOW under dogfooding).
_WORD = re.compile(r"[A-Za-zА-Яа-яЁё0-9_]{3,}")
_TERM_STOPWORDS = frozenset(
    {
        "and",
        "are",
        "bash",
        "command",
        "conclusion",
        "displaytitle",
        "encoding",
        "false",
        "for",
        "from",
        "headsha",
        "input",
        "into",
        "json",
        "literalpath",
        "null",
        "only",
        "output",
        "powershell",
        "shell",
        "status",
        "string",
        "that",
        "the",
        "this",
        "tool",
        "tool_input",
        "tool_name",
        "true",
        "url",
        "utf",
        "was",
        "were",
        "with",
    }
)


def _command_corpus(kind: str, command: str) -> str:
    if kind in {"commit", "push", "remote_operation", "release_shell"}:
        # Kind alone is the conflict key: OR-ing "git" / commit-message prose /
        # "gh workflow run release-qualification…" / "git tag vX.Y.Z" floods
        # historical release/CI/git dead_ends and trips MEMORY_CONFLICT_OVERFLOW
        # on a normal tip commit, exact-SHA qual trigger, or local release tag
        # (dogfooding blocker).
        return kind
    return f"{kind} {command}"


def preflight_terms(tool_name: str, tool_input: Mapping[str, Any], kind: str) -> list[str]:
    """Build FTS terms from the protected action without shell/JSON noise."""
    # Prefer the observed command string over the full tool_input envelope so
    # keys like "status"/"url" from gh --json do not become conflict terms.
    payload = tool_input.get("command")
    if isinstance(payload, str) and payload.strip():
        corpus = _command_corpus(kind, payload)
    else:
        encoded = json.dumps(
            dict(tool_input), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        )
        corpus = f"{kind} {tool_name} {encoded}"
    words = _WORD.findall(corpus.lower())
    seen: set[str] = set()
    terms: list[str] = []
    for word in words:
        if word in _TERM_STOPWORDS or word in seen:
            continue
        # Drop pure numeric tokens (run ids, SHA fragments) — they never name a policy.
        if word.isdigit():
            continue
        seen.add(word)
        terms.append(word)
        if len(terms) == 24:
            break
    return terms


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


__all__ = [
    "fts_or",
    "has_quarantined_conflict",
    "live_conflict_count",
    "preflight_terms",
]
