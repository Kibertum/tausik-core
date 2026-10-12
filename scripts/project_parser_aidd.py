"""AIDD command subparser — `tausik aidd autogen`."""

from __future__ import annotations

import argparse


def build_aidd_subparsers(sub: argparse._SubParsersAction) -> None:
    aidd_p = sub.add_parser("aidd", help="AIDD layer commands (autogen, validate)")
    aidd_sub = aidd_p.add_subparsers(dest="aidd_command", required=True)
    ag = aidd_sub.add_parser(
        "autogen",
        help="Draft vision.md pre-seeded from repo signals (stdlib-only, no LLM)",
    )
    ag.add_argument(
        "--write",
        action="store_true",
        help="Persist to vision.md (default: print draft to stdout)",
    )
    ag.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing vision.md without prompting",
    )
    aidd_sub.add_parser(
        "validate",
        help="Check conventions.md claims against repo (exit 1 on drift, 2 if missing)",
    )
