"""A journal entry is paid for on every read, so its length has a budget.

MEASURED, session #277, and the split is what sets the numbers: 292 entries across 25
closed tasks, 99,335 characters (~24,800 tokens). Of those, 158 entries and 48,400
characters carry evidence of the closure — an AC with a tick, a structured root cause, a
domain or negative line. The other 134 entries and 50,935 characters, 51% of the whole,
retell the work. Median entry 319 characters, p90 520, longest 1,355.

WHY LENGTH MATTERS HERE AND NOT IN A COMMIT MESSAGE. A journal entry is written once and
READ many times: by `task show`, by the compaction carry-over, by the session-start
memory tail, by every fresh agent opening the task. A release whose subject is token
economy cannot have its own record be the largest producer of tokens in it.

WHAT IS NOT BUDGETED, and this is the half that keeps the rule honest: evidence. An entry
naming a test, a root cause, a domain argument or a negative scenario is why the journal
exists at all, and squeezing it would trade the expensive thing for the cheap one. Only
retelling is capped, and the cap is a SIGNAL — a refusal here would teach agents to close
tasks in silence, which is the failure this project was built against.
"""

from __future__ import annotations

import re

#: p90 of the measured distribution. Chosen over the mean because half the entries are
#: evidence and their length is legitimate; p90 sits above every ordinary entry and
#: below the handful that retell a session.
ENTRY_CHARS = 520

#: The measured mean of retelling per closed task (50,935 characters over 25 tasks).
#: A DECLARED REMAINDER, not a target: it may only shrink.
TASK_RETELLING_CHARS = 2037

#: Markers the project already uses to mean "this line is the proof, not the story".
#: Read from the same vocabulary the AC-evidence parser and the root-cause gate use, so
#: an author does not have to learn a second spelling to be exempt.
_EVIDENCE = re.compile(
    r"(AC-?\s*\d+\s*[:.]?\s*✓"
    r"|AC-?\s*\d+\s*:?\s*(?:tested via|✓)"
    r"|Root cause"
    r"|Domain\s*:"
    r"|Negative\s*:"
    r"|NO-DEAD-END"
    r"|EVIDENCE-(?:MOVED|RETIRED|UNPROVEN)"
    r"|tested via)",
    re.IGNORECASE,
)


def is_evidence(text: str) -> bool:
    """Whether this entry is proof of the closure rather than a retelling.

    Deliberately generous: a false positive costs one uncapped entry, a false negative
    nags the author about the very line the gate below demands. The asymmetry is the
    whole reason the check errs this way.
    """
    return bool(_EVIDENCE.search(text or ""))


def entry_advisory(text: str, *, limit: int = ENTRY_CHARS) -> str:
    """One line when a RETELLING entry is over budget, else ``""``.

    Silent for evidence at any length, and silent for everything under the limit — which
    is most of it: the measured median is 319 characters against a limit of 520.
    """
    body = text or ""
    if len(body) <= limit or is_evidence(body):
        return ""
    return (
        f"ЗАПИСЬ НА {len(body)} СИМВОЛОВ, предел для пересказа {limit}. Журнал читается "
        "заново при каждом `task show`, при переносе через сжатие и на старте смены — "
        "длина оплачивается не один раз. Доказательство закрытия (AC с галочкой, Root "
        "cause, Domain, Negative) не ограничено; ход работы короче, а подробности — в "
        "память или в CHANGELOG."
    )


def journal_chars(entries: list[str]) -> tuple[int, int]:
    """`(evidence_chars, retelling_chars)` for one task's entries."""
    evidence = sum(len(e) for e in entries if is_evidence(e))
    return evidence, sum(len(e) for e in entries) - evidence


def closing_advisory(entries: list[str], *, limit: int) -> str:
    """One line when a task's RETELLING total is over `limit`, else ``""``.

    The per-task figure is what the ratchet tracks, because a single long entry can be
    justified while a dozen medium ones usually cannot, and the sum is what the next
    reader actually pays.
    """
    try:
        _evidence, retelling = journal_chars(entries)
    except Exception:  # noqa: BLE001 — a hint must never cost a close
        return ""
    if retelling <= limit:
        return ""
    return (
        f"ПЕРЕСКАЗ В ЖУРНАЛЕ: {retelling} символов при пределе {limit} на задачу "
        "(доказательство закрытия не считается). Следующая задача дешевле, если ход "
        "работы уместить в шаг, а объяснения отправить в память."
    )


def log_suffix(text: str) -> str:
    """What `task log` appends to its confirmation: a prefixed advisory, or ``""``.

    The prefixing lives here rather than at the call site because `service_task.py` sits
    at its 500-line ceiling, and a formatting detail is not worth displacing a rule.
    """
    advisory = entry_advisory(text)
    return f"\nℹ {advisory}" if advisory else ""


def limits(repo_root: str | None = None) -> tuple[int, int]:
    """`(entry_chars, retelling_chars_per_task)` from the committed ratchet.

    Read from `tausik/gates.json` rather than hard-coded here, so the numbers ratchet in
    the same place as the project's other debt and a consumer project can set its own.
    Falls back to the measured defaults when the node is absent — a project that never
    adopted the ratchet keeps working, and the fallback is the figure the measurement
    produced rather than a round number.
    """
    import json
    import os

    root = repo_root or os.getcwd()
    try:
        with open(os.path.join(root, "tausik", "gates.json"), encoding="utf-8") as fh:
            node = json.load(fh).get("journal_budget") or {}
        entry = node.get("entry_chars")
        per_task = node.get("retelling_chars_per_task")
        return (
            int(entry) if isinstance(entry, int) else ENTRY_CHARS,
            int(per_task) if isinstance(per_task, int) else TASK_RETELLING_CHARS,
        )
    except (OSError, ValueError, TypeError):
        return ENTRY_CHARS, TASK_RETELLING_CHARS


def close_lines(entries: list[str], repo_root: str | None = None) -> list[str]:
    """The advisory a close prints about its own journal, or ``[]``.

    A list so the caller can splice it into the message without a conditional, and so a
    second budget line could join later without touching the call site.
    """
    try:
        _entry_limit, per_task = limits(repo_root)
        line = closing_advisory(entries, limit=per_task)
    except Exception:  # noqa: BLE001 — a hint must never cost a close
        return []
    return [line] if line else []


def close_lines_for(svc: object, slug: str) -> list[str]:
    """`close_lines` for a task, reading its own journal. Never raises.

    Takes the service so the call site stays one line: `service_task_done.py` sits at its
    500-line ceiling and a second read there would displace a rule.
    """
    try:
        entries = [row["message"] for row in svc.task_logs(slug)]  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — a hint must never cost a close
        return []
    return close_lines(entries)
