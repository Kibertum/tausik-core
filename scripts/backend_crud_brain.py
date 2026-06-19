"""Brain usage CRUD helpers (v22, r14-brain-metrics).

Lives outside backend_crud.py so the file stays under the 400-line gate.
Mixed into the SQLiteBackend at import time via attribute injection in
backend_crud.

Exposed as functions taking the backend instance as first argument so
both an explicit `be.brain_event_record(...)` style and a future migration
to an instance method dispatch is straightforward.
"""

from __future__ import annotations

from typing import Any, cast

from tausik_utils import utcnow_iso

_VALID_TYPES = {"search", "hit", "write", "ignored"}


def brain_event_record(
    be: Any,
    event_type: str,
    query: str | None = None,
    result_count: int = 0,
    session_id: int | None = None,
) -> int:
    if event_type not in _VALID_TYPES:
        raise ValueError(f"unknown brain event type: {event_type}")
    if session_id is None:
        cur = be._q1(
            "SELECT id FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
        )
        session_id = (cur or {}).get("id")
    return cast(
        int,
        be._ins(
            "INSERT INTO brain_events(session_id, event_type, query, result_count, ts) "
            "VALUES(?,?,?,?,?)",
            (session_id, event_type, query, int(result_count), utcnow_iso()),
        ),
    )


def brain_event_metrics(be: Any, session_id: int | None = None) -> dict[str, Any]:
    if session_id is None:
        cur = be._q1(
            "SELECT id FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
        )
        session_id = (cur or {}).get("id")

    def _count(et: str, scope: str) -> int:
        if scope == "session" and session_id is not None:
            row = be._q1(
                "SELECT COUNT(*) AS c FROM brain_events "
                "WHERE session_id=? AND event_type=?",
                (session_id, et),
            )
        else:
            row = be._q1(
                "SELECT COUNT(*) AS c FROM brain_events WHERE event_type=?",
                (et,),
            )
        return int((row or {}).get("c") or 0)

    sess_searches = _count("search", "session")
    sess_hits = _count("hit", "session")
    sess_writes = _count("write", "session")
    sess_ignored = _count("ignored", "session")
    all_searches = _count("search", "all")
    all_hits = _count("hit", "all")
    all_writes = _count("write", "all")
    return {
        "session_id": session_id,
        "session": {
            "searches": sess_searches,
            "hits": sess_hits,
            "writes": sess_writes,
            "ignored": sess_ignored,
            "hit_rate_pct": (
                round(sess_hits / sess_searches * 100, 1) if sess_searches else 0.0
            ),
        },
        "all_time": {
            "searches": all_searches,
            "hits": all_hits,
            "writes": all_writes,
            "hit_rate_pct": (
                round(all_hits / all_searches * 100, 1) if all_searches else 0.0
            ),
        },
    }
