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
    exp_p = sub.add_parser("explore", help="SENAR exploration — time-bounded investigation")
    exp_sub = exp_p.add_subparsers(dest="explore_cmd")
    exp_start = exp_sub.add_parser("start", help="Start an exploration")
    exp_start.add_argument("title", help="What are you investigating")
    exp_start.add_argument("--time-limit", type=int, default=30, help="Time limit in minutes")
    exp_end = exp_sub.add_parser("end", help="End current exploration")
    exp_end.add_argument("--summary", default=None, help="What was found")
    exp_end.add_argument("--create-task", action="store_true", help="Create task from findings")
    exp_sub.add_parser("current", help="Show current exploration")


def add_audit(sub: argparse._SubParsersAction) -> None:
    audit_p = sub.add_parser("audit", help="SENAR periodic audit")
    audit_sub = audit_p.add_subparsers(dest="audit_cmd")
    audit_sub.add_parser("check", help="Check if audit is overdue")
    audit_sub.add_parser("mark", help="Mark audit as completed")


def add_review(sub: argparse._SubParsersAction) -> None:
    """SENAR Rule 10.15: track L1/L2/L3 review runs + ADR metric."""
    rev_p = sub.add_parser("review", help="Track L1/L2/L3 review runs (SENAR Rule 10.15)")
    rev_sub = rev_p.add_subparsers(dest="review_cmd")

    rec = rev_sub.add_parser("record", help="Record a review run")
    rec.add_argument("--task", required=True, help="Task slug being reviewed")
    rec.add_argument(
        "--type",
        dest="run_type",
        required=True,
        choices=["L1", "L2", "L3"],
        help="L1=author, L2=peer, L3=adversarial/external",
    )
    rec.add_argument("--critical", type=int, default=0, help="Number of critical findings")
    rec.add_argument("--warnings", type=int, default=0, help="Number of warnings")
    rec.add_argument("--notes", default=None, help="Free-form notes (links, summary)")

    ls = rev_sub.add_parser("list", help="List recent reviews")
    ls.add_argument("--task", default=None, help="Filter by task slug")
    ls.add_argument("--type", dest="run_type", default=None, choices=["L1", "L2", "L3"])
    ls.add_argument("--limit", type=int, default=20)
    ls.add_argument("--json", action="store_true", help="Output as JSON")

    rev_sub.add_parser("metrics", help="Show ADR metric")


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
    bm.add_argument(
        "--keep-source",
        action="store_true",
        dest="keep_source",
        help="Don't delete the source row after a successful move",
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


def add_run(sub: argparse._SubParsersAction) -> None:
    run_p = sub.add_parser(
        "run",
        help="Parse and display a batch-run plan",
        epilog="Example: tausik run plan.md",
    )
    run_p.add_argument("plan_file", help="Path to markdown plan file")


def add_doc(sub: argparse._SubParsersAction) -> None:
    """`tausik doc <subcommand>` — extract via markitdown; constants JSON generator."""
    doc_p = sub.add_parser(
        "doc",
        help="Document tools: extract (markitdown), constants (generated MCP/version JSON)",
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
    dc = doc_sub.add_parser(
        "constants",
        help="Write docs/_generated/constants.json from pyproject + MCP TOOLS counts",
    )
    dc.add_argument(
        "--check",
        action="store_true",
        dest="doc_constants_check",
        help="Exit 1 if constants.json is missing or out of sync",
    )


def add_skill(sub: argparse._SubParsersAction) -> None:
    """`tausik skill {activate,deactivate,list,install,uninstall,repo}`."""
    sk_p = sub.add_parser("skill", help="External skill lifecycle management")
    sk_sub = sk_p.add_subparsers(dest="skill_cmd")
    sk_act = sk_sub.add_parser(
        "activate",
        help="Activate a vendored skill (copy from vendor/ to .claude/skills/)",
    )
    sk_act.add_argument("name", help="Skill name to activate (see: tausik skill list)")
    sk_deact = sk_sub.add_parser(
        "deactivate", help="Deactivate an active skill (remove from .claude/skills/)"
    )
    sk_deact.add_argument("name", help="Skill name to deactivate (see: tausik skill list)")
    sk_sub.add_parser("list", help="List skills: active, vendored, available from configured repos")
    sk_inst = sk_sub.add_parser(
        "install",
        help="Install a skill from a configured repo (clone + copy + activate)",
    )
    sk_inst.add_argument("name", help="Skill name to install (see: tausik skill list)")
    sk_uninst = sk_sub.add_parser(
        "uninstall", help="Uninstall a skill (deactivate + drop from config)"
    )
    sk_uninst.add_argument("name", help="Skill name to uninstall (see: tausik skill list)")

    sk_repo = sk_sub.add_parser("repo", help="Manage skill repositories")
    sk_repo_sub = sk_repo.add_subparsers(dest="repo_cmd")
    sk_repo_add = sk_repo_sub.add_parser(
        "add",
        help="Add a TAUSIK-compatible skill repo (clones + validates)",
    )
    sk_repo_add.add_argument(
        "url",
        help=(
            "Git URL of skill repo (e.g. https://github.com/Kibertum/tausik-skills). "
            "Third-party URLs require --force."
        ),
    )
    sk_repo_add.add_argument(
        "--force",
        action="store_true",
        help="Confirm adding a third-party repo (not github.com/Kibertum/tausik-skills)",
    )
    sk_repo_rm = sk_repo_sub.add_parser("remove", help="Remove a configured skill repo")
    sk_repo_rm.add_argument("name", help="Repo name to remove (see: tausik skill repo list)")
    sk_repo_sub.add_parser("list", help="List configured skill repos")


def add_metrics(sub: argparse._SubParsersAction) -> None:
    """`tausik metrics`, `hud`, `suggest-model` subparsers."""
    metrics_p = sub.add_parser("metrics", help="Project metrics and velocity")
    metrics_p.add_argument(
        "--cost",
        action="store_true",
        help="Show LLM usage/cost rollup by task (same as `metrics cost`)",
    )
    metrics_sub = metrics_p.add_subparsers(dest="metrics_cmd")
    mr = metrics_sub.add_parser(
        "record-session",
        help="Record session token/cost metrics (used by hooks/session_metrics.py)",
    )
    mr.add_argument("--session-id", type=int, default=None)
    mr.add_argument("--tokens-input", type=int, required=True)
    mr.add_argument("--tokens-output", type=int, required=True)
    mr.add_argument("--tokens-total", type=int, required=True)
    mr.add_argument("--cost-usd", type=float, required=True)
    mr.add_argument("--tool-calls", type=int, default=0)
    mr.add_argument("--model", default="")
    ml = metrics_sub.add_parser(
        "log-usage",
        help="Append one usage_events row (source=manual); does not update session_usage_metrics",
    )
    ml.add_argument("--session-id", type=int, default=None)
    ml.add_argument("--task-slug", default=None, help="Optional; must exist in tasks.slug")
    ml.add_argument("--tokens-input", type=int, required=True)
    ml.add_argument("--tokens-output", type=int, required=True)
    ml.add_argument("--tokens-total", type=int, required=True)
    ml.add_argument("--cost-usd", type=float, required=True)
    ml.add_argument("--tool-calls", type=int, default=0)
    ml.add_argument("--model", default="")
    mc = metrics_sub.add_parser(
        "cost",
        help="Sum tokens/cost from usage_events grouped by task_slug (NULL slugs excluded)",
    )
    mc.add_argument("--since", default=None, help="ISO-8601 lower bound on recorded_at (inclusive)")
    mc.add_argument("--until", default=None, help="ISO-8601 upper bound on recorded_at (inclusive)")
    sub.add_parser("hud", help="Live dashboard")
    sub.add_parser("suggest-model", help="Suggest Claude model for complexity").add_argument(
        "complexity", nargs="?", default=None
    )


def add_hygiene(sub: argparse._SubParsersAction) -> None:
    """`tausik hygiene archive [--confirm]` — read-only project hygiene.

    v1 spec (docs/{en,ru}/task-archive-spec.md): list done tasks older than
    N days, never mutates anything. `--confirm` is reserved for future
    destructive operations and currently fails fast with an explanation.
    """
    h_p = sub.add_parser(
        "hygiene",
        help="Project hygiene operations (dry-run by default)",
    )
    h_sub = h_p.add_subparsers(dest="hygiene_cmd")
    h_arch = h_sub.add_parser(
        "archive",
        help="List done tasks older than task_archive.done_age_days (read-only in v1)",
    )
    h_arch.add_argument(
        "--confirm",
        action="store_true",
        help="Reserved for future destructive ops; currently rejected (v1 is dry-run only).",
    )
