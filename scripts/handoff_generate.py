"""The handoff is generated from the journal, not composed by the agent (1.10, story E).

SENAR 1.5 §3.45: the handoff is the only route by which one session's context
reaches the next, and §7.3 requires it of every session. Until 1.10 a handoff
existed only when the agent ran `/checkpoint` or `/end` and hand-wrote a JSON —
an autonomous agent closed by its host wrote none (sessions #252–#260 closed
without one). Everything a handoff says is already recorded: task logs,
statuses, verify receipts, decisions, memory, dead ends, the open exploration.
This module projects those records over the session's window.

WHAT IS GENERATED AND WHAT IS AUTHORED. Generated fields describe what the
records say. `next_steps`, `warnings` and per-task `state` are judgement: they
are accepted ON TOP, listed in `authored_fields`, and nothing generated
overwrites them.

TWO HONESTY RULES, each held by a test:
  * a task is listed as completed only when its status IS done — a task in
    review is "in review", not finished;
  * a window with no records says so in words (`empty`), it is never an empty
    object and never an invented step.

Reads go through existing backend methods only: SQLiteBackend's public
surface is a ratchet (class_surface gate), and a generator does not earn a
method of its own.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

EMPTY_WINDOW = "в окне сессии записей нет"
_AUTHORED = ("next_steps", "warnings")
_LIMIT = 50
_RECORDED = (
    "completed",
    "in_progress",
    "in_review",
    "verify",
    "decisions",
    "knowledge",
    "dead_ends",
)


def _ts(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _in(value: object, start: datetime, end: datetime) -> bool:
    t = _ts(value)
    return t is not None and start <= t <= end


def _window(session: dict[str, Any]) -> tuple[datetime, datetime]:
    start = _ts(session.get("started_at")) or datetime.min.replace(tzinfo=timezone.utc)
    end = _ts(session.get("ended_at")) or datetime.now(timezone.utc)
    return start, end


def _last_log(be: Any, slug: str) -> str:
    logs = be.task_log_list(slug)
    return str(logs[-1]["message"])[:300] if logs else ""


def generate(be: Any, session: dict[str, Any]) -> dict[str, Any]:
    """The handoff of `session`, projected from the records of its window."""
    start, end = _window(session)
    tasks = be.task_list() or []
    done = [
        t for t in tasks if t.get("status") == "done" and _in(t.get("completed_at"), start, end)
    ]
    active = [t for t in tasks if t.get("status") == "active"]
    review = [t for t in tasks if t.get("status") == "review"]
    blocked = [t for t in tasks if t.get("status") == "blocked"]

    receipts: list[dict[str, Any]] = []
    for t in done + active + review:
        for run in be.verification_runs_for_task(t["slug"]):
            if _in(run.get("ran_at"), start, end):
                receipts.append(
                    {"task": t["slug"], "run": run["id"], "passed": run.get("exit_code") == 0}
                )

    decisions = [
        f"#{d['id']} {str(d.get('decision') or '')[:160]}"
        for d in be.decision_list(_LIMIT)
        if _in(d.get("created_at"), start, end)
    ]
    memory = [m for m in be.memory_list(n=_LIMIT) if _in(m.get("created_at"), start, end)]
    exploration = be.exploration_current()

    out: dict[str, Any] = {
        "generated_from": "journal",
        "window": {"start": session.get("started_at"), "end": session.get("ended_at")},
        "completed": [f"{t['slug']}: {t.get('title', '')}"[:200] for t in done],
        "in_progress": [{"slug": t["slug"], "last_log": _last_log(be, t["slug"])} for t in active],
        "in_review": [t["slug"] for t in review],
        "blocked": [t["slug"] for t in blocked],
        "verify": receipts[-_LIMIT:],
        "decisions": decisions,
        "knowledge": [
            f"#{m['id']} {m.get('title', '')}" for m in memory if m.get("type") != "dead_end"
        ],
        "dead_ends": [
            f"#{m['id']} {m.get('title', '')}" for m in memory if m.get("type") == "dead_end"
        ],
    }
    if exploration:
        out["exploration"] = {"id": exploration.get("id"), "title": exploration.get("title")}
    if not any(out[k] for k in _RECORDED) and not exploration:
        out["empty"] = EMPTY_WINDOW
    return out


def merge_authored(generated: dict[str, Any], authored: dict[str, Any] | None) -> dict[str, Any]:
    """Authored judgement on top of the generated record, marked as authored."""
    result = dict(generated)
    if not authored:
        return result
    marked: list[str] = []
    for key in _AUTHORED:
        if authored.get(key):
            result[key] = authored[key]
            marked.append(key)
    states = {
        item.get("slug"): item.get("state")
        for item in authored.get("in_progress") or []
        if isinstance(item, dict) and item.get("slug") and item.get("state")
    }
    if states:
        result["in_progress"] = [
            {**item, "state": states[item["slug"]]} if item["slug"] in states else item
            for item in result.get("in_progress", [])
        ]
        marked.append("in_progress[].state")
    # Authored keys the generator does not produce (summary, key_files, …) sit
    # on top as before. Keys it DOES produce (completed, verify, …) are what the
    # records say; the authored version is kept beside them under `authored`
    # rather than silently replacing a projection with a recollection.
    extra = {k: v for k, v in authored.items() if k not in (*_AUTHORED, "in_progress")}
    colliding = {k: v for k, v in extra.items() if k in generated}
    for k, v in extra.items():
        if k not in generated:
            result[k] = v
            marked.append(k)
    if colliding:
        result["authored"] = colliding
        marked.append("authored")
    if marked:
        result["authored_fields"] = marked
    return result
