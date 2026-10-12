"""CLI dispatcher for `tausik snippet detect|extract` (v15 snippet system).

`detect` runs the AST clone detector over a path and persists each cluster into
the snippets store (taxonomy_kind='clone'). `extract <id>` sends a stored snippet
to one of TWO destinations, and they are not variants of each other: `--scope
brain` publishes to the cross-project Shared Brain as a `patterns` artifact card
(network, Notion, scrubbed, artifact_taxonomy_kind classified via
brain_snippet_detect), while `--scope global` copies it into the local shared
store `~/.tausik-knowledge/knowledge.db` (no network, no scrubber, no config
required). Kept
separate from the engine (snippet_detect.py) so detection stays pure/testable and
out of the CLI's filesize budget. Idempotent ingest: clusters dedup on content hash.
"""

from __future__ import annotations

from typing import Any

from project_service import ProjectService
from snippet_detect import detect_clones
from snippet_storage import add_snippet, count_snippets, get_snippet


def cmd_snippet(svc: ProjectService, args: Any) -> None:
    sub = getattr(args, "snippet_cmd", None)
    if sub == "extract":
        _cmd_snippet_extract(svc, args)
        return
    if sub != "detect":
        print(
            "Usage: tausik snippet {detect [--path X] [--threshold N] | "
            "extract <id> --scope brain|global}"
        )
        return
    _cmd_snippet_detect(svc, args)


def _cmd_snippet_detect(svc: ProjectService, args: Any) -> None:
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
    ingested: list[tuple[int, int]] = []  # (snippet_id, occurrences)
    for cluster in result.clusters:
        members_str = "; ".join(f"{f}:{s}-{e}" for f, s, e in cluster.members)
        sid = add_snippet(
            conn,
            code_hash=cluster.hash,
            language=cluster.language,
            code=cluster.code,
            source_file=cluster.members[0][0],
            source_lines=members_str,
            taxonomy_kind="clone",
            fts_rank=float(len(cluster.members)),
        )
        ingested.append((sid, len(cluster.members)))
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


def _cmd_snippet_extract(svc: ProjectService, args: Any) -> None:
    snippet_id = getattr(args, "id", None)
    snippet = get_snippet(svc.be._conn, int(snippet_id)) if snippet_id is not None else None
    if snippet is None:
        print(f"Snippet #{snippet_id} not found.")
        return
    # The shared store is a file in this user's home: no network and
    # deliberately no scrubber. Redaction belongs at the boundary where
    # knowledge leaves the machine — not here, where scrubbing would corrupt a
    # snippet (a redacted identifier is a wrong identifier) to buy privacy
    # against oneself.
    from knowledge_write import write_snippet

    print(
        write_snippet(
            code=snippet["code"],
            language=snippet["language"],
            source_file=snippet.get("source_file"),
            source_lines=snippet.get("source_lines"),
            taxonomy_kind=snippet.get("taxonomy_kind"),
        )
    )


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
