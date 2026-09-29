"""`tausik changelog` on the parser side.

Its own module for the same reason every other command family has one: `project_parser_ops`
is under a 500-line cap and this addition crossed it. A parser file per family also means a
reader looking for one command's flags does not scroll past nine others.
"""

from __future__ import annotations

from typing import Any


def add(sub: Any) -> None:
    """Register `changelog` and its subcommands on the given subparsers."""
    ch_p = sub.add_parser(
        "changelog", help="Per-task changelog fragments (changelog.d/) and their assembly"
    )
    ch_sub = ch_p.add_subparsers(dest="changelog_cmd")
    ch_asm = ch_sub.add_parser(
        "assemble",
        help="Fold every changelog.d/<slug>.md into both CHANGELOG files in slug order "
        "and remove the fragments. Without --apply it only says what it would do.",
    )
    ch_asm.add_argument("--apply", action="store_true", help="Write, and delete the fragments")
