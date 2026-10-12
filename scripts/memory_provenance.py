"""Where a memory record's claim came from — and "observed" has to be earned.

1.10, story D (memory-record-does-not-say-where-its-claim-came-from). Every
record carries `provenance`: `observed`, `inferred` or `told`. Without a check
the field would decay into noise within a week — every agent would write
"observed" — so the strong value is EARNED: an `observed` record must point at
something checkable, or it is written as `inferred` and the writer is told so.

Checkable means one of: a verification run named in the text
(`verification_run #N`, `verify #N`), a test named by path
(`tests/...py` or `tests/...py::test_x`), or a task the record is linked to
whose journal is not empty. This is the same shape of evidence `task done`
accepts, so an agent who closed a task honestly already has what it needs.
"""

from __future__ import annotations

import re
from typing import Any

from tausik_utils import ServiceError

VALUES = ("observed", "inferred", "told")
_CHECKABLE = re.compile(
    r"(verification_run\s*#\d+|verify\s*#\d+|tests/[\w./-]+\.py(::\w+)?)", re.IGNORECASE
)


def backing(be: Any, content: str, task_slug: str | None) -> str | None:
    """What makes an `observed` claim checkable; None when nothing does."""
    m = _CHECKABLE.search(content or "")
    if m:
        return m.group(1)
    if task_slug:
        task = be.task_get(task_slug)
        if task and (task.get("notes") or "").strip():
            return f"the journal of task {task_slug}"
    return None


def settle(be: Any, provenance: str | None, content: str, task_slug: str | None) -> tuple[str, str]:
    """(provenance to store, note for the writer). Refuses an unknown value."""
    value = (provenance or "inferred").strip().lower()
    if value not in VALUES:
        raise ServiceError(f"provenance must be one of {', '.join(VALUES)}, got {provenance!r}")
    if value != "observed" or backing(be, content, task_slug):
        return value, ""
    return "inferred", (
        " Provenance DOWNGRADED to inferred: an observed record must name something "
        "checkable — a verification run (verify #N), a test (tests/...py::test_x), "
        "or a task with a journal (--task)."
    )
