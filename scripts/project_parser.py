"""TAUSIK argparse parser — CLI command tree."""

from __future__ import annotations

import argparse

from project_parser_errors import SelfCorrectingParser
from project_parser_hierarchy import build_hierarchy_subparsers
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

    # --- epic + story (extracted to project_parser_hierarchy for filesize) ---
    build_hierarchy_subparsers(sub)

    # --- task --- (extracted to project_parser_task.add_task to keep filesize gate)
    add_task(sub)

    # --- team ---
    sub.add_parser("team", help="Team status — tasks by agent")

    # --- session ---
    from project_parser_session import build_session_subparsers

    build_session_subparsers(sub)

    from project_parser_adapts import build_adapt_subparsers
    from project_parser_aidd import build_aidd_subparsers
    from project_parser_role import build_role_subparsers
    from project_parser_specs import build_spec_subparsers
    from project_parser_stack import build_stack_subparsers

    build_stack_subparsers(sub)
    build_role_subparsers(sub)
    build_spec_subparsers(sub)
    build_adapt_subparsers(sub)
    build_aidd_subparsers(sub)
    sub.add_parser("doctor", help="Health check: venv + DB + MCP + skills + drift")

    drift_p = sub.add_parser("drift", help="RENAR drift detectors (schema + TC↔req provenance)")
    drift_p.add_argument(
        "--detector",
        choices=["schema", "provenance", "all"],
        default="all",
        help="Which RENAR drift detector to run (default: all)",
    )

    renar_p = sub.add_parser("renar", help="RENAR conformance self-assessment")
    renar_sub = renar_p.add_subparsers(dest="renar_cmd")
    rc = renar_sub.add_parser(
        "conformance", help="Generate RENAR-CONFORMANCE.yaml from live DB state"
    )
    rc.add_argument(
        "--assessor",
        default=None,
        help="Assessor id (default: config renar_default_assessor -> git user.name -> unknown-assessor)",
    )
    rc.add_argument(
        "--write", action="store_true", help="Write RENAR-CONFORMANCE.yaml to project root"
    )
    re_ = renar_sub.add_parser(
        "export", help="Serialize specs+adapts+conformance to a derived renar/ tree"
    )
    re_.add_argument("--out", default=None, help="Output dir (default: <project_root>/renar/)")
    re_.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if the renar/ tree is stale vs live DB (CI gate)",
    )

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
    mlint = mem_sub.add_parser(
        "lint",
        help="Find contradictions / superseded / stale-file memories. Dry-run unless --apply.",
    )
    mlint.add_argument(
        "--apply",
        action="store_true",
        help="Archive superseded entries (idempotent). Without it: dry-run report.",
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

    # --- receipt (v15-receipt-emit-on-verify) ---
    rcpt_p = sub.add_parser("receipt", help="Signed verify receipts (ed25519)")
    rcpt_sub = rcpt_p.add_subparsers(dest="receipt_cmd")
    rs = rcpt_sub.add_parser(
        "show",
        help="Print + re-verify the latest signed receipt",
        epilog="Example: tausik receipt show --task my-task",
    )
    rs.add_argument("--task", help="Latest receipt for this task slug")
    rs.add_argument("--run", type=int, help="Receipt of a specific verification_run id")
    rs.add_argument("--json", action="store_true", help="Print the raw signed envelope")
    re_ = rcpt_sub.add_parser(
        "export",
        help="Export a portable, self-verifiable receipt artifact",
        epilog="Example: tausik receipt export --task my-task",
    )
    re_.add_argument("--task", help="Latest receipt for this task slug")
    re_.add_argument("--run", type=int, help="Receipt of a specific verification_run id")
    re_.add_argument("--out", help="Output path (default .tausik/receipts/<task>-<sha8>.json)")
    re_.add_argument("--stdout", action="store_true", help="Print artifact instead of writing")
    rv = rcpt_sub.add_parser(
        "verify",
        help="Verify an exported receipt file offline (no DB/keystore)",
        epilog="Example: tausik receipt verify .tausik/receipts/my-task-abc12345.json",
    )
    rv.add_argument("file", help="Path to a tausik-receipt-export/v1 JSON file")
    rv.add_argument("--pub", help="Override key: 'ed25519:<64 hex>' from `tausik key show`")

    # --- serve (v15-nosdk-verify-endpoint) ---
    srv = sub.add_parser(
        "serve",
        help="Stateless HTTP verify endpoint (no MCP/SDK needed)",
        epilog="Example: tausik serve --port 8765",
    )
    srv.add_argument("--host", default="127.0.0.1", help="Bind address (default 127.0.0.1)")
    srv.add_argument("--port", type=int, default=8765)
    srv.add_argument(
        "--yes-expose",
        action="store_true",
        dest="yes_expose",
        help="Confirm a non-localhost bind (endpoint has no auth layer)",
    )

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

    # --- snippet (v15-snippet-ast-detect) ---
    snip_p = sub.add_parser("snippet", help="Code snippet / clone detection")
    snip_sub = snip_p.add_subparsers(dest="snippet_cmd")
    snip_detect = snip_sub.add_parser(
        "detect",
        help="Detect AST clone clusters and store them in the snippets table",
        epilog="Example: tausik snippet detect --path scripts --threshold 12",
    )
    snip_detect.add_argument(
        "--path", default=None, help="File or directory to scan (default: current dir)"
    )
    snip_detect.add_argument(
        "--threshold",
        type=int,
        default=10,
        help="Minimum source-line span for a clone candidate (default: 10)",
    )
    snip_extract = snip_sub.add_parser("extract", help="Publish a snippet to the Brain")
    snip_extract.add_argument("id", type=int, help="Snippet id (from `snippet detect`)")
    snip_extract.add_argument(
        "--scope", choices=("brain",), default="brain", help="Destination (only 'brain')"
    )

    # --- events ---
    ev_p = sub.add_parser("events", help="Audit event log")
    ev_p.add_argument("--entity", default=None, help="Filter by entity type (task, epic, story)")
    ev_p.add_argument("--id", default=None, dest="entity_id", help="Filter by entity ID/slug")
    ev_p.add_argument("--limit", type=int, default=50)
    ev_sub = ev_p.add_subparsers(dest="events_cmd")
    ev_sub.add_parser("seal", help="Seal pending events into the hash-chain")
    ev_sub.add_parser("verify", help="Verify the audit hash-chain (+ ed25519 anchor)")
    ev_sub.add_parser("anchor", help="Sign the current chain head with the project key")

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
