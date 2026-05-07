"""Memory hygiene operations (archive + dedupe).

Extracted from service_knowledge.py to keep that file under the 400-line gate.
Mirrors the service_knowledge_aggregates.py split pattern: thin delegators
in KnowledgeMixin, real logic here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


def archive_memory(be: SQLiteBackend, before: str, confirm: bool = False) -> dict[str, Any]:
    """Soft-archive memory rows whose ``created_at`` is older than ``before``.

    ``before`` is a duration string like ``"90d"`` / ``"12w"`` / ``"2m"`` /
    ``"1y"``. Without ``confirm=True`` returns a dry-run preview; with
    ``confirm=True`` the matching rows get a ``archived_at`` timestamp
    (idempotent — already-archived rows are skipped).
    """
    from memory_cleanup import parse_duration_to_days

    try:
        days = parse_duration_to_days(before)
    except ValueError as e:
        raise ServiceError(str(e)) from e
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if confirm:
        archived = be.memory_archive_apply(cutoff)
        return {"archived": archived, "before_days": days, "cutoff": cutoff, "applied": True}
    candidates = be.memory_archive_candidates(cutoff)
    return {
        "archived": 0,
        "candidates": candidates,
        "before_days": days,
        "cutoff": cutoff,
        "applied": False,
    }


def dedupe_memory(be: SQLiteBackend, threshold: float = 0.85, n: int = 200) -> list[dict[str, Any]]:
    """Suggest memory pairs with similarity ≥ ``threshold`` (0 < t ≤ 1).

    Compares unarchived rows in pairs (same ``type`` only) using
    SequenceMatcher over ``title || content``. Returns suggestions sorted
    by descending ratio. Read-only — does not delete or merge.
    """
    from memory_cleanup import find_dedupe_candidates

    if not (0.0 < threshold <= 1.0):
        raise ServiceError(f"threshold must be in (0, 1], got {threshold!r}")
    rows = be.memory_list(n=n, include_archived=False)
    return find_dedupe_candidates(rows, threshold)
