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
    epic_sub.add_parser("list")
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
    sd = story_sub.add_parser("done")
    sd.add_argument("slug")
    sdel = story_sub.add_parser("delete")
    sdel.add_argument("slug")
