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
    """Transport. The copy this replaces showed no tags."""
    from render_memory import memory_list_lines

    return "\n".join(
        memory_list_lines(
            svc,
            args.get("type"),
            args.get("limit", 50),
            include_archived=bool(args.get("include_archived", False)),
        )
    )


def _do_memory_show(svc: Any, args: dict) -> str:
    """Transport. The copy this replaces dropped created-at, tags and task."""
    from render_memory import memory_show_lines

    return "\n".join(memory_show_lines(svc, args["id"]))


def _do_memory_archive(svc: Any, args: dict) -> str:
    from render_memory import memory_archive_lines

    return "\n".join(
        memory_archive_lines(svc, args["before"], confirm=bool(args.get("confirm", False)))
    )


def _do_memory_dedupe(svc: Any, args: dict) -> str:
    from render_memory import memory_dedupe_lines

    return "\n".join(
        memory_dedupe_lines(
            svc,
            threshold=float(args.get("threshold", 0.85)),
            limit=int(args.get("limit", 200)),
        )
    )


def _do_memory_lint(svc: Any, args: dict) -> str:
    from render_memory import memory_lint_lines

    return "\n".join(memory_lint_lines(svc, apply=bool(args.get("apply", False))))


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
    """Transport. The copy this replaces showed no tags and no origin project,
    so a hit from the shared cross-project store looked like one of our own."""
    from render_memory import memory_search_lines

    return "\n".join(
        memory_search_lines(
            svc,
            args["query"],
            include_archived=bool(args.get("include_archived", False)),
        )
    )


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
    from render_memory import memory_related_lines

    return "\n".join(
        memory_related_lines(
            svc,
            args["node_type"],
            args["node_id"],
            args.get("max_hops", 2),
            args.get("include_invalid", False),
        )
    )


def _do_memory_graph(svc: Any, args: dict) -> str:
    """Transport. The copy this replaces dropped edge confidence and the date an
    edge stopped holding — the two fields that say what an edge is worth."""
    from render_memory import memory_graph_lines

    return "\n".join(
        memory_graph_lines(
            svc,
            args.get("node_type"),
            args.get("node_id"),
            args.get("relation"),
            args.get("include_invalid", False),
            args.get("limit", 50),
        )
    )


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
