"""TAUSIK CLI handlers — memory, gates, skill, fts, update-claudemd commands."""

from __future__ import annotations

from typing import Any

from project_service import ProjectService

# One renderer per memory command, shared with the MCP handlers. Every one of
# these was implemented twice, and every MCP copy had fallen behind this one.
from render_memory import (
    memory_archive_lines,
    memory_dedupe_lines,
    memory_graph_lines,
    memory_lint_lines,
    memory_list_lines,
    memory_related_lines,
    memory_search_lines,
    memory_show_lines,
    render_tags,
)


#: The tag suffix moved to `render_memory` with the commands that use it. The
#: old private name stays as an alias rather than a second body: callers that
#: import it by that name keep working, and there is still ONE implementation.
_render_tags = render_tags


def _publication_blocklists() -> tuple[list[str], list[str]]:
    """What the boundary must not let through by name: this project's directory
    name, plus whatever `publication.project_names` and
    `publication.private_url_patterns` list in the config. The registry that used
    to union every project on the machine left with the Notion transport
    (decision #358); the config is the explicit replacement."""
    import os

    from project_config import find_tausik_dir, load_config

    names: list[str] = []
    try:
        names.append(os.path.basename(os.path.dirname(os.path.abspath(find_tausik_dir()))))
    except Exception:  # noqa: BLE001 — no project here: the config lists are still honoured
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
    if sub == "import-brain":
        from knowledge_import import format_counts, import_from_brain_mirror

        counts = import_from_brain_mirror(dry_run=bool(getattr(args, "dry_run", False)))
        verb = "Would import" if getattr(args, "dry_run", False) else "Imported"
        print(f"{verb}: {format_counts(counts)}.")
        return
    print(
        "Usage: tausik knowledge {export --to <dir> | restore --from <dir> | "
        "import-brain [--dry-run]}"
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
    elif c == "dedupe":
        print("\n".join(memory_dedupe_lines(svc, threshold=args.threshold, limit=args.limit)))
    elif c == "lint":
        print("\n".join(memory_lint_lines(svc, apply=bool(getattr(args, "apply", False)))))


def cmd_update_claudemd(svc: ProjectService, args: Any) -> None:
    """Update <!-- DYNAMIC:START --> section in CLAUDE.md."""
    import os

    # Both the block AND the file lookup live in claudemd_state, shared with the
    # MCP handler. Each side used to carry its own copy, and the copies drifted
    # silently — the MCP one lost the memory tail and the AGENTS.md refresh
    # (mcp-update-claudemd-erases-the-memory-tail).
    from claudemd_state import build_dynamic_state, resolve_claudemd, resolve_project_dir

    # Адрес выводится ИЗ БАЗЫ, а не из cwd. Здесь стояло `os.getcwd()` в обеих
    # строках — тот же дефект, что в MCP-обработчике: содержимое из `svc`, адрес
    # из текущего каталога. Заодно это чинит запуск из подкаталога проекта:
    # раньше `resolve_claudemd(os.getcwd())` там не находил файла, хотя база
    # находилась подъёмом (claudemd-dynamic-block-wiped-to-an-empty-project).
    # Явный `--claudemd` уважается: это высказанное намерение пользователя.
    project_dir = resolve_project_dir(svc)
    if project_dir is None and not args.claudemd:
        print(
            "Error: cannot tell which project this database describes "
            "(no db_path, or it does not live in .tausik/). Use --claudemd to "
            "specify the file explicitly."
        )
        return

    claudemd = args.claudemd or resolve_claudemd(project_dir or "")
    if not claudemd or not os.path.exists(claudemd):
        print("Error: CLAUDE.md not found. Use --claudemd to specify path.")
        return

    dynamic_content = build_dynamic_state(svc, project_dir or os.path.dirname(claudemd))

    # Refresh CLAUDE.md AND its AGENTS.md sibling from the same dynamic source so
    # no IDE's onboarding file goes stale mid-session (v15p-agents-md-bootstrap).
    from claudemd_writer import apply_dynamic_section, plan_dynamic_writes

    dry_run = getattr(args, "dry_run", False)
    any_change = False
    for path, content in plan_dynamic_writes(claudemd, dynamic_content):
        msg, changed = apply_dynamic_section(path, content, dry_run)
        print(msg)
        any_change = any_change or changed
    if dry_run and any_change:
        import sys

        sys.exit(1)


def cmd_fts(svc: ProjectService, args: Any) -> None:
    c = getattr(args, "fts_cmd", None)
    if c == "optimize":
        results = svc.fts_optimize()
        for table, status in results.items():
            print(f"  {table}: {status}")
        print("FTS5 optimization complete.")
    else:
        print("Usage: tausik fts optimize")


from project_cli_skill import cmd_skill  # noqa: F401,E402  (re-export for project.py dispatch table)


def _print_gate(name: str, gate: dict, indent: str, verbose: bool) -> None:
    """Format and print a single gate entry."""
    status = "ON" if gate.get("enabled", True) else "OFF"
    severity = gate.get("severity", "warn")
    triggers = ", ".join(gate.get("trigger", []))
    desc = gate.get("description", "")
    cmd = gate.get("command") or "(built-in)"
    print(f"{indent}[{status}] {name} ({severity}) -> {triggers}")
    print(f"{indent}       {desc}")
    if verbose and gate.get("enabled", True):
        print(f"{indent}       cmd: {cmd}")


from project_cli_stack import cmd_stack  # noqa: F401,E402


def cmd_gates(svc: ProjectService, args: Any) -> None:
    """Handle gates subcommands: status, list, enable, disable."""
    c = args.gates_cmd or "status"
    if c in ("status", "list"):
        data = svc.gates_status()
        gates = data["gates"]
        if not gates:
            print("No gates configured.")
            return
        stack_groups = data["stack_groups"]
        active_stacks = data["active_stacks"]
        verbose = c == "status"
        print("Quality Gates:")
        shown: set[str] = set()
        for name in stack_groups.get("general", []):
            if name in shown or name not in gates:
                continue
            shown.add(name)
            _print_gate(name, gates[name], "  ", verbose)
        for stack in sorted(stack_groups):
            if stack == "general":
                continue
            stack_gates = [g for g in stack_groups[stack] if g in gates and g not in shown]
            if not stack_gates:
                continue
            active = stack in active_stacks
            print(f"  [{stack}]" + (" (detected)" if active else ""))
            for name in stack_gates:
                shown.add(name)
                _print_gate(name, gates[name], "    ", verbose)
        if verbose:
            qg0 = data.get("qg0", {})
            no_goal = qg0.get("no_goal", [])
            no_ac = qg0.get("no_ac", [])
            planning = qg0.get("planning_count", 0)
            if no_goal or no_ac:
                print(f"\n  QG-0 Readiness ({planning} planning tasks):")
                if no_goal:
                    print(f"    ⚠{len(no_goal)} without goal: {', '.join(no_goal)}")
                if no_ac:
                    print(f"    ⚠{len(no_ac)} without acceptance_criteria: {', '.join(no_ac)}")
            elif planning:
                print(f"\n  QG-0 Readiness: all {planning} planning tasks have goal + AC")

    elif c == "enable":
        print(svc.gate_enable(args.name))
    elif c == "disable":
        print(svc.gate_disable(args.name))


# cmd_verify moved to project_cli_verify.py to keep this file under filesize gate
# cmd_metrics, cmd_search, cmd_events, cmd_dead_end, cmd_explore, cmd_audit, cmd_run
# -> moved to project_cli_ops.py


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
