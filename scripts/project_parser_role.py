"""argparse builder for `tausik role` subcommands.

Extracted to keep main parser under filesize gate.
"""

from __future__ import annotations

from typing import Any


def build_role_subparsers(sub: Any) -> None:
    """Attach `role` subparser tree."""
    role_p = sub.add_parser(
        "role", help="Role registry — list/show/create/update/delete"
    )
    role_sub = role_p.add_subparsers(dest="role_cmd")
    role_sub.add_parser("list")
    rs = role_sub.add_parser("show")
    rs.add_argument("slug")
    rc = role_sub.add_parser("create")
    rc.add_argument("slug")
    rc.add_argument("title")
    rc.add_argument("--description", default=None)
    rc.add_argument(
        "--extends",
        default=None,
        help="Existing role slug to clone profile from (e.g. developer)",
    )
    ru = role_sub.add_parser("update")
    ru.add_argument("slug")
    ru.add_argument("--title", default=None)
    ru.add_argument("--description", default=None)
    rd = role_sub.add_parser("delete")
    rd.add_argument("slug")
    rd.add_argument(
        "--force",
        action="store_true",
        help="Delete even if tasks reference this role",
    )
    role_sub.add_parser(
        "seed",
        help="Bootstrap role rows from agents/roles/*.md and existing task usage",
    )
