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
    av = audit_sub.add_parser(
        "vendors",
        help="Audit vendor skill repos: classify installed vs vendored_unused (read-only)",
    )
    av.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit JSON instead of human-readable report",
    )
    ar = audit_sub.add_parser(
        "research",
        help="Audit docs/{en,ru}/research/ for stale unreferenced dumps (read-only)",
    )
    ar.add_argument(
        "--min-age-days",
        type=int,
        default=30,
        dest="min_age_days",
        help="Minimum file age in days to be considered (default: 30)",
    )
    ar.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit JSON instead of human-readable report",
    )


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

    sk_cat = sk_sub.add_parser(
        "catalog",
        help="Discovery: list skills offered by configured/cloned skill repos",
    )
    sk_cat.add_argument(
        "repo",
        nargs="?",
        default=None,
        help="Optional repo name (see: tausik skill repo list). Omit to list all repos.",
    )
    sk_cat.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit JSON instead of a human-readable table.",
    )

    sk_sign = sk_sub.add_parser(
        "sign",
        help="Sign a skill/stack release directory (ed25519 supply-chain signature)",
        epilog="Example: tausik skill sign skills-official/pdf",
    )
    sk_sign.add_argument("path", help="Release directory to sign")
    sk_sign.add_argument("--name", default=None, help="Artifact name (default: dir name)")

    sk_rebuild = sk_sub.add_parser(
        "rebuild",
        help="Pre-merge skill SKILL.md files with current ide+model overlays",
    )
    sk_rebuild.add_argument(
        "--force",
        action="store_true",
        help="Rewrite even if sha256 of merged content matches the file on disk",
    )

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
    sk_repo_trust = sk_repo_sub.add_parser(
        "trust",
        help="Pin a publisher public key for a repo (verified installs)",
        epilog="Example: tausik skill repo trust my-repo ed25519:<64 hex>",
    )
    sk_repo_trust.add_argument("name", help="Repo name (see: tausik skill repo list)")
    sk_repo_trust.add_argument(
        "pubkey",
        help="Publisher key from an OUT-OF-BAND channel ('ed25519:<64 hex>', "
        "never copied from the repo itself)",
    )

    sk_bundle = sk_sub.add_parser("bundle", help="Bulk install/uninstall skills via bundles.json")
    sk_bundle_sub = sk_bundle.add_subparsers(dest="bundle_cmd")
    sk_bundle_list = sk_bundle_sub.add_parser("list", help="List configured bundles + skill counts")
    sk_bundle_list.add_argument(
        "--json", action="store_true", dest="as_json", help="Emit JSON instead of a table."
    )
    sk_bundle_show = sk_bundle_sub.add_parser("show", help="Show a single bundle's skills")
    sk_bundle_show.add_argument("name", help="Bundle name (see: tausik skill bundle list)")
    sk_bundle_show.add_argument("--json", action="store_true", dest="as_json")
    sk_bundle_install = sk_bundle_sub.add_parser(
        "install", help="Install every skill in a bundle (skips deprecated)"
    )
    sk_bundle_install.add_argument("name", help="Bundle name (see: tausik skill bundle list)")
    sk_bundle_install.add_argument("--json", action="store_true", dest="as_json")
    sk_bundle_uninstall = sk_bundle_sub.add_parser(
        "uninstall", help="Uninstall every skill in a bundle"
    )
    sk_bundle_uninstall.add_argument("name", help="Bundle name (see: tausik skill bundle list)")
    sk_bundle_uninstall.add_argument("--json", action="store_true", dest="as_json")


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
    mt = metrics_sub.add_parser(
        "tokens",
        help="Per-tool token aggregates (p50/p90) over last N sessions from .tausik/token_metrics.jsonl",
    )
    mt.add_argument(
        "--last",
        type=int,
        default=10,
        help="Window size — last N distinct sessions (default: 10)",
    )
    mt.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON instead of formatted table",
    )
    sub.add_parser("hud", help="Live dashboard")
    sub.add_parser("suggest-model", help="Suggest Claude model for complexity").add_argument(
        "complexity", nargs="?", default=None
    )


def add_hygiene(sub: argparse._SubParsersAction) -> None:
    """`tausik hygiene archive [--confirm]` — list/soft-archive old done tasks.

    Spec: docs/{en,ru}/task-archive-spec.md. Dry-run by default; `--confirm`
    stamps `archived_at` on done tasks older than `task_archive.done_age_days`.
    Archived rows still exist (status stays 'done') but are hidden from
    `task list` unless `--include-archived` is passed.
    """
    h_p = sub.add_parser(
        "hygiene",
        help="Project hygiene operations (dry-run by default)",
    )
    h_sub = h_p.add_subparsers(dest="hygiene_cmd")
    h_arch = h_sub.add_parser(
        "archive",
        help="List or soft-archive done tasks older than task_archive.done_age_days",
    )
    h_arch.add_argument(
        "--confirm",
        action="store_true",
        help="Stamp archived_at on matching rows (idempotent). Without it, dry-run lists candidates.",
    )


def add_push_ok(sub: argparse._SubParsersAction) -> None:
    """`tausik push-ok [--ttl SECONDS]` — write a single-use push ticket.

    Consumed by scripts/hooks/git_push_gate.py on the next `git push`.
    Bound to current HEAD SHA + branch; expires after TTL (default 60s);
    one-shot (hook deletes it). Skills /commit and /ship invoke this only
    after the user has confirmed "y" to a push prompt.
    """
    pop = sub.add_parser(
        "push-ok",
        help="Authorize the next git push (writes single-use 60s ticket bound to HEAD)",
    )
    pop.add_argument(
        "--ttl",
        type=int,
        default=60,
        help="Ticket TTL in seconds (default: 60)",
    )
