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
import json
import os
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


def _json_list(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value:
        return []
    try:
        parsed = json.loads(value)
    except ValueError:
        return []
    return parsed if isinstance(parsed, list) else []


def _resume_task(be: Any, task: dict[str, Any]) -> dict[str, Any]:
    """Recorded task state a new agent needs before it can safely continue.

    This is intentionally a projection of fields already in the task row and
    journal.  It does not infer that an unchecked plan item was completed.
    """
    plan = _json_list(task.get("plan"))
    if task.get("plan") and (not plan or not all(isinstance(step, dict) for step in plan)):
        plan_state: dict[str, Any] = {"state": "unreadable"}
    else:
        plan_state = {
            "state": "recorded",
            "completed": [i + 1 for i, step in enumerate(plan) if step.get("done")],
            "remaining": [
                {"number": i + 1, "step": step.get("step", "")}
                for i, step in enumerate(plan)
                if not step.get("done")
            ],
        }
    return {
        "slug": task["slug"],
        "last_log": _last_log(be, task["slug"]),
        "goal": task.get("goal") or "",
        "acceptance_criteria": task.get("acceptance_criteria") or "",
        "plan": plan_state,
        "unresolved_risk": {
            "status": task.get("status"),
            "blocked_at": task.get("blocked_at"),
            "risk_score": task.get("risk_score"),
            "risk": task.get("risk_json"),
        },
        "relevant_files": _json_list(task.get("relevant_files")),
    }


def _working_tree(tausik_dir: str | None) -> tuple[str | None, dict[str, Any]]:
    """A read-only, explicit snapshot of uncommitted files for resumption."""
    if not tausik_dir:
        return None, {"state": "unavailable", "reason": "project directory unknown"}
    root = os.path.dirname(os.path.abspath(tausik_dir))
    try:
        from verify_git_diff import uncommitted_changes

        changed = uncommitted_changes(root=root, untracked="all")
    except Exception as exc:  # noqa: BLE001 -- handoff reports a failed observation
        return root, {"state": "unavailable", "reason": type(exc).__name__}
    if changed is None:
        return root, {"state": "unavailable", "reason": "git status unavailable"}
    return root, {"state": "recorded", "modified_uncommitted": changed}


def _receipt_state(run: dict[str, Any], task: dict[str, Any], root: str | None) -> str:
    """Whether a green receipt still matches the files it claims to cover."""
    if run.get("exit_code") != 0:
        return "red"
    try:
        from verify_files_hash import compute_files_hash
        from verify_recent_lookup import _extract_files_from_cache_command

        files = _extract_files_from_cache_command(str(run.get("command") or ""))
        if not files:
            files = [str(p) for p in _json_list(task.get("relevant_files")) if isinstance(p, str)]
        if not files:
            return "unverifiable"
        if root is None:
            return "unknown"
        return (
            "current" if run.get("files_hash") == compute_files_hash(files, root=root) else "stale"
        )
    except Exception:  # noqa: BLE001 -- evidence must degrade visibly, never turn green
        return "unknown"


SLOW_LANE_FILE = "slow_lane.json"


def slow_lane(tausik_dir: str | None, start: datetime) -> str | None:
    """The slow lane's colour as the handoff states it, or None where no lane is recorded.

    A project whose test suite writes `.tausik/slow_lane.json` (this repository's
    conftest does) has a lane the default run deselects and CI may not reach. For such
    a project silence is the failure mode: a lane not run in this session, or run red,
    is said in words. A project that records nothing gets nothing — it has no such lane.
    """
    import json
    import os

    if not tausik_dir:
        return None
    path = os.path.join(tausik_dir, SLOW_LANE_FILE)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        ran_at = _ts(rec.get("ran_at"))
        failed, passed = int(rec.get("failed", 0)), int(rec.get("passed", 0))
    except (OSError, ValueError, TypeError, AttributeError) as e:
        return f"UNREADABLE {path}: {type(e).__name__} — run `pytest -q -m slow`"
    if ran_at is None or ran_at < start:
        return f"NOT RUN this session (last {rec.get('ran_at')}) — run `pytest -q -m slow`"
    if failed or rec.get("exit_status") not in (0, None):
        return f"RED: {failed} failed, {passed} passed at {rec.get('ran_at')}"
    return f"green: {passed} passed at {rec.get('ran_at')}"


def generate(be: Any, session: dict[str, Any], tausik_dir: str | None = None) -> dict[str, Any]:
    """The handoff of `session`, projected from the records of its window."""
    start, end = _window(session)
    root, working_tree = _working_tree(tausik_dir)
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
            # A completed task belongs to this session's narrative, whereas an
            # active/review task needs its latest proof across a session boundary:
            # the replacement must not lose a still-current receipt merely
            # because it was created before the new agent started.
            if t.get("status") in ("active", "review") or _in(run.get("ran_at"), start, end):
                receipts.append(
                    {
                        "task": t["slug"],
                        "run": run["id"],
                        "passed": run.get("exit_code") == 0,
                        "state": _receipt_state(run, t, root),
                    }
                )

    # A replacement session needs the decisions attached to work that remains
    # active, even if that decision was recorded in the preceding session.
    # Project-wide decisions remain bounded by this session's window: widening
    # that list would leak unrelated history into a handoff.
    active_slugs = {str(task["slug"]) for task in active}
    decisions = [
        f"#{d['id']} {str(d.get('decision') or '')[:160]}"
        for d in be.decision_list(_LIMIT)
        if _in(d.get("created_at"), start, end) or str(d.get("task_slug") or "") in active_slugs
    ]
    memory = [m for m in be.memory_list(n=_LIMIT) if _in(m.get("created_at"), start, end)]
    exploration = be.exploration_current()

    out: dict[str, Any] = {
        "generated_from": "journal",
        "window": {"start": session.get("started_at"), "end": session.get("ended_at")},
        "completed": [f"{t['slug']}: {t.get('title', '')}"[:200] for t in done],
        "in_progress": [_resume_task(be, t) for t in active],
        "in_review": [t["slug"] for t in review],
        "blocked": [t["slug"] for t in blocked],
        "working_tree": working_tree,
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
    lane = slow_lane(tausik_dir, start)
    if lane is not None:
        out["slow_lane"] = lane
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
