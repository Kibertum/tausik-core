"""argparse builder for `tausik stack` subcommands.

Extracted from project_parser.py to keep the main parser under the
400-line filesize gate.
"""

from __future__ import annotations

from typing import Any


def build_stack_subparsers(sub: Any) -> None:
    """Attach `stack` subparser tree to the top-level subparser."""
    stack_sub = sub.add_parser(
        "stack", help="Stack info — gates per language + user override management"
    ).add_subparsers(dest="stack_cmd")
    stack_sub.add_parser("info").add_argument("stack")  # validated by service
    stack_sub.add_parser("list")
    stack_sub.add_parser(
        "export", help="Print resolved stack decl as JSON"
    ).add_argument("stack")
    stack_sub.add_parser(
        "diff", help="Show diff between built-in and user override"
    ).add_argument("stack")
    reset_sub = stack_sub.add_parser(
        "reset", help="Remove user override for a stack (.tausik/stacks/<stack>/)"
    )
    reset_sub.add_argument("stack")
    reset_sub.add_argument(
        "--yes", action="store_true", help="Skip confirmation prompt"
    )
    stack_sub.add_parser(
        "lint", help="Validate user-override stack.json files against the schema"
    )
    scaff = stack_sub.add_parser(
        "scaffold",
        help="Create .tausik/stacks/<name>/{stack.json,guide.md} skeleton",
    )
    scaff.add_argument("stack")
    scaff.add_argument(
        "--extends",
        default=None,
        help="Built-in stack to extend (e.g. python). Sets 'extends: builtin:<X>' in skeleton.",
    )
    scaff.add_argument("--force", action="store_true", help="Overwrite existing files")
