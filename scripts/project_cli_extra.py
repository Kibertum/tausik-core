"""TAUSIK CLI handlers — memory, gates, skill, fts, update-claudemd commands."""

from __future__ import annotations

import json
from typing import Any

from project_service import ProjectService


def cmd_memory(svc: ProjectService, args: Any) -> None:
    c = args.memory_cmd
    if c == "add":
        print(
            svc.memory_add(
                args.mem_type, args.title, args.content, args.tags, args.task
            )
        )
    elif c == "list":
        rows = svc.memory_list(args.mem_type, args.limit)
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
            print(f"  #{r['id']} [{r['type']}] {r['title']}{tags}")
    elif c == "search":
        rows = svc.memory_search(args.query)
        if not rows:
            print("  No results.")
            return
        for r in rows:
            print(f"  #{r['id']} [{r['type']}] {r['title']}")
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
        results = svc.memory_related(
            args.node_type, args.node_id, args.hops, args.include_invalid
        )
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


def cmd_update_claudemd(svc: ProjectService, args: Any) -> None:
    """Update <!-- DYNAMIC:START --> section in CLAUDE.md."""
    import os
    import subprocess

    # Find CLAUDE.md
    claudemd = args.claudemd
    if not claudemd:
        # Auto-detect: look in cwd, then parent dirs
        try:
            from ide_utils import detect_ide, get_ide_config

            _ide = detect_ide(os.getcwd())
            _cfg = get_ide_config(_ide)
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

    # Gather data
    tasks = svc.task_list()
    session = svc.session_current()

    # Build dynamic section
    active = [t for t in tasks if t["status"] == "active"]
    blocked = [t for t in tasks if t["status"] == "blocked"]
    done_count = sum(1 for t in tasks if t["status"] == "done")
    total = len(tasks)

    # Get branch
    try:
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = r.stdout.strip() or "unknown"
    except Exception:
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

    dynamic_content = "\n".join(lines)

    # Read and replace
    with open(claudemd, encoding="utf-8") as f:
        content = f.read()

    marker_start = "<!-- DYNAMIC:START -->"
    marker_end = "<!-- DYNAMIC:END -->"

    if marker_start in content:
        if marker_end in content:
            before = content[: content.index(marker_start) + len(marker_start)]
            after = content[content.index(marker_end) :]
            content = f"{before}\n{dynamic_content}\n{after}"
        else:
            # No end marker — replace from start marker to end of file
            before = content[: content.index(marker_start) + len(marker_start)]
            content = f"{before}\n{dynamic_content}\n{marker_end}\n"
    else:
        print("Warning: <!-- DYNAMIC:START --> marker not found in CLAUDE.md")
        return

    with open(claudemd, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"CLAUDE.md updated ({claudemd}).")


def _get_version() -> str:
    """Get TAUSIK version from tausik_version.py."""
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


def cmd_skill(svc: ProjectService, args: Any) -> None:
    """Handle skill lifecycle: activate, deactivate, list, install, uninstall, repo."""
    import os

    c = getattr(args, "skill_cmd", None)
    project_dir = os.getcwd()
    vendor_dir = os.path.join(project_dir, ".tausik", "vendor")
    tausik_dir = os.path.join(project_dir, ".tausik")
    try:
        from ide_utils import detect_ide, get_skills_dir, get_agents_skills_dir

        _ide = detect_ide(project_dir)
        skills_dst = get_skills_dir(project_dir, _ide)
        lib_skills_dir = get_agents_skills_dir(project_dir, _ide)
    except ImportError:
        skills_dst = os.path.join(project_dir, ".claude", "skills")
        lib_skills_dir = os.path.join(project_dir, "agents", "claude", "skills")

    config_path = os.path.join(project_dir, ".tausik", "config.json")

    if c == "activate":
        print(
            svc.skill_activate(
                args.name, vendor_dir, skills_dst, lib_skills_dir, config_path
            )
        )
    elif c == "deactivate":
        print(svc.skill_deactivate(args.name, skills_dst, lib_skills_dir, config_path))
    elif c == "list":
        data = svc.skill_list(vendor_dir, skills_dst)
        print("Skills:")
        for s in sorted(data["active"], key=lambda x: x["name"]):
            print(f"  [ACTIVE  ] {s['name']}")
        for s in sorted(data["vendored"], key=lambda x: x["name"]):
            print(f"  [VENDORED] {s['name']}")
        # Show available skills from repos (not yet installed)
        try:
            from skill_repos import repo_list_all_skills

            active_names = {s["name"] for s in data["active"]}
            vendored_names = {s["name"] for s in data["vendored"]}
            all_repo_skills = repo_list_all_skills(vendor_dir)
            for s in all_repo_skills:
                if s["name"] not in active_names and s["name"] not in vendored_names:
                    desc = f" — {s['description']}" if s.get("description") else ""
                    print(f"  [AVAILABLE] {s['name']} ({s['repo']}){desc}")
        except ImportError:
            all_repo_skills = []
        if not data["active"] and not data["vendored"] and not all_repo_skills:
            print("  (none)")
    elif c == "install":
        print(
            svc.skill_install(
                args.name, vendor_dir, skills_dst, config_path, tausik_dir
            )
        )
    elif c == "uninstall":
        print(svc.skill_uninstall(args.name, skills_dst, config_path))
    elif c == "repo":
        _cmd_skill_repo(args, vendor_dir, config_path)
    else:
        print("Usage: tausik skill [activate|deactivate|list|install|uninstall|repo]")


def _cmd_skill_repo(args: Any, vendor_dir: str, config_path: str) -> None:
    """Handle skill repo subcommands."""
    try:
        from skill_repos import repo_add, repo_list, repo_remove
    except ImportError:
        print("Error: skill_repos module not found. Run bootstrap first.")
        return

    rc = getattr(args, "repo_cmd", None)
    if rc == "add":
        print(repo_add(args.url, vendor_dir, config_path))
    elif rc == "remove":
        print(repo_remove(args.name, vendor_dir, config_path))
    elif rc == "list":
        repos = repo_list(vendor_dir, config_path)
        if not repos:
            print("No skill repos configured.")
            print("  Add one: tausik skill repo add <git-url>")
            return
        print("Skill repos:")
        for r in repos:
            status = "cloned" if r["cloned"] else "not cloned"
            default = " (default)" if r.get("default") else ""
            print(f"  {r['name']}{default} [{status}] — {r['url']}")
            if r["skills"]:
                print(f"    Skills: {', '.join(r['skills'])}")
    else:
        print("Usage: tausik skill repo [add|remove|list]")


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
            stack_gates = [
                g for g in stack_groups[stack] if g in gates and g not in shown
            ]
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
                    print(
                        f"    ⚠{len(no_ac)} without acceptance_criteria: {', '.join(no_ac)}"
                    )
            elif planning:
                print(
                    f"\n  QG-0 Readiness: all {planning} planning tasks have goal + AC"
                )

    elif c == "enable":
        print(svc.gate_enable(args.name))
    elif c == "disable":
        print(svc.gate_disable(args.name))


# cmd_verify moved to project_cli_verify.py to keep this file under filesize gate
# cmd_metrics, cmd_search, cmd_events, cmd_dead_end, cmd_explore, cmd_audit, cmd_run
# -> moved to project_cli_ops.py
