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
    compute_active_seconds,
)
from project_config import DEFAULT_SESSION_MAX_MINUTES, load_config

QueryFn = Callable[..., list[dict[str, Any]]]
Query1Fn = Callable[..., dict[str, Any] | None]


def resolve_idle_threshold(idle_threshold: int | None) -> int:
    """Honour explicit override, otherwise read from config, otherwise default."""
    if idle_threshold is not None:
        return idle_threshold
    cfg = load_config()
    return int(cfg.get("session_idle_threshold_minutes", DEFAULT_IDLE_THRESHOLD_MINUTES))


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


def session_active_seconds(
    be: Any, session_id: int | None = None, idle_threshold: int | None = None
) -> int:
    """Active seconds for a session (current if id is None) — sub-minute precision."""
    if session_id is None:
        current = be.session_current()
        if not current:
            return 0
        session_id = current["id"]
    threshold = resolve_idle_threshold(idle_threshold)
    return compute_active_seconds(be._q, be._q1, session_id, threshold)


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


def session_overrun_warning(
    be: Any,
    max_minutes: int | None = None,
    *,
    effective_limit: int | None = None,
) -> str | None:
    """Session time advisory — a warning when active time exceeds the threshold, else None.

    A signal, not a gate (decision #376, 1.10): nothing refuses work on it; the
    text says so and names where the threshold's basis lives.

    `effective_limit` lets a caller that has ALREADY resolved the limit hand it
    in instead of paying for a second `events_list` scan of the same session.
    `status_view` renders the limit and asks for this warning in one pass, and
    that pass runs on the compact hot path behind `/start` — the path this
    codebase keeps hardening against latency. Omitted, the limit is resolved
    here as before, so every existing caller is unaffected.
    """
    current = be.session_current()
    if not current or not current.get("started_at"):
        return None
    base = max_minutes or DEFAULT_SESSION_MAX_MINUTES
    limit = (
        effective_limit
        if effective_limit is not None
        else effective_session_limit(be, current["id"], base)
    )
    if limit <= 0:
        return None  # a threshold of 0 switches the signal off (1.10)
    active = session_active_minutes(be, current["id"])
    if active <= limit:
        return None
    try:
        from session_pressure import note_crossing

        note_crossing(be, current["id"], active, limit)  # §9.4(d): recorded once
    except Exception:  # noqa: BLE001 — recording the crossing must never cost the advice
        pass
    wall = session_wall_minutes(be, current["id"])
    return (
        f"Session #{current['id']} has {active} min active ({wall} min wall) — "
        f"over the {limit}-min advisory threshold. Context pressure is a signal, "
        f"not a gate: save state with /checkpoint or hand off with /end; the basis "
        f"for the threshold is docs/ru/session-active-time.md."
    )


# SENAR Rule 9.5 cadence, counted in CLOSURES since 1.10 (decision #376). It
# counted sessions: the last dependency of a quality rule on a ritual — a rule
# "every 3 sessions" could be dodged or over-performed by opening and closing
# sessions, and without sessions it never arrived at all. Basis for the default
# (SENAR 1.5 §9.4(c)): the old cadence was 3 sessions, and the measured
# throughput is 5.72 closures per session (tausik metrics, session #266):
# 3 x 5.72 = 17. Override with `audit_every_closures` in .tausik/config.json.
DEFAULT_AUDIT_EVERY_CLOSURES = 17


def audit_mark_time(be: Any) -> str | None:
    """When the last audit was marked, or None when never.

    `last_audit_at` since 1.10; before that only `last_audit_session` was kept,
    and its session's start is the moment — a mark made under the old clock is
    read, not reset to zero.
    """
    at = be.meta_get("last_audit_at")
    if at:
        return str(at)
    try:
        sid = int(be.meta_get("last_audit_session") or 0)
    except (ValueError, TypeError):
        return None
    if not sid:
        return None
    row = be.session_last_handoff(sid)  # the by-id form returns the session row
    return str(row["started_at"]) if row and row.get("started_at") else None


def audit_closures_since(be: Any) -> int | None:
    """Tasks closed after the last audit mark; None when no audit was ever marked."""
    mark = audit_mark_time(be)
    if mark is None:
        return None
    return sum(
        1
        for t in be.task_list(status="done") or []
        if t.get("completed_at") and str(t["completed_at"]) > mark
    )


def audit_overdue_closures(be: Any, every: int = DEFAULT_AUDIT_EVERY_CLOSURES) -> int:
    """SENAR Rule 9.5: closures since the last audit when at or over `every`, else 0."""
    n = audit_closures_since(be)
    return n if n is not None and n >= every else 0
