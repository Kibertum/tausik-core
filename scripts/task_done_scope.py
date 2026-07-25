"""Where a closing task's scope comes from — and when it gets written down.

Split out of `service_task_done` when that file crossed the 400-line gate. The
seam is real: `_task_done_report` decides whether a task may CLOSE, while this
answers a prior and separate question — what is this task's declared scope, and
which of three sources did it come from (the caller, the task row, or the last
verify run). The two got tangled because the answer arrives first and is then
used everywhere after.

Three sources, in falling order of authority:

1. The caller (`--relevant-files`). Authoritative, and PERSISTED IMMEDIATELY —
   see `persist_declared_scope`.
2. The task row, for a `task done` that names no files. Keeping this makes the
   verify-cache hash match the one `tausik verify --task` computed.
3. The latest fresh verify run, when caller and row are both silent. Security-
   sensitive paths are recovered for the COUNT only, never adopted as scope.
"""

from __future__ import annotations

import json
from typing import Any


def persist_declared_scope(be: Any, slug: str, relevant_files: list[str] | None) -> bool:
    """Write a caller-declared scope to the task row at once. True if written.

    verify-warn-names-a-flag-verify-does-not-have. A DECLARATION IS NOT A
    RESULT. The scope used to be written inside the `status=done` transaction,
    so a close blocked by Verify-First discarded it — and the agent was then
    told to run `verify`, which read the still-empty scope, skipped every gate
    and signed a receipt for nothing. Two commands pointing at each other with
    no way through. Recording the declaration when it is made costs one write
    and removes the deadlock; the blocked close still blocks.
    """
    if not relevant_files:
        return False
    be.task_update(slug, relevant_files=json.dumps(list(relevant_files)))
    return True


def scope_from_task_row(task: dict[str, Any]) -> list[str] | None:
    """The scope stored on the task, or None when absent/unparseable.

    Malformed JSON is treated as absence rather than an error: this runs on the
    close path, and a scope that cannot be read is exactly as informative as a
    scope that was never declared.
    """
    raw = task.get("relevant_files")
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, list) else None


def scope_from_recent_verify(conn: Any, slug: str) -> tuple[list[str] | None, list[str] | None]:
    """Recover a scope from the last fresh verify row.

    Returns ``(adoptable, for_count)``. They differ for security-sensitive
    paths: those are never adopted as the scope (v14-task-done-relevant-files-
    fallback keeps recovery explicit for auth/payment/hooks), but they still
    feed the complexity COUNT — a count leaks only a number, and dropping it
    would blind the detector to the highest-risk category, a security task
    closed as 'simple' (l26 review MED).
    """
    from service_verification import is_security_sensitive
    from verify_recent_lookup import lookup_relevant_files_from_recent_verify

    recovered = lookup_relevant_files_from_recent_verify(conn, slug)
    if not recovered:
        return None, None
    adoptable = recovered if not is_security_sensitive(recovered) else None
    return adoptable, recovered
