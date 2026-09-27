"""Starting a task that is not the plan's next one is said out loud, once.

MEASURED on the session that filed this, which is the only reason it exists: 22 tasks
closed, 4 of them from the plan that existed beforehand, 18 filed AND closed inside the
same session. Nine of those eighteen were the owner's own instructions and legitimate.
The other nine were findings the agent chased, including four the owner then named as
work he did not want before a release.

THE MECHANISM IS BUILT INTO THE CYCLE, which is why willpower does not fix it:

  1. `task done` prints findings -- closure notes, ratchets that fired, gate output.
  2. The project's first principle says file a bug for each. That step is RIGHT.
  3. The agent then STARTS it, because the context is warm and it is cheap RIGHT NOW.

Step 3 is the defect. "Cheap right now" is not "next in the plan", and repeating it
walks a defect tree depth-first, never returning. `task next` already chooses correctly
-- release first, then declared order -- and was not called once in that session.

SO THIS MOVES KNOWLEDGE, IT DOES NOT ADD IT. The comparison lives where the decision is
taken, not one command away from it.

A SIGNAL, NEVER A GATE (decision #376). Filing a finding must stay free: forbidding it
brings back the silent errors this project exists against. DEFERRING one is what the
line asks for, and it names the displaced task, because a reproach without an address is
not an action.
"""

from __future__ import annotations

from typing import Any


def displaced_by(svc: Any, slug: str) -> dict[str, Any] | None:
    """The task the plan would have offered instead, or ``None``.

    ``None`` covers every case where there is nothing to say: the backlog offers this
    very task, or offers nothing at all. Those are the common cases and they must stay
    silent — a note printed on every start is read on none of them.
    """
    from service_task_order import task_next_report

    report = task_next_report(svc)
    if report.get("state") != "ready":
        # Nothing offerable: no composition work is being displaced. Work outside the
        # plan is then legitimate and a warning about it would be noise.
        return None
    candidate = report.get("task")
    if not isinstance(candidate, dict) or candidate.get("slug") == slug:
        return None
    return {"slug": candidate.get("slug"), "basis": report.get("basis"), "task": candidate}


def plan_advisory(svc: Any, slug: str) -> str:
    """One line when `slug` displaces the plan's choice, else ``""``.

    Never raises. An advisory that can break `task start` is a gate with extra steps,
    and this one exists to be ignored freely when the author has a reason.
    """
    try:
        displaced = displaced_by(svc, slug)
    except Exception:  # noqa: BLE001 — advice must never cost a task start
        return ""
    if not displaced:
        return ""
    other = displaced["slug"]
    basis = displaced.get("basis") or "release first, then declared order"
    return (
        f"Не по плану: состав предлагал `{other}` ({basis}), а начата `{slug}`. "
        "Это не запрет — находку заводить свободно, но ОТКЛАДЫВАТЬ её дешевле, чем "
        "начинать: 82% закрытий одной смены оказались задачами, заведёнными в той же "
        f"смене. Вернуться к плану: `tausik task start {other}`."
    )


def plan_next_line(svc: Any) -> list[str]:
    """One line naming what the plan offers next, or ``[]``.

    Printed at CLOSE, not only at start, and that is the whole point of it. Drift is
    not born on `task start` -- by then the choice is made. It is born here: `task
    done` prints findings (closure notes, ratchets that fired, ticket reminders, gate
    output) and that is the only moment an agent sees a list of things worth doing.
    The plan is not in that list. So the finding wins by being the only thing on
    screen, and a signal one command away arrives too late to matter.

    ONE LINE, because this is framework code: it ships to every project on TAUSIK and
    is paid for on EVERY close. `[]` whenever the backlog offers nothing, so a project
    working legitimately outside a release composition never sees it.

    Never raises. A close that fails over a hint would be a gate nobody asked for.
    """
    try:
        from service_task_order import task_next_report

        report = task_next_report(svc)
        if report.get("state") != "ready":
            return []
        candidate = report.get("task")
        if not isinstance(candidate, dict) or not candidate.get("slug"):
            return []
        basis = report.get("basis") or "release first, then declared order"
        return [
            f"ПЛАН ПРЕДЛАГАЕТ ДАЛЬШЕ: `{candidate['slug']}` ({basis}). "
            "Находку выше заводить свободно — начинать по плану."
        ]
    except Exception:  # noqa: BLE001 — a hint must never cost a close
        return []
