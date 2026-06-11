"""TAUSIK argparse parser — CLI command tree."""

from __future__ import annotations

import argparse

from project_parser_errors import SelfCorrectingParser
from project_parser_task import add_task
from project_types import (
    VALID_EDGE_RELATIONS,
    VALID_MEMORY_TYPES,
    VALID_NODE_TYPES,
)


def build_parser() -> argparse.ArgumentParser:
    # v1.5 self-correcting CLI: arg errors print usage + known-good examples.
    # Subparsers inherit the class, so the whole tree is covered.
    p = SelfCorrectingParser(prog="tausik", description="TAUSIK")
    sub = p.add_subparsers(dest="command")

    # --- init ---
    init_p = sub.add_parser("init", help="Initialize project")
    init_p.add_argument("--name", default=None, help="Project slug (default: directory name)")
    init_p.add_argument(
        "--template",
        default=None,
        help="Scaffold template: 'aidd' creates idea.md/vision.md/conventions.md "
        "with conflict prompt (default skip).",
    )
    init_p.add_argument(
        "--force",
        action="store_true",
        help="With --template: overwrite existing files without prompting.",
    )

    # --- status ---
    st_p = sub.add_parser("status", help="Project overview")
    st_p.add_argument(
        "--compact",
        action="store_true",
        help="Single-line JSON (tasks + session id + optional session_warning)",
    )

    # --- epic ---
    epic_p = sub.add_parser("epic", help="Epic management")
    epic_sub = epic_p.add_subparsers(dest="epic_cmd")
    ea = epic_sub.add_parser(
        "add",
        epilog='Example: tausik epic add my-epic "Epic title"',
    )
    ea.add_argument("slug", help="Epic slug (lowercase, hyphens)")
    ea.add_argument("title", help="Epic title (in quotes)")
    ea.add_argument("--description", default=None)
    epic_sub.add_parser("list")
    ed = epic_sub.add_parser("done")
    ed.add_argument("slug")
    edel = epic_sub.add_parser("delete")
    edel.add_argument("slug")

    # --- story ---
    story_p = sub.add_parser("story", help="Story management")
    story_sub = story_p.add_subparsers(dest="story_cmd")
    sa = story_sub.add_parser(
        "add",
        epilog='Example: tausik story add my-epic my-story "Story title"',
    )
    sa.add_argument("epic_slug", help="Parent epic slug")
    sa.add_argument("slug", help="Story slug (lowercase, hyphens)")
    sa.add_argument("title", help="Story title (in quotes)")
    sa.add_argument("--description", default=None)
    sl = story_sub.add_parser("list")
    sl.add_argument("--epic", default=None)
    sd = story_sub.add_parser("done")
    sd.add_argument("slug")
    sdel = story_sub.add_parser("delete")
    sdel.add_argument("slug")

    # --- task --- (extracted to project_parser_task.add_task to keep filesize gate)
    add_task(sub)

    # --- team ---
    sub.add_parser("team", help="Team status — tasks by agent")

    # --- session ---
    from project_parser_session import build_session_subparsers

    build_session_subparsers(sub)

    from project_parser_role import build_role_subparsers
    from project_parser_stack import build_stack_subparsers

    build_stack_subparsers(sub)
    build_role_subparsers(sub)
    sub.add_parser("doctor", help="Health check: venv + DB + MCP + skills + drift")

    # --- decide ---
    dec_p = sub.add_parser("decide", help="Record a decision")
    dec_p.add_argument("text")
    dec_p.add_argument("--task", default=None)
    dec_p.add_argument("--rationale", default=None)

    # --- decisions ---
    decs_p = sub.add_parser("decisions", help="List decisions")
    decs_p.add_argument("--limit", type=int, default=20)

    # --- memory ---
    mem_p = sub.add_parser("memory", help="Project memory")
    mem_sub = mem_p.add_subparsers(dest="memory_cmd")
    ma = mem_sub.add_parser("add")
    ma.add_argument("mem_type", choices=sorted(VALID_MEMORY_TYPES))
    ma.add_argument("title")
    ma.add_argument("content")
    ma.add_argument("--tags", nargs="*", default=None)
    ma.add_argument("--task", default=None)
    ml = mem_sub.add_parser("list")
    ml.add_argument("--type", default=None, dest="mem_type")
    ml.add_argument("--limit", type=int, default=50)
    ml.add_argument(
        "--include-archived",
        action="store_true",
        help="Include soft-archived rows (archived_at IS NOT NULL).",
    )
    ms = mem_sub.add_parser("search")
    ms.add_argument("query")
    ms.add_argument(
        "--include-archived",
        action="store_true",
        help="Include soft-archived rows in search results.",
    )
    mshow = mem_sub.add_parser("show")
    mshow.add_argument("id", type=int)
    mdel = mem_sub.add_parser("delete")
    mdel.add_argument("id", type=int)
    march = mem_sub.add_parser(
        "archive",
        help="Soft-archive memory rows older than --before. Dry-run unless --confirm.",
    )
    march.add_argument(
        "--before",
        required=True,
        help="Duration: 90d / 12w / 2m / 1y (units d/w/m/y).",
    )
    march.add_argument(
        "--confirm",
        action="store_true",
        help="Apply: stamp archived_at on candidates (idempotent). Without it: dry-run preview.",
    )
    mdedupe = mem_sub.add_parser(
        "dedupe",
        help="Suggest memory pairs with similarity >= threshold. Read-only.",
    )
    mdedupe.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Similarity threshold in (0, 1]. Default 0.85.",
    )
    mdedupe.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max recent rows scanned for pairs. Default 200.",
    )
    # graph subcommands
    mlink = mem_sub.add_parser("link", help="Create edge between nodes")
    mlink.add_argument("source_type", choices=sorted(VALID_NODE_TYPES))
    mlink.add_argument("source_id", type=int)
    mlink.add_argument("target_type", choices=sorted(VALID_NODE_TYPES))
    mlink.add_argument("target_id", type=int)
    mlink.add_argument("relation", choices=sorted(VALID_EDGE_RELATIONS))
    mlink.add_argument("--confidence", type=float, default=1.0)
    mlink.add_argument("--created-by", default=None)
    munlink = mem_sub.add_parser("unlink", help="Soft-invalidate an edge (never deletes)")
    munlink.add_argument("edge_id", type=int)
    munlink.add_argument("--replacement", type=int, default=None, help="Replacement edge ID")
    mrelated = mem_sub.add_parser("related", help="Find related nodes via graph")
    mrelated.add_argument("node_type", choices=sorted(VALID_NODE_TYPES))
    mrelated.add_argument("node_id", type=int)
    mrelated.add_argument("--hops", type=int, default=2)
    mrelated.add_argument("--include-invalid", action="store_true")
    mgraph = mem_sub.add_parser("graph", help="List graph edges")
    mgraph.add_argument("--type", default=None, dest="node_type", choices=sorted(VALID_NODE_TYPES))
    mgraph.add_argument("--id", type=int, default=None, dest="node_id")
    mgraph.add_argument(
        "--relation",
        default=None,
        choices=sorted(VALID_EDGE_RELATIONS),
    )
    mgraph.add_argument("--include-invalid", action="store_true")
    mgraph.add_argument("--limit", type=int, default=50)
    mblock = mem_sub.add_parser(
        "block",
        help="Print compact memory block (decisions + conventions + dead ends) for re-injection",
    )
    mblock.add_argument("--max-decisions", type=int, default=5)
    mblock.add_argument("--max-conventions", type=int, default=10)
    mblock.add_argument("--max-deadends", type=int, default=5)
    mblock.add_argument("--max-lines", type=int, default=50)
    mcompact = mem_sub.add_parser(
        "compact",
        help="Aggregate recent task_logs into pattern summary (phases, top words, top files)",
    )
    mcompact.add_argument("--last", type=int, default=50, dest="last_n")

    # --- gates ---
    gates_p = sub.add_parser("gates", help="Quality gates status")
    gates_sub = gates_p.add_subparsers(dest="gates_cmd")
    gates_sub.add_parser("status", help="Show active gates and their config")
    gates_sub.add_parser("list", help="List all gates with enabled/disabled state")
    ge = gates_sub.add_parser("enable")
    ge.add_argument("name", help="Gate name to enable")
    gd = gates_sub.add_parser("disable")
    gd.add_argument("name", help="Gate name to disable")

    # --- key (v15-crypto-keymgmt) ---
    key_p = sub.add_parser("key", help="Project signing key (ed25519)")
    key_sub = key_p.add_subparsers(dest="key_cmd")
    ki = key_sub.add_parser(
        "init",
        help="Generate project keypair in .tausik/keys/",
        epilog="Example: tausik key init",
    )
    ki.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing key (old signatures stop verifying)",
    )
    key_sub.add_parser("show", help="Print public key + fingerprint (never the seed)")

    vp = sub.add_parser("verify", help="Run scoped quality gates")
    vp.add_argument("--task")
    _scopes = ["lightweight", "standard", "high", "critical", "manual"]
    vp.add_argument("--scope", choices=_scopes, default="manual")

    rm_p = sub.add_parser("roadmap", help="Project roadmap")
    rm_p.add_argument("--include-done", action="store_true")

    # --- update-claudemd ---
    uc_p = sub.add_parser("update-claudemd", help="Update CLAUDE.md dynamic section")
    uc_p.add_argument(
        "--claudemd", default=None, help="Path to CLAUDE.md (auto-detected if omitted)"
    )
    uc_p.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Show diff between current CLAUDE.md and what `update-claudemd` would write; do not modify the file. Exit code 0 if identical, 1 if drift detected.",
    )

    # --- metrics / hud / suggest-model (delegated below) ---

    # --- search ---
    sr_p = sub.add_parser("search", help="Full-text search")
    sr_p.add_argument("query")
    sr_p.add_argument("--scope", default="all", choices=["all", "tasks", "memory", "decisions"])
    sr_p.add_argument("--limit", type=int, default=20, help="Max results per scope")

    # --- fts ---
    fts_p = sub.add_parser("fts", help="FTS5 index maintenance")
    fts_sub = fts_p.add_subparsers(dest="fts_cmd")
    fts_sub.add_parser("optimize", help="Optimize all FTS5 indexes")

    # --- events ---
    ev_p = sub.add_parser("events", help="Audit event log")
    ev_p.add_argument("--entity", default=None, help="Filter by entity type (task, epic, story)")
    ev_p.add_argument("--id", default=None, dest="entity_id", help="Filter by entity ID/slug")
    ev_p.add_argument("--limit", type=int, default=50)

    # --- db (v14b-junk-audit-pass: backup hygiene) ---
    db_p = sub.add_parser("db", help="Database hygiene helpers")
    db_sub = db_p.add_subparsers(dest="db_cmd")
    db_prune = db_sub.add_parser(
        "prune",
        help="Delete oldest .tausik/tausik.db.bak.* files keeping the most recent N",
    )
    db_prune.add_argument(
        "--keep",
        type=int,
        default=3,
        help="Number of most-recent backups to keep (default: 3, 0 = delete all)",
    )

    # --- SENAR ops subparsers (delegated) ---
    from project_parser_brain import add_brain
    from project_parser_config import add_config
    from project_parser_ops import (
        add_audit,
        add_dead_end,
        add_doc,
        add_explore,
        add_hygiene,
        add_metrics,
        add_push_ok,
        add_review,
        add_run,
        add_skill,
    )

    add_dead_end(sub)
    add_explore(sub)
    add_audit(sub)
    add_skill(sub)
    add_metrics(sub)
    add_hygiene(sub)
    add_brain(sub)
    add_run(sub)
    add_doc(sub)
    add_review(sub)
    add_config(sub)
    add_push_ok(sub)

    return p
