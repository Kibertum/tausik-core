"""argparse builder for `tausik epic` / `tausik story` subcommands.

Extracted from project_parser.py for filesize compliance. build_parser() calls
build_hierarchy_subparsers(sub) — pure move, the command tree is unchanged.
"""

from __future__ import annotations

from typing import Any


def build_hierarchy_subparsers(sub: Any) -> None:
    # --- epic ---
    epic_p = sub.add_parser("epic", help="Epic management")
    epic_sub = epic_p.add_subparsers(dest="epic_cmd")
    ea = epic_sub.add_parser(
        "add",
        epilog='Example: tausik epic add my-epic "Epic title"',
    )
    ea.add_argument("slug", help="Epic slug (lowercase, hyphens)")
    ea.add_argument("title", help="Epic title (in quotes)")
    ea.add_argument("--description", default=None)
    el = epic_sub.add_parser("list")
    el.add_argument(
        "--stale-over",
        type=int,
        default=None,
        help="Show only epics whose description fell behind by more than N tasks "
        "(tasks created since the description was last edited); N=0 keeps every "
        "epic with at least one. Without the flag every epic prints with its number.",
    )
    eu = epic_sub.add_parser(
        "update",
        epilog='Example: tausik epic update my-epic --description "What this epic is for now"',
    )
    eu.add_argument("slug")
    eu.add_argument("--title", default=None)
    eu.add_argument("--description", default=None)
    ed = epic_sub.add_parser("done")
    ed.add_argument("slug")
    edel = epic_sub.add_parser("delete")
    edel.add_argument("slug")

    # --- story ---
    story_p = sub.add_parser("story", help="Story management")
    story_sub = story_p.add_subparsers(dest="story_cmd")
    sa = story_sub.add_parser(
        "add",
        epilog='Example: tausik story add my-epic my-story "Story title"',
    )
    sa.add_argument("epic_slug", help="Parent epic slug")
    sa.add_argument("slug", help="Story slug (lowercase, hyphens)")
    sa.add_argument("title", help="Story title (in quotes)")
    sa.add_argument("--description", default=None)
    sl = story_sub.add_parser("list")
    sl.add_argument("--epic", default=None)
    sl.add_argument(
        "--stale-over",
        type=int,
        default=None,
        help="Show only stories whose description fell behind by more than N tasks; "
        "N=0 keeps every story with at least one. Without the flag every story "
        "prints with its number.",
    )
    su = story_sub.add_parser(
        "update",
        epilog='Example: tausik story update my-story --title "New title"',
    )
    su.add_argument("slug")
    su.add_argument("--title", default=None)
    su.add_argument("--description", default=None)
    sd = story_sub.add_parser("done")
    sd.add_argument("slug")
    sdel = story_sub.add_parser("delete")
    sdel.add_argument("slug")
