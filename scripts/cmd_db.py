"""`tausik db` CLI subcommands — backup hygiene helpers.

Currently exposes ``db prune`` to clean up auto-created
``.tausik/tausik.db.bak.*`` files left behind by migration runs.

The pure helper ``prune_backups`` is the test surface; ``cmd_db`` is the
thin argparse dispatcher used by ``scripts/project.py``.
"""

from __future__ import annotations

import glob
import os
from typing import Any


_BACKUP_PATTERN = "tausik.db.bak.*"


def list_backups(tausik_dir: str) -> list[str]:
    """Return absolute paths of all tausik.db backups, newest mtime first."""
    if not os.path.isdir(tausik_dir):
        return []
    matches = glob.glob(os.path.join(tausik_dir, _BACKUP_PATTERN))
    # mtime descending — most recently created first.
    return sorted(matches, key=lambda p: os.path.getmtime(p), reverse=True)


def prune_backups(tausik_dir: str, keep: int) -> dict[str, list[str]]:
    """Keep the ``keep`` most recent .bak files; delete the rest.

    Returns ``{"kept": [...], "deleted": [...], "errors": [...]}`` with
    absolute paths in each list. ``keep`` is clamped at zero (negative
    values are treated as 0). When fewer than ``keep`` backups exist the
    deleted list is empty (no-op).
    """
    if keep < 0:
        keep = 0
    backups = list_backups(tausik_dir)
    kept = backups[:keep]
    candidates = backups[keep:]
    deleted: list[str] = []
    errors: list[str] = []
    for path in candidates:
        try:
            os.remove(path)
            deleted.append(path)
        except OSError as e:
            errors.append(f"{path}: {e}")
    return {"kept": kept, "deleted": deleted, "errors": errors}


def cmd_db(svc: Any, args: Any) -> None:
    """Dispatch ``tausik db <subcommand>``."""
    sub = getattr(args, "db_cmd", None)
    if sub == "prune":
        keep = int(getattr(args, "keep", 3) or 0)
        from project_config import find_tausik_dir

        tausik_dir = find_tausik_dir()
        result = prune_backups(tausik_dir, keep)
        if not result["kept"] and not result["deleted"]:
            print("No tausik.db.bak.* files found.")
            return
        if result["kept"]:
            print(f"Kept ({len(result['kept'])}):")
            for p in result["kept"]:
                print(f"  {os.path.basename(p)}")
        if result["deleted"]:
            print(f"Deleted ({len(result['deleted'])}):")
            for p in result["deleted"]:
                print(f"  {os.path.basename(p)}")
        for err in result["errors"]:
            print(f"  ! {err}")
        return
    raise SystemExit(f"Unknown subcommand 'db {sub}'. Available: prune")
