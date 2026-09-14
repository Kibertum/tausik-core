"""The text of the memory commands, rendered ONCE for both surfaces.

Every command in this family was implemented twice, and every MCP copy showed
less than the CLI. The losses were not decisions; they are what a second
implementation does when the first one grows:

* `list` and `search` — no tags. The two stores spell a tag list differently,
  which is why `render_tags` exists at all; the handler had neither the function
  nor the field.
* `search` — no `origin_project`, so a hit from the shared cross-project store
  was indistinguishable from one of this project's own.
* `show` — no created-at, no tags, no task. The MCP answer was the title and the
  body, and the agent reading it could not tell when the note was written or
  what it belonged to.
* `graph` — no confidence and no invalidation date, the two fields that say how
  much an edge is worth and whether it still holds.
* `archive`, `dedupe`, `lint` — the CLI says what to do next (`--confirm`,
  `memory delete <id>`, `--apply`); the handler printed the finding and stopped.

The CLI rendering is canonical here, indentation included: it is the richer of
the two everywhere they differ, and a surface that starts showing MORE is a safe
change while one that shows less silently removes evidence.

Lines, not printing: the CLI prints them, the MCP handler joins them.
"""

from __future__ import annotations

from typing import Any

from knowledge_tags import load_tags

#: How many dry-run candidates `archive` names before it elides. The MCP copy
#: used 20 and the CLI 50; one number now, and the elision stays visible.
_ARCHIVE_SAMPLE = 50


def render_tags(raw: str | None) -> str:
    """Tags as a display suffix, empty when there are none.

    Reads through `knowledge_tags.load_tags` rather than `json.loads` so one
    function serves rows from the project store and the shared store alike — the
    two spell a tag list differently, and a reader written for either would have
    shown the other as having no tags.
    """
    tags = load_tags(raw)
    return " " + ", ".join(tags) if tags else ""


def memory_list_lines(
    svc: Any, mem_type: str | None, limit: int, include_archived: bool = False
) -> list[str]:
    rows = svc.memory_list(mem_type, limit, include_archived=include_archived)
    if not rows:
        return ["  (no memories)"]
    return [
        f"  #{r['id']} [{r['type']}] {r['title']}{render_tags(r.get('tags'))}"
        f"{' [archived]' if r.get('archived_at') else ''}"
        for r in rows
    ]


def memory_search_lines(svc: Any, query: str, include_archived: bool = False) -> list[str]:
    """Search hits, plus the shared store's degradation notice when there is one.

    The notice has to reach BOTH surfaces. CLAUDE.md tells agents to prefer MCP,
    so a warning that existed only in the CLI was a warning the primary reader
    never saw — and an incomplete result list that says nothing is exactly the
    silent failure the shared-read path was written to rule out. It is printed
    AFTER the results, not instead of them: the project's own answers are still
    valid, and what the reader needs to know is that the list is INCOMPLETE.
    """
    from knowledge_read import pop_last_warning

    rows = svc.memory_search(query, include_archived=include_archived)
    lines = []
    for r in rows:
        # cq and shared-store rows have no id — knowledge with no `memory` row
        # HERE to address. Omit the address rather than print `#None`, and never
        # print the shared store's own id: it would point at a different, real,
        # local record.
        address = "" if r.get("id") is None else f"#{r['id']} "
        archived = " [archived]" if r.get("archived_at") else ""
        origin = f"  ({r['origin_project']})" if r.get("origin_project") else ""
        lines.append(
            f"  {address}[{r['type']}] {r['title']}{render_tags(r.get('tags'))}{archived}{origin}"
        )
    if not lines:
        lines = ["  No results."]
    warning = pop_last_warning()
    if warning:
        lines.append(f"  ⚠ {warning}")
    return lines


def memory_show_lines(svc: Any, memory_id: int) -> list[str]:
    row = svc.memory_show(memory_id)
    lines = [
        f"#{row['id']} [{row['type']}] {row['title']}",
        f"Created: {row.get('created_at', '')}",
    ]
    shown = load_tags(row.get("tags"))
    if shown:
        lines.append(f"Tags: {', '.join(shown)}")
    if row.get("task_slug"):
        lines.append(f"Task: {row['task_slug']}")
    lines.append("")
    lines.append(row["content"])
    return lines


def memory_related_lines(
    svc: Any,
    node_type: str,
    node_id: int,
    max_hops: int = 2,
    include_invalid: bool = False,
) -> list[str]:
    results = svc.memory_related(node_type, node_id, max_hops, include_invalid)
    if not results:
        return ["  No related nodes found."]
    lines = []
    for r in results:
        record = r.get("record", {})
        label = record.get("title", record.get("decision", ""))[:60]
        lines.append(
            f"  [{r['depth']} hop] {r['node_type']}#{r['node_id']} "
            f"--[{r.get('via_relation', '')}]--> {label}"
        )
    return lines


def memory_graph_lines(
    svc: Any,
    node_type: str | None = None,
    node_id: int | None = None,
    relation: str | None = None,
    include_invalid: bool = False,
    limit: int = 50,
) -> list[str]:
    edges = svc.memory_graph(node_type, node_id, relation, include_invalid, limit)
    if not edges:
        return ["  No edges found."]
    lines = []
    for e in edges:
        valid = "" if not e.get("valid_to") else f" [invalid {e['valid_to'][:10]}]"
        confidence = f" ({e['confidence']:.0%})" if e["confidence"] < 1.0 else ""
        lines.append(
            f"  #{e['id']} {e['source_type']}#{e['source_id']} "
            f"--[{e['relation']}]--> {e['target_type']}#{e['target_id']}"
            f"{confidence}{valid}"
        )
    return lines


def memory_archive_lines(svc: Any, before: Any, confirm: bool = False) -> list[str]:
    result = svc.memory_archive(before, confirm=confirm)
    days = result["before_days"]
    if result["applied"]:
        return [
            f"Memory archive: archived {result['archived']} rows older than "
            f"{days} days. Hidden from `memory list` by default; use "
            f"`--include-archived` to see them."
        ]
    candidates = result.get("candidates", [])
    if not candidates:
        return [f"Memory archive (dry-run): no unarchived rows older than {days} days."]
    lines = [
        f"Memory archive (dry-run): {len(candidates)} rows older than {days} days "
        f"would be archived. Re-run with `--confirm` to apply."
    ]
    for r in candidates[:_ARCHIVE_SAMPLE]:
        title = r.get("title") or ""
        if len(title) > 60:
            title = title[:57] + "..."
        lines.append(f"  #{r['id']:<5} [{r['type']:<10}] {r['created_at']}  {title}")
    if len(candidates) > _ARCHIVE_SAMPLE:
        lines.append(f"  ... and {len(candidates) - _ARCHIVE_SAMPLE} more")
    return lines


def memory_dedupe_lines(svc: Any, threshold: float = 0.85, limit: int = 200) -> list[str]:
    suggestions = svc.memory_dedupe(threshold=threshold, n=limit)
    if not suggestions:
        return [
            f"Memory dedupe: no pairs above threshold {threshold:.2f} "
            f"in the last {limit} unarchived rows."
        ]
    lines = [
        f"Memory dedupe: {len(suggestions)} pair(s) above {threshold:.2f} similarity. "
        "Review then merge with `memory delete <id>` after consolidating."
    ]
    for s in suggestions:
        lines.append(
            f'  {s["ratio"]:.3f} [{s["type"]:<10}] #{s["id_a"]} "{s["title_a"][:40]}"'
            f'  ↔  #{s["id_b"]} "{s["title_b"][:40]}"'
        )
    return lines


def memory_lint_lines(svc: Any, apply: bool = False) -> list[str]:
    result = svc.memory_lint(apply=apply)
    findings = result["findings"]
    if not findings:
        return ["Memory lint: no contradictions, superseded, or stale-file issues found."]
    if result["applied"]:
        head = (
            f"Memory lint: {result['count']} finding(s); archived "
            f"{result['archived']} superseded entry(ies). Contradictions and "
            f"stale-file hits are advisory — review them below."
        )
    else:
        head = (
            f"Memory lint (dry-run): {result['count']} finding(s). "
            f"Re-run with `--apply` to archive superseded entries."
        )
    lines = [head]
    for f in findings:
        lines.append(
            f'  #{f["id"]:<5} [{f["kind"]:<11}] {f["reason"]}  "{(f["title"] or "")[:50]}"'
        )
    return lines
