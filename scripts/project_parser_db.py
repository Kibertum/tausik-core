"""`tausik db` subparser, split out of `project_parser` for the filesize gate.

The file's own convention: a section moves here when the 500-line cap bites, rather than the cap
being widened. `db` was the smallest self-contained block, so it travelled first.
"""

from __future__ import annotations

from typing import Any


def add_db(sub: Any) -> None:
    """Register `db prune` — backup hygiene (v14b-junk-audit-pass)."""
    db_p = sub.add_parser("db", help="Database hygiene helpers")
    db_sub = db_p.add_subparsers(dest="db_cmd")
    db_prune = db_sub.add_parser(
        "prune",
        help="Delete oldest .tausik/tausik.db.bak.* files keeping the most recent N",
    )
    db_prune.add_argument(
        "--keep", type=int, default=3, help="Newest MANAGED .bak.v<N> backups to keep (default 3)"
    )
    db_prune.add_argument(
        "--dry-run", dest="dry_run", action="store_true", help="List deletions, delete nothing"
    )
    db_tel = db_sub.add_parser(
        "telemetry",
        help="Trim append-only sidecars in .tausik to their declared window (dry-run by default)",
    )
    db_tel.add_argument(
        "--apply", action="store_true", help="Actually trim; without it nothing is written"
    )
