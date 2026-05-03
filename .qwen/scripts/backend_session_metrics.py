"""Session active-time metrics — gap-based duration vs wall clock.

Wall-clock session duration over-counts AFK periods. Active time sums
intervals between consecutive `events` rows where the gap is below an
idle threshold (default 10 minutes). Used by:
  - `tausik status` to display "X min active / Y wall clock"
  - `session_cleanup_check` hook to enforce SENAR Rule 9.2 (180-min limit)
  - `tausik session recompute` for retro analysis

Free functions over a query callable so this module stays out of the
backend_queries 400-line gate.
"""

from __future__ import annotations

from typing import Any, Callable

QueryFn = Callable[..., list[dict[str, Any]]]
Query1Fn = Callable[..., dict[str, Any] | None]

DEFAULT_IDLE_THRESHOLD_MINUTES = 10


def compute_active_minutes(
    q: QueryFn,
    q1: Query1Fn,
    session_id: int,
    idle_threshold_minutes: int = DEFAULT_IDLE_THRESHOLD_MINUTES,
) -> int:
    """Sum minutes between consecutive `events` for the session, excluding gaps ≥ threshold.

    Returns 0 for sessions with 0 or 1 event. Uses SQL window functions
    (sqlite ≥ 3.25) — single roundtrip, no Python iteration.

    Args:
        q: backend's _q method (returns list[dict] of rows)
        q1: backend's _q1 method (returns single row or None)
        session_id: target session row id from `sessions` table
        idle_threshold_minutes: gaps ≥ this are excluded (treated as AFK)

    Returns:
        active minutes (rounded int)
    """
    if idle_threshold_minutes <= 0:
        return 0
    sess = q1(
        "SELECT started_at, ended_at FROM sessions WHERE id = ?",
        (session_id,),
    )
    if not sess or not sess.get("started_at"):
        return 0
    started = sess["started_at"]
    ended = sess.get("ended_at")
    row = q1(
        """
        WITH ordered AS (
            SELECT created_at,
                   LAG(created_at) OVER (ORDER BY created_at) AS prev_at
            FROM events
            WHERE created_at >= ?
              AND created_at <= COALESCE(?, strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        )
        SELECT COALESCE(SUM(
            CASE
                WHEN prev_at IS NULL THEN 0
                WHEN (julianday(created_at) - julianday(prev_at)) * 1440 >= ? THEN 0
                ELSE (julianday(created_at) - julianday(prev_at)) * 1440
            END
        ), 0) AS active_minutes
        FROM ordered
        """,
        (started, ended, idle_threshold_minutes),
    )
    if not row:
        return 0
    return int(round(row.get("active_minutes") or 0))


def recompute_all_sessions(
    q: QueryFn,
    q1: Query1Fn,
    idle_threshold_minutes: int = DEFAULT_IDLE_THRESHOLD_MINUTES,
) -> list[dict[str, Any]]:
    """Compute active vs wall-clock minutes for every session, oldest first.

    Returns rows with: id, started_at, ended_at, wall_minutes, active_minutes,
    afk_pct (1 - active/wall, or None if wall == 0).
    """
    sessions = q("SELECT id, started_at, ended_at FROM sessions ORDER BY id ASC")
    out: list[dict[str, Any]] = []
    for s in sessions:
        active = compute_active_minutes(q, q1, s["id"], idle_threshold_minutes)
        wall_row = q1(
            "SELECT (julianday(COALESCE(?, datetime('now'))) - julianday(?)) * 1440 AS wall",
            (s.get("ended_at"), s["started_at"]),
        )
        wall = int(round(wall_row.get("wall") or 0)) if wall_row else 0
        afk_pct = round(1 - active / wall, 3) if wall > 0 else None
        out.append(
            {
                "id": s["id"],
                "started_at": s["started_at"],
                "ended_at": s.get("ended_at"),
                "wall_minutes": wall,
                "active_minutes": active,
                "afk_pct": afk_pct,
            }
        )
    return out
