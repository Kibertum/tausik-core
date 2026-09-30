"""A task that SAW a failure closes with a dead end, or says why there is none.

Measured in session #189: 67 closed tasks had at least one red verify, and not
one of the 67 carried a dead end. `tausik dead-end` was a voluntary command and
the rule lived as a line in CLAUDE.md — a rule the agent has to REMEMBER under
context pressure, the same class as continuous logging. So the framework asks at
the one moment it has itself observed a failure.

THE TRIGGER comes from data already written, never from `attempts` alone
(1 of 1239 closes had attempts > 1 in #189, so it cannot carry the rule):
  * a red `verification_runs` row for the task (exit_code != 0);
  * a `BLOCKED:` line in the task's journal (task block writes it);
  * more than one attempt (start after a block, or a restart).

WHAT SATISFIES IT, one of two:
  * a dead end linked to the task (`tausik dead-end ... --task <slug>`);
  * a journal line `NO-DEAD-END: <reason>` — the failure was a typo, a flaky
    run, a fixture — with a reason of at least MIN_REASON characters.

NOT A TAX ON RUNNING VERIFY: the second option is one log line, and the check
never fires on a task that saw no failure. A red run is information; closing
over it without a word is what this refuses.
"""

from __future__ import annotations

import re
from typing import Any

MARKER = "NO-DEAD-END:"
MIN_REASON = 10
_MARKER_RE = re.compile(r"NO-DEAD-END:\s*(.+)", re.IGNORECASE)


def _count(be: Any, sql: str, slug: str) -> int:
    row = be._q1(sql, (slug,))  # ruff-not-enabled: SLF001 — read-only, the backend's own helper
    return int((row or {}).get("n") or 0)


def observed_failures(be: Any, task: dict[str, Any]) -> list[str]:
    """What the framework itself saw fail on this task; empty when nothing did."""
    seen: list[str] = []
    red = _count(
        be,
        "SELECT COUNT(*) AS n FROM verification_runs WHERE task_slug=? AND exit_code != 0",
        task["slug"],
    )
    if red:
        seen.append(f"{red} red verify run(s)")
    if "BLOCKED:" in (task.get("notes") or ""):
        seen.append("the task was blocked")
    if int(task.get("attempts") or 0) > 1:
        seen.append(f"{task['attempts']} attempts")
    return seen


def statement(notes: str) -> str | None:
    """The `NO-DEAD-END:` reason in the journal, if one of sufficient length exists."""
    for m in _MARKER_RE.finditer(notes or ""):
        reason = m.group(1).strip()
        if len(reason) >= MIN_REASON:
            return reason
    return None


def check(be: Any, task: dict[str, Any]) -> str | None:
    """A blocking message, or None when the close may proceed."""
    seen = observed_failures(be, task)
    if not seen:
        return None
    slug = task["slug"]
    dead_ends = _count(
        be, "SELECT COUNT(*) AS n FROM memory WHERE task_slug=? AND type='dead_end'", slug
    )
    if dead_ends or statement(task.get("notes") or ""):
        return None
    return (
        f"'{slug}' saw a failure ({'; '.join(seen)}) and closes without a word about it. "
        f'Record what did not work: `.tausik/tausik dead-end "<approach>" "<why>" --task {slug}`, '
        f"or say why there is no dead end: `.tausik/tausik task log {slug} "
        f'"{MARKER} <the failure was a typo / a flaky run / ...>"`.'
    )


def bind_task(be: Any, task_slug: str | None) -> str:
    """The task a new dead end belongs to: given, or the single active one; else refuse."""
    if task_slug:
        if not be.task_get(task_slug):
            raise ValueError(f"task {task_slug!r} does not exist; a dead end must name a real task")
        return task_slug
    rows = be._q(
        "SELECT slug FROM tasks WHERE status='active' ORDER BY slug"
    )  # ruff-not-enabled: SLF001
    active = [str(r["slug"]) for r in rows]
    if len(active) == 1:
        return active[0]
    which = "no task is active" if not active else f"{len(active)} tasks are active"
    raise ValueError(
        f"a dead end must name its task, and {which}: add --task <slug> "
        "(half of the dead ends recorded before 1.10 said nowhere where they came from)"
    )
