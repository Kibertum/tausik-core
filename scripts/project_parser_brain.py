"""Argparse subparser for `tausik brain ...`.

Extracted from project_parser_ops.py to keep that file under the 400-line gate.
"""

from __future__ import annotations

import argparse


def add_brain(sub: argparse._SubParsersAction) -> None:
    brain_p = sub.add_parser("brain", help="Shared brain (cross-project knowledge)")
    brain_sub = brain_p.add_subparsers(dest="brain_cmd")
    bi = brain_sub.add_parser("init", help="Initialize brain: create 4 Notion databases + config")
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
    bsync = brain_sub.add_parser(
        "sync",
        help="Pull updates from Notion into the local mirror (.tausik-brain/brain.db)",
    )
    bsync.add_argument(
        "--category",
        choices=["decisions", "patterns", "gotchas", "web_cache"],
        default=None,
        help="Sync only one category (default: all 4)",
    )
    bsync.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit raw JSON instead of human-readable summary",
    )
    bm = brain_sub.add_parser(
        "move",
        help="Move a record between local TAUSIK and the shared brain",
    )
    bm.add_argument("source_id", help="Local id (--to-brain) or notion_page_id (--to-local)")
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
    # Keeping the local row is the DEFAULT. Publishing used to delete it, which
    # only became untenable once `decide` stopped mirroring on its own: this is
    # now the path a person is pointed at, and a publish that removes the
    # project's copy is a handover, not a publish.
    #
    # `--keep-source` is still accepted and now names the default, so any script
    # that passed it keeps working and keeps meaning the same thing. Handing a
    # record over is available under a name that says so.
    bm.add_argument(
        "--keep-source",
        action="store_true",
        dest="keep_source",
        default=True,
        help="Keep the local row after publishing (the default; kept for compatibility)",
    )
    bm.add_argument(
        "--drop-local",
        action="store_false",
        dest="keep_source",
        help="Delete the local row after a successful publish — a move, not a copy",
    )
    bd = brain_sub.add_parser(
        "draft",
        help="Dry-run artifact publish (pattern/gotcha): JSON via --json or --file",
    )
    bd.add_argument(
        "--json",
        dest="json_payload",
        default=None,
        metavar="TEXT",
        help='JSON object with "kind" (pattern|gotcha) and fields',
    )
    bd.add_argument(
        "--file",
        dest="json_file",
        default=None,
        metavar="PATH",
        help="JSON file path",
    )
    bp = brain_sub.add_parser(
        "publish",
        help="Publish artifact (pattern/gotcha) to Notion: JSON via --json or --file",
    )
    bp.add_argument(
        "--json",
        dest="json_payload",
        default=None,
        metavar="TEXT",
    )
    bp.add_argument(
        "--file",
        dest="json_file",
        default=None,
        metavar="PATH",
    )
    bp.add_argument(
        "--confirm-high-risk",
        action="store_true",
        dest="confirm_high_risk",
        help=("Allow publish when classifier marks high-risk (project-specific markers)"),
    )
