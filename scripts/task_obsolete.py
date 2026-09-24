"""Close a task as OBSOLETE: the finding was resolved by time, not shipped.

a-task-cannot-be-closed-as-obsolete (1.10, decision #390). The lifecycle had
three exits and none fit a task whose premise stopped being true: `task done`
demands per-criterion evidence and QG-2, `task delete` erases the record and its
journal, and leaving it open lies to the roadmap. In session #265 the honest
close of four such tasks took writing criteria after the fact and a hard delete.

An obsolete close keeps the record (status `done`, so everything that asks "is
it still open?" — dependencies, story/epic cascade, the roadmap — answers no)
and marks it `resolution = 'obsolete'` with the reason, so everything that asks
"was it delivered?" — FPSR, DER, cycle/lead time, calibration, defect escape —
can leave it out. A closed finding is not a shipped one.

A module function, not a service method: ProjectService is on the class-surface
ratchet and may not grow a public member.
"""

from __future__ import annotations

from typing import Any

from ac_placeholder import substance
from tausik_utils import ServiceError, utcnow_iso

OBSOLETE = "obsolete"
MIN_REASON_CHARS = 10
MIN_REASON_WORDS = 3


def _check_reason(reason: str | None) -> str:
    text = (reason or "").strip()
    if len(text) < MIN_REASON_CHARS or substance(text) < MIN_REASON_WORDS:
        raise ServiceError(
            "An obsolete close needs a reason a later reader can check — what made the "
            f"task unnecessary and where that is recorded (at least {MIN_REASON_CHARS} "
            f"characters and {MIN_REASON_WORDS} words once placeholders are removed). "
            'Example: --reason "resolved by 077e0957 under task X; HEAD no longer has Y".'
        )
    return text


def refuse_unclosable(task: dict[str, Any], slug: str) -> None:
    """Why `task done` must not close this task, raised before it writes anything.

    Already done: persist_declared_scope would rewrite the scope of a certified
    task — its risk_score, verify-cache hash and receipt — from a call that then
    fails, corrupting it invisibly. Never started (task-done-closes-a-task-that-
    never-started): a planning task never passed QG-0 and has no started_at, so
    closing it as delivered skipped the gate and broke cycle time; 52 of 1571
    done tasks had closed that way by session #269. Time-resolved work has its
    own exit, `task obsolete`.
    """
    if task["status"] == "done":
        raise ServiceError(f"Task '{slug}' is already done")
    if task["status"] == "planning":
        raise ServiceError(
            f"Task '{slug}' was never started, so it cannot close as delivered. "
            f"Start it (`task start {slug}`, QG-0) and do the work, or, if time "
            f'resolved it, `task obsolete {slug} --reason "..."`.'
        )


def close_obsolete(svc: Any, slug: str, reason: str | None) -> str:
    """Close `slug` as obsolete with `reason`; return the message to print."""
    text = _check_reason(reason)
    task = svc.be.task_get(slug)
    if not task:
        raise ServiceError(f"Task '{slug}' not found")
    if task["status"] == "done":
        kind = task.get("resolution") or "done"
        raise ServiceError(f"Task '{slug}' is already closed ({kind}); nothing to mark obsolete.")
    now = utcnow_iso()
    with svc.be.transaction():
        svc.be.task_update(
            slug,
            status="done",
            completed_at=now,
            updated_at=now,
            resolution=OBSOLETE,
            resolution_reason=text,
        )
        svc.be.task_append_notes(slug, f"OBSOLETE (was {task['status']}): {text}")
        msgs = [
            f"Task '{slug}' closed as OBSOLETE — kept on record, left out of delivery "
            "metrics (FPSR, DER, cycle/lead time, calibration)."
        ]
        msgs.extend(svc._cascade_done(slug))  # noqa: SLF001 — the same cascade as task done
    from task_baseline import release

    release(svc.tausik_dir(), slug)
    return " ".join(msgs)
