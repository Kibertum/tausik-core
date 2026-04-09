#!/usr/bin/env python3
"""Generate CLI reference documentation from argparse tree.

Usage: python scripts/generate_cli_ref.py
Outputs markdown to stdout.
"""

from __future__ import annotations

import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from project_parser import build_parser  # noqa: E402


def format_action(action) -> str:
    """Format a single argparse action as markdown."""
    if action.option_strings:
        flags = ", ".join(action.option_strings)
    else:
        flags = action.dest
    parts = [f"`{flags}`"]
    if action.choices:
        parts.append(f"(choices: {', '.join(str(c) for c in action.choices)})")
    if action.default is not None and action.default != "==SUPPRESS==":
        parts.append(f"(default: {action.default})")
    if action.help:
        parts.append(f"-- {action.help}")
    return " ".join(parts)


def print_subcommands(parser, prefix: str = "", level: int = 2) -> None:
    """Recursively print subcommands as markdown."""
    for action in parser._actions:
        if action.__class__.__name__ == "_SubParsersAction":
            for name, subparser in action.choices.items():
                full_cmd = f"{prefix} {name}".strip()
                print(f"\n{'#' * level} `tausik {full_cmd}`\n")
                if subparser.description:
                    print(f"{subparser.description}\n")

                positional = [
                    a
                    for a in subparser._actions
                    if not a.option_strings
                    and a.dest != "help"
                    and a.__class__.__name__ != "_SubParsersAction"
                ]
                optional = [
                    a
                    for a in subparser._actions
                    if a.option_strings and a.dest != "help"
                ]

                if positional:
                    for a in positional:
                        print(f"- {format_action(a)}")

                if optional:
                    for a in optional:
                        print(f"- {format_action(a)}")

                if subparser.epilog:
                    print(f"\n*{subparser.epilog}*")

                print_subcommands(subparser, full_cmd, level + 1)


def main() -> None:
    print("# TAUSIK CLI Reference\n")
    print("Auto-generated from argparse definitions.\n")

    parser = build_parser()
    print_subcommands(parser)


if __name__ == "__main__":
    main()
