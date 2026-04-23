"""Argparse subparser builders for SENAR ops commands (dead-end, explore, audit, brain, run).

Extracted from project_parser.py to keep that file under the 400-line filesize gate.
Each function takes the root `sub` ArgumentParser-subaction and attaches a subcommand.
"""

from __future__ import annotations

import argparse


def add_dead_end(sub: argparse._SubParsersAction) -> None:
    de_p = sub.add_parser("dead-end", help="Document a dead end (SENAR Rule 9.4)")
    de_p.add_argument("approach", help="What was tried")
    de_p.add_argument("reason", help="Why it failed")
    de_p.add_argument("--task", default=None, help="Related task slug")
    de_p.add_argument("--tags", nargs="*", default=None)


def add_explore(sub: argparse._SubParsersAction) -> None:
    exp_p = sub.add_parser(
        "explore", help="SENAR exploration — time-bounded investigation"
    )
    exp_sub = exp_p.add_subparsers(dest="explore_cmd")
    exp_start = exp_sub.add_parser("start", help="Start an exploration")
    exp_start.add_argument("title", help="What are you investigating")
    exp_start.add_argument(
        "--time-limit", type=int, default=30, help="Time limit in minutes"
    )
    exp_end = exp_sub.add_parser("end", help="End current exploration")
    exp_end.add_argument("--summary", default=None, help="What was found")
    exp_end.add_argument(
        "--create-task", action="store_true", help="Create task from findings"
    )
    exp_sub.add_parser("current", help="Show current exploration")


def add_audit(sub: argparse._SubParsersAction) -> None:
    audit_p = sub.add_parser("audit", help="SENAR periodic audit")
    audit_sub = audit_p.add_subparsers(dest="audit_cmd")
    audit_sub.add_parser("check", help="Check if audit is overdue")
    audit_sub.add_parser("mark", help="Mark audit as completed")


def add_brain(sub: argparse._SubParsersAction) -> None:
    brain_p = sub.add_parser("brain", help="Shared brain (cross-project knowledge)")
    brain_sub = brain_p.add_subparsers(dest="brain_cmd")
    bi = brain_sub.add_parser(
        "init", help="Initialize brain: create 4 Notion databases + config"
    )
    bi.add_argument("--parent-page-id", default=None, dest="parent_page_id")
    bi.add_argument("--token-env", default=None, dest="token_env")
    bi.add_argument("--project-name", default=None, dest="project_name")
    bi.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    bi.add_argument(
        "--force", action="store_true", help="Overwrite existing brain config"
    )
    bi.add_argument(
        "--non-interactive",
        action="store_true",
        dest="non_interactive",
        help="Fail instead of prompting for missing args",
    )


def add_run(sub: argparse._SubParsersAction) -> None:
    run_p = sub.add_parser(
        "run",
        help="Parse and display a batch-run plan",
        epilog="Example: tausik run plan.md",
    )
    run_p.add_argument("plan_file", help="Path to markdown plan file")
