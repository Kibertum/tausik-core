"""`tausik hygiene` CLI handler (v14-hygiene-cli-stub).

Implements the read-only v1 of `docs/{en,ru}/task-archive-spec.md`:
list done tasks older than ``task_archive.done_age_days`` days. Always
dry-run. ``--confirm`` is reserved for future destructive operations and
currently fails fast with an explanation, so accidental invocation cannot
silently mutate anything.
"""

from __future__ import annotations

from typing import Any

from project_service import ProjectService
from tausik_utils import ServiceError


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
    """Done tasks with completed_at older than now - age_days (UTC)."""
    cutoff_sql = f"-{int(age_days)} days"
    rows = svc.be._conn.execute(
        """
        SELECT slug, title, completed_at
        FROM tasks
        WHERE status = 'done'
          AND completed_at IS NOT NULL
          AND completed_at <= datetime('now', ?)
        ORDER BY completed_at ASC
        """,
        (cutoff_sql,),
    ).fetchall()
    return [{"slug": r[0], "title": r[1], "completed_at": r[2]} for r in rows]


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

    if getattr(args, "confirm", False):
        raise ServiceError(
            "hygiene archive v1 is read-only — `--confirm` has no destructive "
            "operation to confirm yet. Spec: docs/en/task-archive-spec.md"
        )

    cfg = load_config()
    enabled, age_days = _archive_config(cfg)
    if not enabled:
        print(
            "Hygiene archive: disabled. Set "
            "`task_archive.enabled = true` in .tausik/config.json "
            "to enable. Spec: docs/en/task-archive-spec.md"
        )
        return

    candidates = _archive_candidates(svc, age_days)
    if not candidates:
        print(
            f"Hygiene archive (dry-run): no done tasks older than {age_days} days. "
            "Active/blocked/planning/review tasks are never included."
        )
        return

    print(
        f"Hygiene archive (dry-run): {len(candidates)} done tasks older than "
        f"{age_days} days. v1 spec is read-only — no writes will happen."
    )
    for row in candidates:
        title = row["title"] or ""
        if len(title) > 60:
            title = title[:57] + "..."
        print(f"  {row['slug']:<32} {row['completed_at']}  {title}")
