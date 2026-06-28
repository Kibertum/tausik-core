"""Session active-time metrics — bounded inter-tool-call deltas.

Wall-clock session duration over-counts AFK periods. Active time sums
clipped intervals between consecutive `events` rows: each gap is
``min(delta, idle_threshold)`` so a long AFK still credits one threshold
worth of "the agent paid attention right before pausing", but no more.
Used by:
  - `tausik status` to display "X min active / Y wall clock"
  - `session_cleanup_check` hook to enforce SENAR Rule 9.2 (180-min limit)
  - `tausik session recompute` for retro analysis

v14b-session-active-time changed the gap rule from "exclude" (gap ≥
threshold → 0 contribution) to "clip" (gap ≥ threshold → threshold
contribution). The clipped variant matches SENAR's bounded-delta intent
and never under-counts a session that interleaves real work with AFK
breaks: every break still costs ``threshold`` seconds against the
180-minute limit.

Free functions over a query callable so this module stays out of the
backend_queries 400-line gate.
"""

from __future__ import annotations

from typing import Any, Callable

QueryFn = Callable[..., list[dict[str, Any]]]
Query1Fn = Callable[..., dict[str, Any] | None]

DEFAULT_IDLE_THRESHOLD_MINUTES = 10
DEFAULT_IDLE_THRESHOLD_SECONDS = DEFAULT_IDLE_THRESHOLD_MINUTES * 60


def compute_active_seconds(
    q: QueryFn,
    q1: Query1Fn,
    session_id: int,
    idle_threshold_minutes: int = DEFAULT_IDLE_THRESHOLD_MINUTES,
) -> int:
    """Sum bounded seconds between consecutive `events` rows for the session.

    Each inter-event gap contributes ``min(delta, idle_threshold)`` seconds
    (clip semantics, v14b-session-active-time). Sessions with 0 or 1 event
    return 0. Uses SQL window functions (sqlite ≥ 3.25) — single roundtrip.

    Negative scenarios (defensive — best-effort, never raises):
        - session has no events → 0
        - corrupt timestamp (NULL prev_at, equal timestamps, non-monotonic)
          → contributes 0 for that pair, returns sum over valid pairs

    Args:
        q: backend's _q method (returns list[dict] of rows)
        q1: backend's _q1 method (returns single row or None)
        session_id: target session row id from `sessions` table
        idle_threshold_minutes: gaps are clipped to this many minutes

    Returns:
        active seconds (int, rounded)
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
    threshold_seconds = idle_threshold_minutes * 60
    row = q1(
        """
        WITH ordered AS (
            SELECT created_at,
                   LAG(created_at) OVER (ORDER BY created_at) AS prev_at
            FROM events
            WHERE created_at >= ?
              AND created_at <= COALESCE(?, strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        ),
        deltas AS (
            SELECT CASE
                WHEN prev_at IS NULL THEN 0
                WHEN julianday(created_at) IS NULL OR julianday(prev_at) IS NULL THEN 0
                WHEN (julianday(created_at) - julianday(prev_at)) * 86400 < 0 THEN 0
                WHEN (julianday(created_at) - julianday(prev_at)) * 86400 >= ? THEN ?
                ELSE (julianday(created_at) - julianday(prev_at)) * 86400
            END AS gap_seconds
            FROM ordered
        )
        SELECT COALESCE(SUM(gap_seconds), 0) AS active_seconds
        FROM deltas
        """,
        (started, ended, threshold_seconds, threshold_seconds),
    )
    if not row:
        return 0
    return int(round(row.get("active_seconds") or 0))


def compute_active_minutes(
    q: QueryFn,
    q1: Query1Fn,
    session_id: int,
    idle_threshold_minutes: int = DEFAULT_IDLE_THRESHOLD_MINUTES,
) -> int:
    """Active minutes for the session — convenience wrapper over compute_active_seconds.

    Returns 0 for sessions with 0 or 1 event. Each gap contributes
    ``min(delta, idle_threshold)`` (clip semantics, v14b-session-active-time);
    long AFK gaps still count for ``idle_threshold`` minutes against the
    Rule 9.2 limit.

    Args:
        q: backend's _q method (returns list[dict] of rows)
        q1: backend's _q1 method (returns single row or None)
        session_id: target session row id from `sessions` table
        idle_threshold_minutes: gaps are clipped to this many minutes

    Returns:
        active minutes (rounded int)
    """
    seconds = compute_active_seconds(q, q1, session_id, idle_threshold_minutes)
    return int(round(seconds / 60))


def recompute_all_sessions(
    q: QueryFn,
    q1: Query1Fn,
    idle_threshold_minutes: int = DEFAULT_IDLE_THRESHOLD_MINUTES,
) -> list[dict[str, Any]]:
    """Compute active vs wall-clock minutes for every session, oldest first.

    Returns rows with: id, started_at, ended_at, wall_minutes, active_minutes,
    active_seconds, afk_pct (1 - active/wall, or None if wall == 0).
    """
    sessions = q("SELECT id, started_at, ended_at FROM sessions ORDER BY id ASC")
    out: list[dict[str, Any]] = []
    for s in sessions:
        active_seconds = compute_active_seconds(q, q1, s["id"], idle_threshold_minutes)
        active = int(round(active_seconds / 60))
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
                "active_seconds": active_seconds,
                "afk_pct": afk_pct,
            }
        )
    return out
