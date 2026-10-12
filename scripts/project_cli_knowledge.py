"""Reading and writing what the project knows: memory, shared store, dead ends.

One home rather than three: a dead end IS a memory of a particular type, and the
shared store is the same knowledge with a wider scope. The helper that builds the
publication blocklists travels with the command that uses it.
"""

from __future__ import annotations

import os
from typing import Any
from project_service import ProjectService
from render_memory import (
    memory_archive_lines,
    memory_dedupe_lines,
    memory_graph_lines,
    memory_lint_lines,
    memory_list_lines,
    memory_related_lines,
    memory_search_lines,
    memory_show_lines,
)


def _publication_blocklists() -> tuple[list[str], list[str]]:
    """What the boundary must not let through by name: this project's directory
    name, plus whatever `publication.project_names` and
    `publication.private_url_patterns` list in the config. The registry that used
    to union every project on the machine left with the Notion transport
    (decision #358); the config is the explicit replacement."""

    from project_config import find_tausik_dir, load_config

    names: list[str] = []
    try:
        names.append(os.path.basename(os.path.dirname(os.path.abspath(find_tausik_dir()))))
    except Exception:  # noqa: BLE001,S110 — no project here: the config lists are still honoured
        pass
    try:
        section = load_config().get("publication") or {}
    except Exception:  # noqa: BLE001 — an unreadable config must not turn redaction off silently
        section = {}
    if isinstance(section, dict):
        names += [n for n in section.get("project_names", []) or [] if isinstance(n, str)]
        patterns = [p for p in section.get("private_url_patterns", []) or [] if isinstance(p, str)]
    else:
        patterns = []
    return [n for n in names if n.strip()], patterns


def cmd_knowledge(svc: ProjectService, args: Any) -> None:
    """`tausik knowledge export|restore` — back up the shared store, or rebuild it.

    Takes `svc` it does not use, to match the dispatcher's uniform signature; the
    shared store is per-user, not per-project, and deliberately reachable without
    one.
    """
    from knowledge_export import export_shared_knowledge, restore_shared_knowledge

    sub = getattr(args, "knowledge_cmd", None)
    if sub == "export":
        redacted = bool(getattr(args, "redacted", False))
        names, url_patterns = _publication_blocklists() if redacted else ((), ())
        counts = export_shared_knowledge(
            args.to, redacted=redacted, project_names=names, private_url_patterns=url_patterns
        )
        records = {k: v for k, v in counts.items() if not k.startswith("redacted_")}
        total = sum(records.values())
        detail = ", ".join(f"{n} {name}" for name, n in records.items())
        print(f"Backed up {total} record(s) to {args.to} ({detail}).")
        if redacted:
            hits = ", ".join(
                f"{n} {k.removeprefix('redacted_')}"
                for k, n in counts.items()
                if k.startswith("redacted_")
            )
            print(f"Redacted: {hits or 'nothing matched'} — the manifest records it.")
        return
    if sub == "restore":
        counts = restore_shared_knowledge(args.from_dir)
        total = sum(counts.values())
        detail = ", ".join(f"{n} {name}" for name, n in counts.items())
        print(f"Restored {total} record(s) from {args.from_dir} ({detail}).")
        return
    if sub == "promote":
        from knowledge_promote import preview, promote

        kind, rid = ("memory", args.memory) if args.memory else ("decision", args.decision)
        print("\n".join(preview(svc, kind, rid)))
        print(promote(svc, kind, rid) if args.yes else "Nothing written: add --yes to copy it.")
        return
    if sub == "import-brain":
        from knowledge_import import format_counts, import_from_brain_mirror

        counts = import_from_brain_mirror(dry_run=bool(getattr(args, "dry_run", False)))
        verb = "Would import" if getattr(args, "dry_run", False) else "Imported"
        print(f"{verb}: {format_counts(counts)}.")
        return
    print(
        "Usage: tausik knowledge {export --to <dir> | restore --from <dir> | "
        "promote --memory|--decision ID [--yes] | import-brain [--dry-run]}"
    )


def cmd_memory(svc: ProjectService, args: Any) -> None:
    c = args.memory_cmd
    if c == "add":
        print(
            svc.memory_add(
                args.mem_type,
                args.title,
                args.content,
                args.tags,
                args.task,
                getattr(args, "to_global", False),
                getattr(args, "provenance", "inferred"),
            )
        )
    elif c == "list":
        print(
            "\n".join(
                memory_list_lines(
                    svc,
                    args.mem_type,
                    args.limit,
                    include_archived=getattr(args, "include_archived", False),
                )
            )
        )
    elif c == "search":
        print(
            "\n".join(
                memory_search_lines(
                    svc,
                    args.query,
                    include_archived=getattr(args, "include_archived", False),
                )
            )
        )
    elif c == "show":
        print("\n".join(memory_show_lines(svc, args.id)))
    elif c == "delete":
        print(svc.memory_delete(args.id))
    elif c == "edit":
        # A module function rather than a service method: both god classes are capped by the
        # class-surface ratchet, which may only shrink, and one caller is not an argument for
        # a public member.
        from memory_edit import edit_memory

        print(edit_memory(svc, args.id, args.title, args.content))
    elif c == "link":
        print(
            svc.memory_link(
                args.source_type,
                args.source_id,
                args.target_type,
                args.target_id,
                args.relation,
                args.confidence,
                args.created_by,
            )
        )
    elif c == "unlink":
        print(svc.memory_unlink(args.edge_id, args.replacement))
    elif c == "related":
        print(
            "\n".join(
                memory_related_lines(
                    svc, args.node_type, args.node_id, args.hops, args.include_invalid
                )
            )
        )
    elif c == "graph":
        if getattr(args, "format", "table") == "mermaid":
            from graph_mermaid import render_memory_graph  # graph-mermaid-render

            print(render_memory_graph(svc), end="")
            return
        print(
            "\n".join(
                memory_graph_lines(
                    svc,
                    args.node_type,
                    args.node_id,
                    args.relation,
                    args.include_invalid,
                    args.limit,
                )
            )
        )
    elif c == "block":
        output = svc.memory_block(
            max_decisions=args.max_decisions,
            max_conventions=args.max_conventions,
            max_deadends=args.max_deadends,
            max_lines=args.max_lines,
        )
        if output:
            print(output)
    elif c == "compact":
        output = svc.memory_compact(last_n=args.last_n)
        print(output if output else "No task logs yet.")
    elif c == "archive":
        print("\n".join(memory_archive_lines(svc, args.before, confirm=bool(args.confirm))))
    elif c == "hygiene":
        # Module functions, same reason as `edit` above: the class-surface
        # ratchet may only shrink, and one caller is not a public member.
        from memory_hygiene import apply_layers, report_lines, revert_last

        if getattr(args, "revert", False):
            print(revert_last(svc.be))
        elif getattr(args, "yes", False):
            print(apply_layers(svc.be))
        else:
            print("\n".join(report_lines(svc.be)))
    elif c == "pin" or c == "unpin":
        from memory_hygiene import set_pinned

        print(set_pinned(svc.be, args.id, pinned=(c == "pin")))
    elif c == "dedupe":
        print("\n".join(memory_dedupe_lines(svc, threshold=args.threshold, limit=args.limit)))
    elif c == "lint":
        print("\n".join(memory_lint_lines(svc, apply=bool(getattr(args, "apply", False)))))


def cmd_dead_end(svc: ProjectService, args: Any) -> None:
    print(svc.dead_end(args.approach, args.reason, args.tags, args.task))


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
