"""`tausik hygiene` CLI handler.

Implements `docs/{en,ru}/task-archive-spec.md`: list (and optionally
soft-archive) done tasks older than ``task_archive.done_age_days`` days.

Default invocation is dry-run. ``--confirm`` writes ``archived_at`` on
matching rows; ``task_list`` then filters them out by default. The
``status`` column stays ``'done'`` so metrics, FTS, and direct
``task_show`` by slug still see the row — soft-delete, not removal.

SOFT-DELETE IS ONLY SOFT IF SOMETHING CAN UNDO IT, and for two releases nothing
could: the spec and a task's Rollback line both called task archival "reversible
by command" while no path anywhere cleared ``archived_at``. Recovering 877
candidate rows would have meant raw SQL, which this project forbids. `unarchive`
is that missing command.

MEMORY ARCHIVAL IS A DIFFERENT ANSWER and stays irreversible on purpose:
archiving a memory row stamps ``valid_to`` on its graph edges, and clearing the
flag would not bring the edges back (see ``backend_graph.edges_invalidate_to``).
A task has no such edges, so nothing is lost by unhiding it.
"""

from __future__ import annotations

from typing import Any

from project_service import ProjectService
from tausik_utils import ServiceError, utcnow_iso


def _archive_config(cfg: dict) -> tuple[bool, int]:
    """Return (enabled, done_age_days). Defensive: missing/bad → off."""
    block = cfg.get("task_archive") if isinstance(cfg, dict) else None
    if not isinstance(block, dict):
        return False, 90
    enabled = bool(block.get("enabled"))
    raw_age = block.get("done_age_days", 90)
    try:
        age = int(raw_age)
    except (TypeError, ValueError):
        age = 90
    if age < 1:
        age = 1
    return enabled, age


def _archive_candidates(svc: ProjectService, age_days: int) -> list[dict[str, Any]]:
    """Not-yet-archived done tasks with ``completed_at`` older than now − age_days."""
    cutoff_sql = f"-{int(age_days)} days"
    rows = svc.be._conn.execute(
        """
        SELECT slug, title, completed_at
        FROM tasks
        WHERE status = 'done'
          AND completed_at IS NOT NULL
          AND completed_at <= datetime('now', ?)
          AND archived_at IS NULL
        ORDER BY completed_at ASC
        """,
        (cutoff_sql,),
    ).fetchall()
    return [{"slug": r[0], "title": r[1], "completed_at": r[2]} for r in rows]


def _archive_apply(svc: ProjectService, age_days: int) -> int:
    """Stamp ``archived_at`` on done tasks older than the cutoff. Idempotent.

    Only rows with ``archived_at IS NULL`` are touched, so re-running the
    command after a successful pass is a no-op.
    """
    cutoff_sql = f"-{int(age_days)} days"
    cur = svc.be._conn.execute(
        """
        UPDATE tasks
           SET archived_at = ?, updated_at = ?
         WHERE status = 'done'
           AND completed_at IS NOT NULL
           AND completed_at <= datetime('now', ?)
           AND archived_at IS NULL
        """,
        (utcnow_iso(), utcnow_iso(), cutoff_sql),
    )
    svc.be._conn.commit()
    return cur.rowcount or 0


#: ARCHIVED WITHIN, not "older than", and the direction is the whole point. What needs
#: undoing is the mass pass somebody just ran — `hygiene archive --confirm` stamps every
#: eligible row in one statement, and the mistake is discovered minutes later. Selecting
#: the OLDEST archived rows instead would restore exactly the tasks that were meant to
#: stay hidden while leaving the fresh mistake in place.
def _unarchive_candidates(
    svc: ProjectService, slug: str | None = None, within_days: int | None = None
) -> list[dict[str, Any]]:
    """Archived tasks a matching `unarchive` would unhide.

    ``slug`` is exact. ``within_days`` selects rows stamped in the last N days. With
    neither, the result is empty: an unarchive with no selector would unhide the whole
    archive, which is not a recovery but a second mistake.
    """
    where = ["archived_at IS NOT NULL"]
    params: list[Any] = []
    if slug:
        where.append("slug = ?")
        params.append(slug)
    elif within_days is not None:
        where.append("archived_at >= datetime('now', ?)")
        params.append(f"-{int(within_days)} days")
    else:
        return []
    rows = svc.be._conn.execute(
        "SELECT slug, title, status, completed_at, archived_at FROM tasks "
        f"WHERE {' AND '.join(where)} ORDER BY archived_at DESC",
        tuple(params),
    ).fetchall()
    return [
        {
            "slug": r[0],
            "title": r[1],
            "status": r[2],
            "completed_at": r[3],
            "archived_at": r[4],
        }
        for r in rows
    ]


def _unarchive_apply(
    svc: ProjectService, slug: str | None = None, within_days: int | None = None
) -> int:
    """Clear ``archived_at`` on the matching rows. Returns the count.

    ONLY ``archived_at`` AND ``updated_at`` MOVE. ``status`` and ``completed_at`` are
    left exactly as they were, because archiving never changed them: the flag hides a
    row from `task list`, and lifting it unhides the row rather than reviving the work.
    A command that also reopened the task would turn a recovery into an edit of history.
    """
    rows = _unarchive_candidates(svc, slug=slug, within_days=within_days)
    if not rows:
        return 0
    slugs = [r["slug"] for r in rows]
    placeholders = ",".join("?" for _ in slugs)
    cur = svc.be._conn.execute(
        f"UPDATE tasks SET archived_at = NULL, updated_at = ? WHERE slug IN ({placeholders})",
        (utcnow_iso(), *slugs),
    )
    svc.be._conn.commit()
    return cur.rowcount or 0


def _cmd_hygiene_unarchive(svc: ProjectService, args: Any) -> None:
    """Dry-run by default, like its counterpart: `--confirm` writes.

    NOT GATED ON ``task_archive.enabled``. The config gates the operation that HIDES
    rows; a recovery path that switched off with it would be unavailable exactly when it
    is needed — after somebody archived a batch and turned the feature back off.
    """
    slug = getattr(args, "slug", None)
    within = getattr(args, "archived_within", None)
    if not slug and within is None:
        raise ServiceError(
            "hygiene unarchive needs a selector: --slug <slug> or --archived-within <days>. "
            "Without one it would unhide the whole archive, which is not a recovery."
        )
    candidates = _unarchive_candidates(svc, slug=slug, within_days=within)
    what = f"slug={slug!r}" if slug else f"archived in the last {within} day(s)"
    if not candidates:
        print(f"Hygiene unarchive: nothing archived matches {what}.")
        return
    if not getattr(args, "confirm", False):
        print(
            f"Hygiene unarchive (dry-run): {len(candidates)} archived task(s) match {what} "
            f"and would be unhidden. status and completed_at are not touched. "
            f"Re-run with `--confirm` to apply."
        )
        for row in candidates:
            title = row["title"] or ""
            if len(title) > 50:
                title = title[:47] + "..."
            print(f"  {row['slug']:<32} {row['archived_at']}  [{row['status']}]  {title}")
        return
    freed = _unarchive_apply(svc, slug=slug, within_days=within)
    print(
        f"Hygiene unarchive: {freed} task(s) unhidden ({what}). They are back in "
        f"`task list`; status and completed_at are unchanged."
    )


def cmd_hygiene(svc: ProjectService, args: Any) -> None:
    """Handle `tausik hygiene <subcmd>`."""
    sub = getattr(args, "hygiene_cmd", None)
    if sub is None:
        print("Usage: tausik hygiene [archive|unarchive] [--confirm]")
        print("  archive    List done tasks older than task_archive.done_age_days")
        print("  unarchive  Clear archived_at by --slug or --archived-within <days>")
        return
    if sub == "archive":
        _cmd_hygiene_archive(svc, args)
        return
    if sub == "unarchive":
        _cmd_hygiene_unarchive(svc, args)
        return
    raise ServiceError(f"Unknown hygiene subcommand: {sub!r}")


def _cmd_hygiene_archive(svc: ProjectService, args: Any) -> None:
    from project_config import load_config

    cfg = load_config()
    enabled, age_days = _archive_config(cfg)
    confirm = bool(getattr(args, "confirm", False))

    if not enabled:
        # Disabled config wins over --confirm: don't pretend to apply.
        print(
            "Hygiene archive: disabled. Set "
            "`task_archive.enabled = true` in .tausik/config.json "
            "to enable. Spec: docs/en/task-archive-spec.md"
        )
        return

    if confirm:
        archived = _archive_apply(svc, age_days)
        if archived == 0:
            print(
                f"Hygiene archive: nothing to archive — no unarchived done "
                f"tasks older than {age_days} days."
            )
            return
        print(
            f"Hygiene archive: archived {archived} done tasks older than "
            f"{age_days} days. They are hidden from `task list` by default; "
            f"use `--include-archived` to see them."
        )
        return

    candidates = _archive_candidates(svc, age_days)
    if not candidates:
        print(
            f"Hygiene archive (dry-run): no unarchived done tasks older than "
            f"{age_days} days. Active/blocked/planning/review tasks are never included."
        )
        return

    print(
        f"Hygiene archive (dry-run): {len(candidates)} done tasks older than "
        f"{age_days} days would be archived. Re-run with `--confirm` to apply."
    )
    for row in candidates:
        title = row["title"] or ""
        if len(title) > 60:
            title = title[:57] + "..."
        print(f"  {row['slug']:<32} {row['completed_at']}  {title}")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
