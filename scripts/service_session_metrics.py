"""Session active-time service helpers — service-layer wrappers.

Service-layer thin wrappers over backend_session_metrics: load config for
default threshold, resolve current session id, format wall-time. Lives in
its own module so SessionMixin in project_service stays under the 400-line
filesize gate.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from backend_session_metrics import (
    DEFAULT_IDLE_THRESHOLD_MINUTES,
    compute_active_minutes,
)
from project_config import DEFAULT_SESSION_MAX_MINUTES, load_config

QueryFn = Callable[..., list[dict[str, Any]]]
Query1Fn = Callable[..., dict[str, Any] | None]


def resolve_idle_threshold(idle_threshold: int | None) -> int:
    """Honour explicit override, otherwise read from config, otherwise default."""
    if idle_threshold is not None:
        return idle_threshold
    cfg = load_config()
    return int(
        cfg.get("session_idle_threshold_minutes", DEFAULT_IDLE_THRESHOLD_MINUTES)
    )


def session_active_minutes(
    be: Any, session_id: int | None = None, idle_threshold: int | None = None
) -> int:
    """Active minutes for a session (current if id is None)."""
    if session_id is None:
        current = be.session_current()
        if not current:
            return 0
        session_id = current["id"]
    threshold = resolve_idle_threshold(idle_threshold)
    return compute_active_minutes(be._q, be._q1, session_id, threshold)


def session_wall_minutes(be: Any, session_id: int | None = None) -> int:
    """Wall-clock minutes since session start (current if id is None)."""
    if session_id is None:
        current = be.session_current()
        if not current:
            return 0
        started = current.get("started_at")
        ended = current.get("ended_at")
    else:
        row = be._q1(
            "SELECT started_at, ended_at FROM sessions WHERE id = ?",
            (session_id,),
        )
        if not row:
            return 0
        started = row.get("started_at")
        ended = row.get("ended_at")
    if not started:
        return 0
    try:
        start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        end_dt = (
            datetime.fromisoformat(ended.replace("Z", "+00:00"))
            if ended
            else datetime.now(timezone.utc)
        )
        # round to match compute_active_minutes — avoids negative afk_pct on
        # tiny sessions where active rounds up but wall truncates down.
        return max(0, int(round((end_dt - start_dt).total_seconds() / 60)))
    except (ValueError, TypeError):
        return 0


def effective_session_limit(be: Any, session_id: int, base_limit: int) -> int:
    """Resolve the effective limit including session_extend events."""
    limit = base_limit
    for ev in be.events_list(entity_type="session", entity_id=str(session_id)):
        if ev.get("action") != "session_extend":
            continue
        try:
            data = json.loads(ev.get("details", "{}"))
            limit = max(limit, data.get("new_limit", limit))
        except (ValueError, TypeError):
            pass
    return limit


def session_overrun_warning(be: Any, max_minutes: int | None = None) -> str | None:
    """SENAR Rule 9.2 — warn if active time exceeds limit. Returns msg or None."""
    current = be.session_current()
    if not current or not current.get("started_at"):
        return None
    base = max_minutes or DEFAULT_SESSION_MAX_MINUTES
    limit = effective_session_limit(be, current["id"], base)
    active = session_active_minutes(be, current["id"])
    if active <= limit:
        return None
    wall = session_wall_minutes(be, current["id"])
    return (
        f"Session #{current['id']} has {active} min active "
        f"({wall} min wall) — over {limit}-min limit. Consider ending with /end."
    )
