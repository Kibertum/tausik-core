"""The text of the task commands, rendered ONCE for both surfaces.

`tausik task next` and `tausik task logs` were each written twice — once in the
CLI, once in the MCP handler — and both pairs had drifted:

* `next` — the CLI names the withheld tasks, the handler printed only how many
  there were. An agent on MCP could see that the plan was waiting and not on
  what, which is the difference between a diagnosis and a rumour. The handler's
  own docstring claimed "this handler and the CLI print the same three states".
* `logs` — the CLI prints the full timestamp and omits the phase when a line has
  none; the handler truncated the timestamp to minutes and printed empty
  parentheses. Same rows, two shapes.

Neither drift was noticed by a test, because nothing compared the two. Rendering
in one place removes the thing that has to be compared: the surfaces cannot
disagree about text neither of them writes.

The richer rendering won each disagreement. A surface that shows MORE than
before is a safe change; one that shows less silently removes evidence someone
may already be relying on.

Returns lines rather than printing them: the CLI prints, the MCP handler joins
and returns, and neither owns the other's transport.
"""

from __future__ import annotations

from typing import Any

from service_task_order import task_deps, task_next_report

#: How many withheld slugs the summary names before it elides. The list is a
#: diagnosis ("waiting on what?"), not an inventory — `task list` is the
#: inventory — so it is bounded, and the elision is VISIBLE rather than silent.
_WITHHELD_SHOWN = 5


def task_next_lines(svc: Any, agent_id: str | None = None) -> list[str]:
    """The answer to `task next`: the backlog STATE, not just a task.

    "No available tasks" used to cover three different situations, one of which
    — everything waits on something unfinished — is a stalled plan that reads
    exactly like a finished one.
    """
    report = task_next_report(svc)
    if report["state"] == "ready":
        task = svc.task_next(agent_id)
        if task:
            action = "claimed and started" if agent_id else "suggested"
            lines = [
                f"Next task ({action}): {task['slug']} — {task['title']}",
                f"Chosen by: {report['basis']}",
            ]
            if report["blocked"]:
                lines.append(_withheld_line(report["blocked"]))
            hint = task.get("model_hint")
            if hint:
                lines.append(f"Model hint: {hint['display']} ({hint['model']})")
            return lines
    if report["state"] == "all-blocked":
        lines = [
            f"No task can start: all {len(report['blocked'])} open task(s) wait "
            "on an unfinished predecessor."
        ]
        for slug in report["blocked"]:
            lines.append(f"  {slug} — after: {', '.join(task_deps(svc, slug))}")
        return lines
    return ["No available tasks."]


def _withheld_line(blocked: list[str]) -> str:
    shown = ", ".join(blocked[:_WITHHELD_SHOWN])
    more = ", ..." if len(blocked) > _WITHHELD_SHOWN else ""
    return f"Withheld: {len(blocked)} task(s) waiting on an unfinished predecessor ({shown}{more})"


def task_logs_lines(svc: Any, slug: str, phase: str | None = None) -> list[str]:
    """The journal of one task, one line per entry.

    The empty answer NAMES the task. "No logs." on its own reads as a fact about
    the framework; "No logs for 'x'." reads as a fact about x, which is what was
    asked.
    """
    logs = svc.task_logs(slug, phase=phase)
    if not logs:
        return [f"No logs for '{slug}'."]
    lines = []
    for entry in logs:
        tag = f" [{entry['phase']}]" if entry.get("phase") else ""
        lines.append(f"[{entry['created_at']}]{tag} {entry['message']}")
    return lines
