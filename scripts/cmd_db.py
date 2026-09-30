"""`tausik db` CLI subcommands — backup hygiene helpers.

Currently exposes ``db prune`` to clean up auto-created
``.tausik/tausik.db.bak.*`` files left behind by migration runs.

DECLARED LIFETIME OF A BACKUP. Two kinds live in `.tausik/`, and they expire
differently:

* ``tausik.db.bak.v<N>`` — written by the migration path before it raises the
  schema, and pruned by it to the newest `BACKUP_KEEP` (3). Its purpose is to
  undo a migration, so it expires after the next few migrations prove the new
  schema. This kind is MANAGED: a mechanism creates it and the same mechanism
  removes it.
* any other ``tausik.db.bak.*`` — made by hand before a one-off operation
  (`…-before-redact`, `…-pre-redact-263`). Its purpose expires with that
  operation, and NOTHING has ever removed one. MEASURED when this rule landed:
  three such files, 254 MiB, the oldest 13 days old, next to three managed ones —
  half the backup weight sat outside every retention rule, and a copy taken
  before a secret redaction outlives the redaction it precedes.

So an unversioned backup does not survive a prune. It is not "newer" material
to be kept in preference to a managed one; it is material whose operation is
over. This is why `prune_backups` splits by NAME rather than ranking one mtime
order over all of them: the old ranking kept the three unmanaged files and
deleted the managed ones, i.e. exactly backwards from what this module's own
first paragraph promises.

The pure helper ``prune_backups`` is the test surface; ``cmd_db`` is the
thin argparse dispatcher used by ``scripts/project.py``.
"""

from __future__ import annotations

import glob
import os
import re
from typing import Any


_BACKUP_PATTERN = "tausik.db.bak.*"

#: A MANAGED backup: written and pruned by the migration path in `backend_init`.
_VERSIONED_RE = re.compile(r"\.bak\.v(\d+)$")


def list_backups(tausik_dir: str) -> list[str]:
    """Return absolute paths of all tausik.db backups, newest mtime first."""
    if not os.path.isdir(tausik_dir):
        return []
    matches = glob.glob(os.path.join(tausik_dir, _BACKUP_PATTERN))
    # mtime descending — most recently created first.
    return sorted(matches, key=lambda p: os.path.getmtime(p), reverse=True)


def unmanaged_backups(tausik_dir: str) -> list[str]:
    """Backups no mechanism owns — every ``.bak.*`` that is not ``.bak.v<N>``.

    The ratchet in `tausik/gates.json` (`repo_hygiene.db_backups.unmanaged`)
    reads this, so the number that is allowed to exist is declared in one place
    and the detector is the same code the prune uses.
    """
    return [p for p in list_backups(tausik_dir) if not _VERSIONED_RE.search(os.path.basename(p))]


def backup_doctor_line(tausik_dir: str, keep: int | None = None) -> tuple[str, str]:
    """``(level, detail)`` for `tausik doctor` — the SIGNAL half of the retention.

    A retention rule with a command and no signal is a rule nobody applies: the
    prune existed for releases while half a gigabyte accumulated, because nothing
    ever said the word "backup" to the person who could run it. The ratchet in
    `tausik/gates.json` catches this at a close; this line catches it for someone
    who is only looking at the project, and both read the code above.

    Reports SIZE with the count, because three snapshots of a 90 MB database are
    a different fact from three of a 2 MB one and the number of files alone hides
    which one the reader has.
    """
    from backend_init import BACKUP_KEEP

    limit = BACKUP_KEEP if keep is None else keep
    backups = list_backups(tausik_dir)
    if not backups:
        return "ok", "no DB backups"
    unmanaged = unmanaged_backups(tausik_dir)
    mib = sum(os.path.getsize(p) for p in backups) / (1024 * 1024)
    managed = len(backups) - len(unmanaged)
    if unmanaged:
        names = ", ".join(sorted(os.path.basename(p) for p in unmanaged)[:2])
        return "warn", (
            f"{len(backups)} backup(s), {mib:.0f} MiB — {len(unmanaged)} made by hand and owned "
            f"by no mechanism ({names}). Their lifetime was the operation that made them: "
            f"`tausik db prune --keep {limit} --dry-run`"
        )
    if managed > limit:
        return "warn", (
            f"{managed} managed backup(s) over the keep of {limit}, {mib:.0f} MiB — "
            f"`tausik db prune --keep {limit}`"
        )
    return "ok", f"{managed} managed backup(s), {mib:.0f} MiB, none unmanaged"


def prune_backups(tausik_dir: str, keep: int, dry_run: bool = False) -> dict[str, list[str]]:
    """Keep the ``keep`` newest MANAGED backups; delete every other backup.

    Returns ``{"kept", "deleted", "errors", "unmanaged"}`` with absolute paths in
    each list. ``keep`` is clamped at zero (negative values are treated as 0).
    When fewer than ``keep`` managed backups exist, nothing managed is deleted
    (no-op for that group). With ``dry_run`` the same "deleted" list comes back
    and nothing is removed — this command is the only one in the CLI that
    destroys hundreds of megabytes, so it can be asked what it would do.

    "Newest" among managed backups is by VERSION NUMBER, not mtime: `v9` sorts
    after `v10` lexically, and a restore-from-backup rewrites mtimes, so both
    string order and file time have already been wrong about which snapshot is
    the recent one. Unversioned backups are deleted regardless of `keep` — see
    the module docstring for why their lifetime is the operation, not a count.
    """
    if keep < 0:
        keep = 0
    managed: list[tuple[int, str]] = []
    unmanaged: list[str] = []
    for path in list_backups(tausik_dir):
        m = _VERSIONED_RE.search(os.path.basename(path))
        if m:
            managed.append((int(m.group(1)), path))
        else:
            unmanaged.append(path)
    managed.sort(key=lambda pair: -pair[0])
    kept = [path for _ver, path in managed[:keep]]
    candidates = [path for _ver, path in managed[keep:]] + unmanaged
    deleted: list[str] = []
    errors: list[str] = []
    for path in candidates:
        if dry_run:
            deleted.append(path)
            continue
        try:
            os.remove(path)
            deleted.append(path)
        except OSError as e:
            errors.append(f"{path}: {e}")
    return {"kept": kept, "deleted": deleted, "errors": errors, "unmanaged": unmanaged}


def cmd_db(svc: Any, args: Any) -> None:
    """Dispatch ``tausik db <subcommand>``."""
    sub = getattr(args, "db_cmd", None)
    if sub == "prune":
        keep = int(getattr(args, "keep", 3) or 0)
        from project_config import find_tausik_dir

        tausik_dir = find_tausik_dir()
        dry = bool(getattr(args, "dry_run", False))
        result = prune_backups(tausik_dir, keep, dry_run=dry)
        if not result["kept"] and not result["deleted"]:
            print("No tausik.db.bak.* files found.")
            return
        if result["kept"]:
            print(f"Kept ({len(result['kept'])}):")
            for p in result["kept"]:
                print(f"  {os.path.basename(p)}")
        if result["deleted"]:
            unmanaged = set(result["unmanaged"])
            verb = "Would delete" if dry else "Deleted"
            print(f"{verb} ({len(result['deleted'])}):")
            for p in result["deleted"]:
                # The KIND is printed, because "why is my hand-made backup gone"
                # is the only question this output has to answer in advance.
                kind = (
                    "unmanaged, lifetime was its operation" if p in unmanaged else "beyond --keep"
                )
                print(f"  {os.path.basename(p)}  ({kind})")
        for err in result["errors"]:
            print(f"  ! {err}")
        return
    if sub == "telemetry":
        from project_config import find_tausik_dir
        from telemetry_retention import POLICIES, doctor_line, truncate

        tausik_dir = find_tausik_dir()
        applied = bool(getattr(args, "apply", False))
        trimmed = truncate(tausik_dir, dry_run=not applied)
        level, detail = doctor_line(tausik_dir)
        print(detail)
        if not trimmed:
            print("Nothing past its window.")
        for name, (before, after) in sorted(trimmed.items()):
            verb = "trimmed" if applied else "would trim"
            print(f"  {name}: {verb} {before} -> {after} lines (tail kept)")
        # The declared lifetimes are printed with the action, because a retention nobody can
        # read is a retention nobody trusts — and one file is deliberately NOT trimmed.
        for policy in POLICIES:
            window = (
                "not trimmed by age" if policy.keep_lines is None else f"{policy.keep_lines} lines"
            )
            print(f"  · {policy.name}: {window} — {policy.reason}")
        return
    raise SystemExit(f"Unknown subcommand 'db {sub}'. Available: prune, telemetry")
