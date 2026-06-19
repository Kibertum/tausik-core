"""Argparse subparser for `tausik config {set,show}`.

Extracted from project_parser_ops.py to keep that file under the 400-line gate.
"""

from __future__ import annotations

import argparse


def add_config(sub: argparse._SubParsersAction) -> None:
    """`tausik config {set,show}` — manage skill profile overrides."""
    c_p = sub.add_parser("config", help="Project config: ide_profile / model_profile")
    c_sub = c_p.add_subparsers(dest="config_cmd")
    c_set = c_sub.add_parser("set", help="Persist an override into .tausik/config.json")
    c_set.add_argument(
        "key",
        choices=["ide_profile", "model_profile"],
        help="Which override to set",
    )
    c_set.add_argument(
        "value",
        help="Value (e.g. claude/cursor/qwen/codex or opus/sonnet/gpt-5)",
    )
    c_sub.add_parser("show", help="Print resolved (ide, model, source) tuple")
