"""Helpers for recording agent-native task metrics on close (SENAR sizing).

Currently houses the single function `record_call_actual`, separated from
service_task.py to keep that file under the project filesize budget.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


def apply_force_capacity_audit(
    be: "SQLiteBackend", slug: str, task: dict[str, Any]
) -> str:
    """Compute + persist force-bypass audit; return user-facing line ('' = no-op)."""
    msg = force_audit_message(be, slug, task)
    if msg:
        be.task_append_notes(slug, msg)
        be.event_add("task", slug, "capacity_force_start", msg)
    return msg


def force_audit_message(be: "SQLiteBackend", slug: str, task: dict[str, Any]) -> str:
    """MED-7: Audit-trail line when `task_start --force` bypasses capacity.

    Empty when the bypass is a no-op (no budget / no session / fits).
    """
    budget = task.get("call_budget")
    if not budget or budget <= 0:
        return ""
    from project_config import DEFAULT_SESSION_CAPACITY_CALLS, load_config

    cap = load_config().get("session_capacity_calls", DEFAULT_SESSION_CAPACITY_CALLS)
    summary = be.session_capacity_summary(cap)
    if summary["session"] is None or budget <= summary["remaining"]:
        return ""
    return (
        f"FORCED start: budget={budget} exceeds remaining "
        f"{summary['remaining']}/{cap} this session"
    )


def check_session_capacity(
    be: "SQLiteBackend", slug: str, task: dict[str, Any]
) -> None:
    """Block task_start if its budget would overshoot the session's call budget."""
    budget = task.get("call_budget")
    if not budget or budget <= 0:
        return
    from project_config import DEFAULT_SESSION_CAPACITY_CALLS, load_config

    cfg = load_config()
    cap = cfg.get("session_capacity_calls", DEFAULT_SESSION_CAPACITY_CALLS)
    summary = be.session_capacity_summary(cap)
    if summary["session"] is None:
        return
    if budget > summary["remaining"]:
        raise ServiceError(
            f"Session capacity gate: '{slug}' budget={budget} exceeds remaining "
            f"{summary['remaining']}/{cap} this session. Split task, delegate to "
            f"subagent, or `tausik session end` and start a fresh session."
        )


def record_call_actual(be: "SQLiteBackend", slug: str, task: dict[str, Any]) -> str:
    """Compute and persist call_actual = events + per-task tool counter.

    Returns a budget-overrun warning string if call_budget is set and
    actual exceeds 1.5× the budget; empty string otherwise. Always clears
    the meta counter so a future re-open starts from zero.
    """
    events_count = be.task_event_count_in_window(slug)
    meta_key = f"tool_calls:{slug}"
    raw_meta = be.meta_get(meta_key)
    try:
        tool_calls = int(raw_meta) if raw_meta else 0
    except (TypeError, ValueError):
        tool_calls = 0
    actual = events_count + tool_calls
    be.task_set_call_actual(slug, actual)
    if raw_meta is not None:
        be.meta_set(meta_key, "0")
    budget = task.get("call_budget")
    if isinstance(budget, int) and budget > 0 and actual > int(budget * 1.5):
        return (
            f"WARNING: call_actual={actual} exceeds 1.5× call_budget={budget} "
            f"for '{slug}'. Re-calibrate budget for similar tasks."
        )
    return ""
