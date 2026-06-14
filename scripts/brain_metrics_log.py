"""Best-effort logger for brain usage events into the project DB.

Used by `brain_mcp_read.search_with_fallback`, MCP brain tools, and the
brain-related hooks. Writes a row into the project's `brain_events` table
so `tausik metrics` can surface "searches in session" / "hit rate" /
"writes" without holding the brain mirror itself responsible.

Failures are swallowed: brain telemetry never blocks a real search/write.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any


def _resolve_project_db() -> str | None:
    """Find .tausik/tausik.db relative to CLAUDE_PROJECT_DIR or cwd.

    Order: explicit env var first, then current working directory. We do
    NOT fall back to the script directory — that would attach telemetry
    to whatever DB happens to live next to bootstrapped scripts and bypass
    the "no events without an active session" expectation.
    """
    candidates: list[str] = []
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("TAUSIK_PROJECT_DIR")
    if env_dir:
        candidates.append(os.path.join(env_dir, ".tausik", "tausik.db"))
    cwd = os.getcwd()
    candidates.append(os.path.join(cwd, ".tausik", "tausik.db"))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _utcnow_iso() -> str:
    import datetime as _dt

    return _dt.datetime.now(_dt.UTC).isoformat()


def log_brain_event(
    event_type: str,
    *,
    query: str | None = None,
    result_count: int = 0,
    session_id: int | None = None,
) -> bool:
    """Insert one brain_events row. Returns True on success."""
    if event_type not in {"search", "hit", "write", "ignored"}:
        return False
    db = _resolve_project_db()
    if not db:
        return False
    try:
        conn = sqlite3.connect(db, timeout=2.0)
        try:
            if session_id is None:
                cur = conn.execute(
                    "SELECT id FROM sessions WHERE ended_at IS NULL "
                    "ORDER BY id DESC LIMIT 1"
                )
                row = cur.fetchone()
                session_id = row[0] if row else None
            conn.execute(
                "INSERT INTO brain_events"
                "(session_id, event_type, query, result_count, ts) "
                "VALUES(?,?,?,?,?)",
                (session_id, event_type, query, int(result_count), _utcnow_iso()),
            )
            conn.commit()
        finally:
            conn.close()
        return True
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        return False


def read_metrics(session_id: int | None = None) -> dict[str, Any] | None:
    """Compute the same shape backend_crud.brain_event_metrics returns."""
    db = _resolve_project_db()
    if not db:
        return None
    try:
        conn = sqlite3.connect(db, timeout=2.0)
        try:
            if session_id is None:
                cur = conn.execute(
                    "SELECT id FROM sessions WHERE ended_at IS NULL "
                    "ORDER BY id DESC LIMIT 1"
                )
                row = cur.fetchone()
                session_id = row[0] if row else None

            def _c(et: str, in_session: bool) -> int:
                if in_session and session_id is not None:
                    cur = conn.execute(
                        "SELECT COUNT(*) FROM brain_events "
                        "WHERE session_id=? AND event_type=?",
                        (session_id, et),
                    )
                else:
                    cur = conn.execute(
                        "SELECT COUNT(*) FROM brain_events WHERE event_type=?",
                        (et,),
                    )
                return int(cur.fetchone()[0] or 0)

            sess: dict[str, Any] = {
                "searches": _c("search", True),
                "hits": _c("hit", True),
                "writes": _c("write", True),
                "ignored": _c("ignored", True),
            }
            sess["hit_rate_pct"] = (
                round(sess["hits"] / sess["searches"] * 100, 1)
                if sess["searches"]
                else 0.0
            )
            all_time: dict[str, Any] = {
                "searches": _c("search", False),
                "hits": _c("hit", False),
                "writes": _c("write", False),
            }
            all_time["hit_rate_pct"] = (
                round(all_time["hits"] / all_time["searches"] * 100, 1)
                if all_time["searches"]
                else 0.0
            )
            return {"session_id": session_id, "session": sess, "all_time": all_time}
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        return None
