"""CLI dispatcher for `tausik snippet detect` (v15-snippet-ast-detect).

Runs the AST clone detector over a path and persists each cluster into the
snippets store (taxonomy_kind='clone'). Kept separate from the engine
(snippet_detect.py) so detection stays pure/testable and out of the CLI's
filesize budget. Idempotent: clusters dedup on their content hash, so a re-run
over unchanged sources writes nothing new.
"""

from __future__ import annotations

from typing import Any

from project_service import ProjectService
from snippet_detect import detect_clones
from snippet_storage import add_snippet, count_snippets


def cmd_snippet(svc: ProjectService, args: Any) -> None:
    sub = getattr(args, "snippet_cmd", None)
    if sub != "detect":
        print("Usage: tausik snippet detect [--path X] [--threshold N]")
        return

    path = getattr(args, "path", None) or "."
    # Respect an explicit --threshold (incl. 0); only default when truly absent.
    threshold = getattr(args, "threshold", None)
    if threshold is None:
        threshold = 10

    result = detect_clones(path, min_lines=threshold)
    conn = svc.be._conn

    # add_snippet is INSERT-OR-IGNORE (dedup on hash), so a per-cluster counter
    # would overstate writes on a re-run. Report actual new rows via a before/
    # after delta — honest output (CLAUDE.md: zero tolerance for silent fiction).
    before = count_snippets(conn)
    for cluster in result.clusters:
        members_str = "; ".join(f"{f}:{s}-{e}" for f, s, e in cluster.members)
        add_snippet(
            conn,
            code_hash=cluster.hash,
            language=cluster.language,
            code=cluster.code,
            source_file=cluster.members[0][0],
            source_lines=members_str,
            taxonomy_kind="clone",
            fts_rank=float(len(cluster.members)),
        )
    written = count_snippets(conn) - before

    print(f"Scanned {result.scanned} file(s) under '{path}' (threshold {threshold} lines).")
    if result.skipped:
        print(f"  Skipped {len(result.skipped)} unparseable file(s).")
    if not result.clusters:
        print("No clone clusters found.")
        return
    print(f"Found {len(result.clusters)} clone cluster(s); wrote {written} new to snippets:")
    for cluster in result.clusters[:20]:
        locs = ", ".join(f"{f}:{s}-{e}" for f, s, e in cluster.members)
        print(f"  [{len(cluster.members)}x] {cluster.hash[:12]}  {locs}")
    if len(result.clusters) > 20:
        print(f"  ... and {len(result.clusters) - 20} more.")
