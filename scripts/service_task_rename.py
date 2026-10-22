"""Rename a task slug and every column that stores it — one transaction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from task_slug_referrers import task_slug_referrers
from tausik_utils import ServiceError

if TYPE_CHECKING:
    from project_service import ProjectService

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def task_rename(svc: "ProjectService", old_slug: str, new_slug: str) -> str:
    """Move ``old_slug`` → ``new_slug`` with all referring columns.

    Referrers come from the live schema (see ``task_slug_referrers``). FK
    checks are deferred for the duration of the transaction (same pattern as
    ``state_import``), then ``PRAGMA foreign_key_check`` must be clean or the
    whole rename rolls back.
    """
    if not isinstance(old_slug, str) or not old_slug.strip():
        raise ServiceError("old slug must be a non-empty string")
    if not isinstance(new_slug, str) or not _SLUG_RE.match(new_slug):
        raise ServiceError(
            f"new slug {new_slug!r} refused: use lowercase letters, digits, hyphens "
            "(max 64, must start with letter/digit)"
        )
    if old_slug == new_slug:
        return f"Task '{old_slug}' already has that slug."
    old = svc.be.task_get(old_slug)
    if old is None:
        raise ServiceError(f"Task '{old_slug}' not found")
    if svc.be.task_get(new_slug) is not None:
        raise ServiceError(f"slug '{new_slug}' is already taken")

    conn = svc.be._conn
    referrers = task_slug_referrers(conn)

    with svc.be.transaction():
        # Children and parent both hold the slug; per-statement FK would refuse
        # either order. Defer to COMMIT (resets automatically at tx end).
        conn.execute("PRAGMA defer_foreign_keys=ON")
        for table, column in referrers:
            conn.execute(
                f'UPDATE "{table}" SET "{column}"=? WHERE "{column}"=?',
                (new_slug, old_slug),
            )
        conn.execute(
            "UPDATE tasks SET slug=?, updated_at=datetime('now') WHERE id=?",
            (new_slug, old["id"]),
        )
        violations = list(conn.execute("PRAGMA foreign_key_check"))
        if violations:
            raise ServiceError(
                f"rename rolled back: foreign_key_check reported {len(violations)} "
                f"violation(s), first={violations[0]}"
            )
        # Projection: drop the old path, write the new one — queued until commit.
        svc._project_task(old_slug)
        svc._project_task(new_slug)

    return f"Task renamed '{old_slug}' → '{new_slug}' ({len(referrers)} referring column(s))."
