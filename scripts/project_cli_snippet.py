"""CLI dispatcher for `tausik snippet detect|extract` (v15 snippet system).

`detect` runs the AST clone detector over a path and persists each cluster into
the snippets store (taxonomy_kind='clone'). `extract <id> --scope brain` reads a
stored snippet and publishes it to the cross-project Shared Brain as a `patterns`
artifact card (artifact_taxonomy_kind classified via brain_snippet_detect). Kept
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
            "Usage: tausik snippet {detect [--path X] [--threshold N] | extract <id> --scope brain}"
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
    _maybe_propose_brain_extract(ingested)


def _maybe_propose_brain_extract(ingested: list[tuple[int, int]]) -> None:
    """Advisory: suggest publishing high-occurrence clusters to the brain.

    Opt-in — only fires when brain is enabled AND a positive integer
    `brain.auto_propose_snippet_threshold` is configured. Never writes anything;
    just nudges the operator toward `snippet extract --scope brain`.
    """
    try:
        from brain_config import load_brain

        brain = load_brain()
        thr = brain.get("auto_propose_snippet_threshold")
        if not brain.get("enabled") or not isinstance(thr, int) or thr <= 0:
            return
        hot = [(sid, occ) for sid, occ in ingested if occ >= thr]
        if not hot:
            return
        print(f"\nBrain: {len(hot)} cluster(s) reused >= {thr}x — consider sharing:")
        for sid, occ in hot[:10]:
            print(f"  tausik snippet extract {sid} --scope brain  ({occ}x)")
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        # Advisory only — a brain-config hiccup must never break `detect`.
        return


def _snippet_to_pattern_card(snippet: dict[str, Any]) -> dict[str, Any]:
    """Build a brain `patterns` artifact card from a stored snippet row.

    The classifier (brain_snippet_detect.detect_artifact_kind) picks
    snippet|pattern from the code itself; falls back to 'snippet' since the row
    is, by construction, reusable code.
    """
    from brain_snippet_detect import detect_artifact_kind

    code = snippet.get("code") or ""
    language = snippet.get("language") or "text"
    source = snippet.get("source_file") or "unknown"
    occurrences = int(snippet.get("fts_rank") or 0)
    fenced = f"```{language}\n{code}\n```"
    kind = detect_artifact_kind({"example": fenced, "description": code}) or "snippet"
    return {
        "name": f"{language} snippet: {source}",
        "description": (
            f"Reusable {language} snippet detected as a clone cluster "
            f"({occurrences} occurrence(s)); source {source}."
        ),
        "when_to_use": f"Reuse instead of re-implementing this {language} logic.",
        "example": fenced,
        "stack": [language],
        "artifact_taxonomy_kind": kind,
    }


def _cmd_snippet_extract(svc: ProjectService, args: Any) -> None:
    snippet_id = getattr(args, "id", None)
    scope = getattr(args, "scope", None) or "brain"
    snippet = get_snippet(svc.be._conn, int(snippet_id)) if snippet_id is not None else None
    if snippet is None:
        print(f"Snippet #{snippet_id} not found.")
        return
    if scope != "brain":
        print(f"Unsupported scope '{scope}'. Only --scope brain is supported.")
        return

    import sys

    from brain_mcp_write import store_record
    from brain_runtime import open_brain_deps
    from brain_store_format import format_store_result

    # open_brain_deps opens SQLite + builds a Notion HTTP client; store_record does
    # network I/O. Wrap both so a DB/network/import failure is a friendly message,
    # not a raw traceback (matches the defensive style of the detect path).
    try:
        conn, client, cfg = open_brain_deps()
        if not cfg.get("enabled") or conn is None:
            print("Brain not configured — enable it with `tausik brain init` first.")
            return
        if client is None:
            print(
                "Brain integration token is not set in env "
                "(`brain.notion_integration_token_env`). Set it and retry."
            )
            return
        fields = _snippet_to_pattern_card(snippet)
        result = store_record(client, conn, "patterns", fields, cfg)
    except Exception as e:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        print(f"Brain error: {e}", file=sys.stderr)
        return
    print(format_store_result(result, "patterns"))
