"""Argparse wiring for `tausik state ...` (state-git-export / state-git-import).

Extracted from project_parser.py to keep that file under the 400-line filesize
cap. `state export` serializes durable DB state to the git-native `tausik/` tree;
`state import` (alias top-level `sync`) rebuilds the DB cache from that tree;
`--check` fails CI on a stale tree (same contract as `renar export --check`).
"""

from __future__ import annotations

import argparse


def _add_import(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out", default=None, help="Tree dir (default: <project_root>/tausik/)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Show the add/update/journal/edge plan without writing to the DB",
    )


def build_state_subparsers(sub: argparse._SubParsersAction) -> None:
    state_p = sub.add_parser(
        "state", help="Git-native project-state projection (export DB <-> tausik/)"
    )
    state_sub = state_p.add_subparsers(dest="state_cmd")
    se = state_sub.add_parser(
        "export",
        help="Serialize durable DB state to the tausik/ tree (one file per entity)",
        epilog="Example: tausik state export  |  tausik state export --check",
    )
    se.add_argument("--out", default=None, help="Output dir (default: <project_root>/tausik/)")
    se.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if the tausik/ tree is stale vs live DB (CI gate)",
    )
    si = state_sub.add_parser(
        "import",
        help="Rebuild the DB cache from the tausik/ tree (idempotent delta; git wins)",
        epilog="Example: tausik state import  |  tausik state import --dry-run",
    )
    _add_import(si)

    # Top-level `tausik sync` — a convenience alias for `tausik state import`, the
    # command an engineer runs after `git pull` / `git checkout`.
    sync_p = sub.add_parser("sync", help="Alias for `tausik state import` (tree -> DB cache)")
    _add_import(sync_p)
