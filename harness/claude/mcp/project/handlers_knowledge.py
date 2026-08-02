"""MCP handlers for the knowledge domain — memory, its graph, decisions, dead ends.

Split out of handlers.py by mcp-handlers-god-module-split. Follows the
convention already set by handlers_spec.py / handlers_adapt.py: the module owns
its handlers AND the slice of the dispatch table that names them, and
handlers.py merges it with `_DISPATCH.update(...)`.

Memory, decisions and dead ends live together because they are one store with
one write path: `_coerce_tags` is shared by memory writes and dead ends, and
all three read back through the same search and graph surface.
"""

from __future__ import annotations

from typing import Any

from handlers_render import render_list


def _coerce_tags(raw: Any) -> list[str] | None:
    """Coerce tags from string or list to list[str].

    MCP clients may serialize array params as JSON strings instead of arrays.
    This handles both cases gracefully.
    """
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        import json as _json

        try:
            parsed = _json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except (ValueError, TypeError):
            pass
        return [t.strip() for t in raw.split(",") if t.strip()]
    return None


def _do_memory_add(svc: Any, args: dict) -> str:
    return svc.memory_add(
        args["type"],
        args["title"],
        args["content"],
        _coerce_tags(args.get("tags")),
        args.get("task_slug"),
    )


def _do_memory_list(svc: Any, args: dict) -> str:
    memories = svc.memory_list(
        args.get("type"),
        args.get("limit", 50),
        include_archived=bool(args.get("include_archived", False)),
    )
    return render_list(
        memories,
        lambda r: (
            f"#{r['id']} [{r['type']}]{' [archived]' if r.get('archived_at') else ''} {r['title']}"
        ),
        "No memories.",
    )


def _do_memory_show(svc: Any, args: dict) -> str:
    m = svc.memory_show(args["id"])
    return f"#{m['id']} [{m['type']}] {m['title']}\n{m['content']}"


def _do_memory_archive(svc: Any, args: dict) -> str:
    result = svc.memory_archive(args["before"], confirm=bool(args.get("confirm", False)))
    days = result["before_days"]
    if result["applied"]:
        return f"Archived {result['archived']} memory rows older than {days} days."
    cands = result.get("candidates", [])
    if not cands:
        return f"No unarchived rows older than {days} days."
    head = (
        f"Dry-run: {len(cands)} rows older than {days} days. Re-run with confirm=true to apply.\n"
    )
    sample = "\n".join(f"  #{r['id']} [{r['type']}] {r['title']}" for r in cands[:20])
    tail = f"\n  ... +{len(cands) - 20} more" if len(cands) > 20 else ""
    return head + sample + tail


def _do_memory_dedupe(svc: Any, args: dict) -> str:
    threshold = float(args.get("threshold", 0.85))
    n = int(args.get("limit", 200))
    suggestions = svc.memory_dedupe(threshold=threshold, n=n)
    if not suggestions:
        return f"No pairs above threshold {threshold:.2f} in the last {n} unarchived rows."
    lines = [f"{len(suggestions)} pair(s) above {threshold:.2f}:"]
    for s in suggestions:
        ta = s["title_a"][:40]
        tb = s["title_b"][:40]
        lines.append(
            f'  {s["ratio"]:.3f} [{s["type"]}] #{s["id_a"]} "{ta}" <-> #{s["id_b"]} "{tb}"'
        )
    return "\n".join(lines)


def _do_memory_lint(svc: Any, args: dict) -> str:
    result = svc.memory_lint(apply=bool(args.get("apply", False)))
    findings = result["findings"]
    if not findings:
        return "Memory lint: no contradictions, superseded, or stale-file issues found."
    if result["applied"]:
        head = (
            f"{result['count']} finding(s); archived {result['archived']} superseded "
            "entry(ies). Contradictions / stale-file hits are advisory:"
        )
    else:
        head = f"{result['count']} finding(s) (dry-run; apply=true archives superseded):"
    lines = [head]
    for f in findings:
        title = (f["title"] or "")[:50]
        lines.append(f'  #{f["id"]} [{f["kind"]}] {f["reason"]} "{title}"')
    return "\n".join(lines)


def _format_memory_hit(r: dict) -> str:
    """One line of a memory-search result.

    Rows sourced from cross-project `cq` knowledge carry no id — there is no
    row in `memory` to address. Printing `#None` would invite exactly the
    round-trip into `memory_show` that has no target, so the address is omitted
    entirely for them.
    """
    address = "" if r.get("id") is None else f"#{r['id']} "
    archived = " [archived]" if r.get("archived_at") else ""
    return f"{address}[{r['type']}]{archived} {r['title']}: {r['content'][:100]}"


def _do_memory_search(svc: Any, args: dict) -> str:
    results = svc.memory_search(
        args["query"],
        include_archived=bool(args.get("include_archived", False)),
    )
    rendered = render_list(results, _format_memory_hit, "No memories found.")

    # The shared store's degradation notice has to reach THIS surface, not only
    # the CLI. CLAUDE.md tells agents to prefer MCP, so a warning that exists
    # only in `tausik memory search` is a warning the primary reader never sees —
    # and an incomplete result list that says nothing is exactly the silent
    # failure the shared-read path was written to rule out.
    #
    # Importable because `handlers.py` puts the scripts directory on sys.path at
    # import time, and this module is only ever reached through it. Stated as the
    # actual reason: an earlier version of this comment claimed the path was
    # settled by `svc.memory_search` having already imported the module, which
    # happens to be true here and would have been the wrong thing to rely on.
    # Kept local rather than top-level so the module has no script-layer
    # dependency at import time.
    from knowledge_read import pop_last_warning

    warning = pop_last_warning()
    return f"{rendered}\n⚠ {warning}" if warning else rendered


def _do_memory_block(svc: Any, args: dict) -> str:
    output = svc.memory_block(
        max_decisions=args.get("max_decisions", 5),
        max_conventions=args.get("max_conventions", 10),
        max_deadends=args.get("max_deadends", 5),
        max_lines=args.get("max_lines", 50),
    )
    return output or "(memory block empty — no decisions, conventions, or dead ends yet)"


def _do_memory_compact(svc: Any, args: dict) -> str:
    output = svc.memory_compact(last_n=args.get("last_n", 50))
    return output or "No task logs yet."


def _do_memory_link(svc: Any, args: dict) -> str:
    return svc.memory_link(
        args["source_type"],
        args["source_id"],
        args["target_type"],
        args["target_id"],
        args["relation"],
        args.get("confidence", 1.0),
        args.get("created_by"),
    )


def _do_memory_related(svc: Any, args: dict) -> str:
    results = svc.memory_related(
        args["node_type"],
        args["node_id"],
        args.get("max_hops", 2),
        args.get("include_invalid", False),
    )
    if not results:
        return "No related nodes found."
    lines = []
    for r in results:
        rec = r.get("record", {})
        label = rec.get("title", rec.get("decision", ""))[:60]
        lines.append(
            f"[{r['depth']} hop] {r['node_type']}#{r['node_id']} --[{r.get('via_relation', '')}]--> {label}"
        )
    return "\n".join(lines)


def _do_memory_graph(svc: Any, args: dict) -> str:
    edges = svc.memory_graph(
        args.get("node_type"),
        args.get("node_id"),
        args.get("relation"),
        args.get("include_invalid", False),
        args.get("limit", 50),
    )
    if not edges:
        return "No edges found."
    lines = []
    for e in edges:
        valid = "" if not e.get("valid_to") else " [invalid]"
        lines.append(
            f"#{e['id']} {e['source_type']}#{e['source_id']} --[{e['relation']}]--> {e['target_type']}#{e['target_id']}{valid}"
        )
    return "\n".join(lines)


def _do_decisions_list(svc: Any, args: dict) -> str:
    decs = svc.decisions(args.get("limit", 20))
    return render_list(decs, lambda d: f"#{d['id']} {d['decision'][:80]}", "No decisions.")


def _do_dead_end(svc: Any, args: dict) -> str:
    return svc.dead_end(
        args["approach"],
        args["reason"],
        tags=_coerce_tags(args.get("tags")),
        task_slug=args.get("task_slug"),
    )


KNOWLEDGE_HANDLERS = {
    # --- Memory ---
    "tausik_memory_add": _do_memory_add,
    "tausik_memory_list": _do_memory_list,
    "tausik_memory_show": _do_memory_show,
    "tausik_memory_delete": lambda svc, args: svc.memory_delete(args["id"]),
    "tausik_memory_search": _do_memory_search,
    "tausik_memory_block": _do_memory_block,
    "tausik_memory_compact": _do_memory_compact,
    "tausik_memory_archive": _do_memory_archive,
    "tausik_memory_dedupe": _do_memory_dedupe,
    "tausik_memory_lint": _do_memory_lint,
    # --- Graph memory ---
    "tausik_memory_link": _do_memory_link,
    "tausik_memory_unlink": lambda svc, args: svc.memory_unlink(
        args["edge_id"], args.get("replacement_id")
    ),
    "tausik_memory_related": _do_memory_related,
    "tausik_memory_graph": _do_memory_graph,
    # --- Decisions ---
    "tausik_decide": lambda svc, args: svc.decide(
        args["decision"], args.get("task_slug"), args.get("rationale")
    ),
    "tausik_decisions_list": _do_decisions_list,
    # --- Dead ends ---
    "tausik_dead_end": _do_dead_end,
}
