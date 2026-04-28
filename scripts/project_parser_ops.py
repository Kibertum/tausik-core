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
        "--force",
        action="store_true",
        help="Overwrite existing local brain config in .tausik/config.json",
    )
    bi.add_argument(
        "--non-interactive",
        action="store_true",
        dest="non_interactive",
        help="Fail instead of prompting for missing args",
    )
    bi.add_argument(
        "--join-existing",
        action="store_true",
        dest="join_existing",
        help=(
            "Skip database creation; reuse the workspace's existing 4 BRAIN "
            "databases. Auto-discovers via Notion search; pass --decisions-id "
            "etc. to override."
        ),
    )
    bi.add_argument(
        "--force-create",
        action="store_true",
        dest="force_create",
        help=(
            "Create a fresh set of 4 BRAIN databases even if existing "
            "canonical-titled ones are detected. Rare — usually only for "
            "a brand-new Notion workspace/integration."
        ),
    )
    bi.add_argument(
        "--decisions-id",
        default=None,
        dest="decisions_id",
        help="Existing decisions DB id (use with --join-existing).",
    )
    bi.add_argument(
        "--web-cache-id",
        default=None,
        dest="web_cache_id",
        help="Existing web_cache DB id (use with --join-existing).",
    )
    bi.add_argument(
        "--patterns-id",
        default=None,
        dest="patterns_id",
        help="Existing patterns DB id (use with --join-existing).",
    )
    bi.add_argument(
        "--gotchas-id",
        default=None,
        dest="gotchas_id",
        help="Existing gotchas DB id (use with --join-existing).",
    )
    bs = brain_sub.add_parser(
        "status",
        help="Show brain mirror freshness, sync state, registered projects",
    )
    bs.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit raw JSON instead of human-readable markdown",
    )
    bm = brain_sub.add_parser(
        "move",
        help="Move a record between local TAUSIK and the shared brain",
    )
    bm.add_argument(
        "source_id", help="Local id (--to-brain) or notion_page_id (--to-local)"
    )
    direction = bm.add_mutually_exclusive_group(required=True)
    direction.add_argument("--to-brain", action="store_true", dest="to_brain")
    direction.add_argument("--to-local", action="store_true", dest="to_local")
    bm.add_argument(
        "--kind",
        choices=["decision", "pattern", "gotcha"],
        help="Source kind (--to-brain only)",
    )
    bm.add_argument(
        "--category",
        choices=["decisions", "patterns", "gotchas", "web_cache"],
        help="Brain category (--to-local only)",
    )
    bm.add_argument(
        "--force",
        action="store_true",
        help="Override cross-project ownership check (--to-local only)",
    )
    bm.add_argument(
        "--keep-source",
        action="store_true",
        dest="keep_source",
        help="Don't delete the source row after a successful move",
    )


def add_run(sub: argparse._SubParsersAction) -> None:
    run_p = sub.add_parser(
        "run",
        help="Parse and display a batch-run plan",
        epilog="Example: tausik run plan.md",
    )
    run_p.add_argument("plan_file", help="Path to markdown plan file")


def add_doc(sub: argparse._SubParsersAction) -> None:
    """`tausik doc <subcommand>` — optional document extraction via markitdown."""
    doc_p = sub.add_parser(
        "doc", help="Document extraction (DOCX/XLSX/PPTX/HTML/...) via markitdown"
    )
    doc_sub = doc_p.add_subparsers(dest="doc_cmd")
    de = doc_sub.add_parser("extract", help="Convert a document to markdown on stdout")
    de.add_argument("path", help="Path to document file")
    de.add_argument(
        "--format",
        dest="format_hint",
        default=None,
        help="Optional format hint (logged, markitdown auto-detects)",
    )
