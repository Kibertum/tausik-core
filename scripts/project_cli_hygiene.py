"""`tausik hygiene` CLI handler.

Implements `docs/{en,ru}/task-archive-spec.md`: list (and optionally
soft-archive) done tasks older than ``task_archive.done_age_days`` days.

Default invocation is dry-run. ``--confirm`` writes ``archived_at`` on
matching rows; ``task_list`` then filters them out by default. The
``status`` column stays ``'done'`` so metrics, FTS, and direct
``task_show`` by slug still see the row — soft-delete, not removal.
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


def cmd_hygiene(svc: ProjectService, args: Any) -> None:
    """Handle `tausik hygiene <subcmd>`."""
    sub = getattr(args, "hygiene_cmd", None)
    if sub is None:
        print("Usage: tausik hygiene [archive] [--confirm]")
        print("  archive  List done tasks older than task_archive.done_age_days")
        return
    if sub == "archive":
        _cmd_hygiene_archive(svc, args)
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
