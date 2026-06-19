"""TAUSIK CLI handlers — memory, gates, skill, fts, update-claudemd commands."""

from __future__ import annotations

import json
from typing import Any

from project_service import ProjectService


def cmd_memory(svc: ProjectService, args: Any) -> None:
    c = args.memory_cmd
    if c == "add":
        print(svc.memory_add(args.mem_type, args.title, args.content, args.tags, args.task))
    elif c == "list":
        rows = svc.memory_list(
            args.mem_type,
            args.limit,
            include_archived=getattr(args, "include_archived", False),
        )
        if not rows:
            print("  (no memories)")
            return
        for r in rows:
            tags = ""
            if r.get("tags"):
                try:
                    tags = " " + ", ".join(json.loads(r["tags"]))
                except (json.JSONDecodeError, TypeError):
                    pass
            arch = " [archived]" if r.get("archived_at") else ""
            print(f"  #{r['id']} [{r['type']}] {r['title']}{tags}{arch}")
    elif c == "search":
        rows = svc.memory_search(
            args.query,
            include_archived=getattr(args, "include_archived", False),
        )
        if not rows:
            print("  No results.")
            return
        for r in rows:
            arch = " [archived]" if r.get("archived_at") else ""
            print(f"  #{r['id']} [{r['type']}] {r['title']}{arch}")
    elif c == "show":
        r = svc.memory_show(args.id)
        print(f"#{r['id']} [{r['type']}] {r['title']}")
        print(f"Created: {r.get('created_at', '')}")
        if r.get("tags"):
            try:
                print(f"Tags: {', '.join(json.loads(r['tags']))}")
            except (json.JSONDecodeError, TypeError):
                pass
        if r.get("task_slug"):
            print(f"Task: {r['task_slug']}")
        print(f"\n{r['content']}")
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
        results = svc.memory_related(args.node_type, args.node_id, args.hops, args.include_invalid)
        if not results:
            print("  No related nodes found.")
            return
        for r in results:
            rec = r.get("record", {})
            ntype = r["node_type"]
            nid = r["node_id"]
            depth = r["depth"]
            rel = r.get("via_relation", "")
            label = rec.get("title", rec.get("decision", ""))[:60]
            print(f"  [{depth} hop] {ntype}#{nid} --[{rel}]--> {label}")
    elif c == "graph":
        edges = svc.memory_graph(
            args.node_type,
            args.node_id,
            args.relation,
            args.include_invalid,
            args.limit,
        )
        if not edges:
            print("  No edges found.")
            return
        for e in edges:
            valid = "" if not e.get("valid_to") else f" [invalid {e['valid_to'][:10]}]"
            conf = f" ({e['confidence']:.0%})" if e["confidence"] < 1.0 else ""
            print(
                f"  #{e['id']} {e['source_type']}#{e['source_id']} "
                f"--[{e['relation']}]--> {e['target_type']}#{e['target_id']}"
                f"{conf}{valid}"
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
        result = svc.memory_archive(args.before, confirm=bool(args.confirm))
        days = result["before_days"]
        if result["applied"]:
            print(
                f"Memory archive: archived {result['archived']} rows older than "
                f"{days} days. Hidden from `memory list` by default; use "
                f"`--include-archived` to see them."
            )
            return
        cands = result.get("candidates", [])
        if not cands:
            print(f"Memory archive (dry-run): no unarchived rows older than {days} days.")
            return
        print(
            f"Memory archive (dry-run): {len(cands)} rows older than {days} days "
            f"would be archived. Re-run with `--confirm` to apply."
        )
        for r in cands[:50]:
            title = r.get("title") or ""
            if len(title) > 60:
                title = title[:57] + "..."
            print(f"  #{r['id']:<5} [{r['type']:<10}] {r['created_at']}  {title}")
        if len(cands) > 50:
            print(f"  ... and {len(cands) - 50} more")
    elif c == "dedupe":
        suggestions = svc.memory_dedupe(threshold=args.threshold, n=args.limit)
        if not suggestions:
            print(
                f"Memory dedupe: no pairs above threshold {args.threshold:.2f} "
                f"in the last {args.limit} unarchived rows."
            )
            return
        print(
            f"Memory dedupe: {len(suggestions)} pair(s) above {args.threshold:.2f} similarity. "
            "Review then merge with `memory delete <id>` after consolidating."
        )
        for s in suggestions:
            ta = s["title_a"][:40]
            tb = s["title_b"][:40]
            print(
                f'  {s["ratio"]:.3f} [{s["type"]:<10}] #{s["id_a"]} "{ta}"  ↔  #{s["id_b"]} "{tb}"'
            )
    elif c == "lint":
        result = svc.memory_lint(apply=bool(getattr(args, "apply", False)))
        findings = result["findings"]
        if not findings:
            print("Memory lint: no contradictions, superseded, or stale-file issues found.")
            return
        if result["applied"]:
            print(
                f"Memory lint: {result['count']} finding(s); archived "
                f"{result['archived']} superseded entry(ies). Contradictions and "
                f"stale-file hits are advisory — review them below."
            )
        else:
            print(
                f"Memory lint (dry-run): {result['count']} finding(s). "
                f"Re-run with `--apply` to archive superseded entries."
            )
        for f in findings:
            title = (f["title"] or "")[:50]
            print(f'  #{f["id"]:<5} [{f["kind"]:<11}] {f["reason"]}  "{title}"')


def cmd_update_claudemd(svc: ProjectService, args: Any) -> None:
    """Update <!-- DYNAMIC:START --> section in CLAUDE.md."""
    import os
    import subprocess

    claudemd = args.claudemd
    if not claudemd:
        try:
            from ide_utils import detect_ide, get_ide_config

            _cfg = get_ide_config(detect_ide(os.getcwd()))
            _candidates = ["CLAUDE.md", os.path.join(_cfg["config_dir"], "CLAUDE.md")]
        except ImportError:
            _candidates = ["CLAUDE.md", ".claude/CLAUDE.md"]
        for candidate in _candidates:
            if os.path.exists(candidate):
                claudemd = candidate
                break
    if not claudemd or not os.path.exists(claudemd):
        print("Error: CLAUDE.md not found. Use --claudemd to specify path.")
        return

    tasks = svc.task_list()
    session = svc.session_current()

    active = [t for t in tasks if t["status"] == "active"]
    blocked = [t for t in tasks if t["status"] == "blocked"]
    done_count = sum(1 for t in tasks if t["status"] == "done")
    total = len(tasks)

    # stdin=DEVNULL: avoids inherit of MCP JSON-RPC pipe (v14b-defect-mcp-task-done-stdin-hang).
    try:
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
            stdin=subprocess.DEVNULL,
        )
        branch = r.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        branch = "unknown"

    session_info = f"#{session['id']} (active)" if session else "none"

    lines = [
        "## Current State",
        f"Session: {session_info} | Branch: {branch} | Version: {_get_version()}",
        f"Tasks: {done_count}/{total} done, {len(active)} active, {len(blocked)} blocked",
    ]
    if active:
        lines.append(f"Active: {', '.join(t['slug'] for t in active)}")
    if blocked:
        lines.append(f"Blocked: {', '.join(t['slug'] for t in blocked)}")

    if (be := getattr(svc, "be", None)) is not None:
        from service_knowledge_aggregates import build_compact_memory_tail

        if memory_tail := build_compact_memory_tail(be):
            lines.append("")
            lines.extend(memory_tail)

    dynamic_content = "\n".join(lines)

    # Refresh CLAUDE.md AND its AGENTS.md sibling from the same dynamic source so
    # no IDE's onboarding file goes stale mid-session (v15p-agents-md-bootstrap).
    from claudemd_writer import apply_dynamic_section, resolve_sibling_targets

    dry_run = getattr(args, "dry_run", False)
    any_change = False
    for path in resolve_sibling_targets(claudemd):
        msg, changed = apply_dynamic_section(path, dynamic_content, dry_run)
        print(msg)
        any_change = any_change or changed
    if dry_run and any_change:
        import sys

        sys.exit(1)


def _get_version() -> str:
    try:
        from tausik_version import __version__

        return __version__
    except ImportError:
        return "unknown"


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
