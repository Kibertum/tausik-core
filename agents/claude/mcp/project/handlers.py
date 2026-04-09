"""TAUSIK MCP handlers — dispatch tool calls to ProjectService."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable

# Ensure scripts dir is in path (once, at import time)
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import handlers_skill as _skill  # noqa: E402 — skill + maintenance handlers


def _project_dir() -> str:
    """Get project root directory."""
    return os.getcwd()


_CHECKPOINT_THRESHOLD = 40

# Type alias for dispatch handlers: (svc, args) -> str
_Handler = Callable[[Any, dict], str]


def _increment_tool_counter(svc: Any) -> str:
    """Increment tool call counter atomically. Returns warning if threshold reached."""
    try:
        # Atomic increment via backend public API
        svc.be.meta_increment("tool_call_count")
        val = svc.be.meta_get("tool_call_count") or "0"
        count = int(val)
        if count == _CHECKPOINT_THRESHOLD:
            return (
                f"\n⚠ SENAR Rule 9.3: {count} tool calls since last checkpoint. "
                f"Consider /checkpoint to save context."
            )
        if count > _CHECKPOINT_THRESHOLD and count % 10 == 0:
            return f"\n⚠ SENAR Rule 9.3: {count} tool calls! /checkpoint overdue."
    except Exception as e:
        import logging

        logging.getLogger("tausik.counter").debug("tool counter error: %s", e)
    return ""


def handle_tool(svc: Any, name: str, args: dict) -> str:
    """Dispatch tool call to service method. Returns text result."""
    # SENAR Rule 9.3: track tool call count for checkpoint reminder
    checkpoint_warning = _increment_tool_counter(svc)
    result = _dispatch_tool(svc, name, args)
    return result + checkpoint_warning if checkpoint_warning else result


# ---------------------------------------------------------------------------
# Inline handlers (too small to warrant a named function)
# ---------------------------------------------------------------------------


def _do_task_add(svc: Any, args: dict) -> str:
    return svc.task_add(
        args.get("story_slug"),
        args["slug"],
        args["title"],
        stack=args.get("stack"),
        complexity=args.get("complexity"),
        goal=args.get("goal"),
        role=args.get("role"),
        defect_of=args.get("defect_of"),
    )


def _do_task_quick(svc: Any, args: dict) -> str:
    return svc.task_quick(
        args["title"], args.get("goal"), args.get("role"), args.get("stack")
    )


def _do_task_next(svc: Any, args: dict) -> str:
    task = svc.task_next(args.get("agent_id"))
    if task:
        action = "claimed and started" if args.get("agent_id") else "suggested"
        return f"Next task ({action}): {task['slug']} — {task['title']}"
    return "No available tasks."


def _do_task_done(svc: Any, args: dict) -> str:
    return svc.task_done(
        args["slug"],
        args.get("relevant_files"),
        ac_verified=args.get("ac_verified", False),
        no_knowledge=args.get("no_knowledge", False),
    )


def _do_task_update(svc: Any, args: dict) -> str:
    fields = {k: v for k, v in args.items() if k != "slug"}
    return svc.task_update(args["slug"], **fields) if fields else "No fields to update."


def _do_session_current(svc: Any, args: dict) -> str:
    s = svc.session_current()
    return (
        f"Session #{s['id']} started {s['started_at']}" if s else "No active session."
    )


def _handle_task_logs(svc: Any, args: dict) -> str:
    logs = svc.task_logs(args["slug"], phase=args.get("phase"))
    if not logs:
        return "No logs."
    lines = []
    for log in logs:
        phase = log.get("phase", "")
        msg = log.get("message", "")
        ts = log.get("created_at", "")[:16]
        lines.append(f"[{ts}] ({phase}) {msg}")
    return "\n".join(lines)


def _do_session_list(svc: Any, args: dict) -> str:
    sessions = svc.session_list(args.get("limit", 10))
    return _handle_list(
        sessions,
        lambda s: (
            f"#{s['id']} [{s.get('ended_at', 'active')}] {(s.get('summary') or '')[:60]}"
        ),
        "No sessions.",
    )


def _do_session_handoff(svc: Any, args: dict) -> str:
    # Reset tool call counter on checkpoint (SENAR Rule 9.3)
    try:
        svc.be.meta_set("tool_call_count", "0")
    except Exception:
        pass
    return svc.session_handoff(args["handoff"])


def _do_session_last_handoff(svc: Any, args: dict) -> str:
    ho = svc.session_last_handoff()
    return json.dumps(ho, indent=2, ensure_ascii=False) if ho else "No handoff found."


def _do_epic_list(svc: Any, args: dict) -> str:
    return _handle_list(
        svc.epic_list(),
        lambda e: f"[{e['status']}] {e['slug']}: {e['title']}",
        "No epics.",
    )


def _do_story_add(svc: Any, args: dict) -> str:
    return svc.story_add(
        args["epic_slug"], args["slug"], args["title"], args.get("description")
    )


def _do_story_list(svc: Any, args: dict) -> str:
    return _handle_list(
        svc.story_list(args.get("epic_slug")),
        lambda s: f"[{s['status']}] {s['slug']}: {s['title']}",
        "No stories.",
    )


def _do_memory_add(svc: Any, args: dict) -> str:
    return svc.memory_add(
        args["type"],
        args["title"],
        args["content"],
        args.get("tags"),
        args.get("task_slug"),
    )


def _do_memory_list(svc: Any, args: dict) -> str:
    memories = svc.memory_list(args.get("type"), args.get("limit", 50))
    return _handle_list(
        memories, lambda r: f"#{r['id']} [{r['type']}] {r['title']}", "No memories."
    )


def _do_memory_show(svc: Any, args: dict) -> str:
    m = svc.memory_show(args["id"])
    return f"#{m['id']} [{m['type']}] {m['title']}\n{m['content']}"


def _do_memory_search(svc: Any, args: dict) -> str:
    results = svc.memory_search(args["query"])
    return _handle_list(
        results,
        lambda r: f"#{r['id']} [{r['type']}] {r['title']}: {r['content'][:100]}",
        "No memories found.",
    )


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
    return _handle_list(
        decs, lambda d: f"#{d['id']} {d['decision'][:80]}", "No decisions."
    )


def _do_team(svc: Any, args: dict) -> str:
    data = svc.team_status()
    if not data:
        return "No active tasks."
    lines = []
    for group in data:
        lines.append(f"{group['agent']}:")
        for t in group["tasks"]:
            lines.append(f"  [{t['status']}] {t['slug']}: {t['title']}")
    return "\n".join(lines)


def _do_dead_end(svc: Any, args: dict) -> str:
    return svc.dead_end(
        args["approach"],
        args["reason"],
        tags=args.get("tags"),
        task_slug=args.get("task_slug"),
    )


def _do_explore_current(svc: Any, args: dict) -> str:
    exp = svc.exploration_current()
    if not exp:
        return "No active exploration."
    elapsed = "?"
    if exp.get("started_at"):
        from datetime import datetime, timezone

        try:
            started = datetime.fromisoformat(exp["started_at"].replace("Z", "+00:00"))
            elapsed = str(
                int((datetime.now(timezone.utc) - started).total_seconds() / 60)
            )
        except (ValueError, TypeError):
            pass
    limit = exp.get("time_limit_min", 30)
    return f"Exploration: {exp['title']} ({elapsed}/{limit} min)"


def _do_audit_check(svc: Any, args: dict) -> str:
    result = svc.audit_check()
    return result or "Audit is up to date."


def _do_fts_optimize(svc: Any, args: dict) -> str:
    results = svc.fts_optimize()
    return "\n".join(f"{t}: {s}" for t, s in results.items())


# ---------------------------------------------------------------------------
# Dispatch table: tool name -> handler(svc, args)
# ---------------------------------------------------------------------------

_DISPATCH: dict[str, _Handler] = {
    # --- Health & Status ---
    "tausik_health": lambda svc, args: _handle_health(svc),
    "tausik_status": lambda svc, args: _handle_status(svc),
    "tausik_metrics": lambda svc, args: _handle_metrics(svc),
    "tausik_search": lambda svc, args: _handle_search(svc, args),
    "tausik_events": lambda svc, args: _handle_events(svc, args),
    "tausik_team": _do_team,
    # --- Tasks ---
    "tausik_task_list": lambda svc, args: _handle_task_list(svc, args),
    "tausik_task_show": lambda svc, args: _handle_task_show(svc, args),
    "tausik_task_add": _do_task_add,
    "tausik_task_quick": _do_task_quick,
    "tausik_task_next": _do_task_next,
    "tausik_task_start": lambda svc, args: svc.task_start(args["slug"]),
    "tausik_task_done": _do_task_done,
    "tausik_task_block": lambda svc, args: svc.task_block(
        args["slug"], args.get("reason")
    ),
    "tausik_task_unblock": lambda svc, args: svc.task_unblock(args["slug"]),
    "tausik_task_update": _do_task_update,
    "tausik_task_plan": lambda svc, args: svc.task_plan(args["slug"], args["steps"]),
    "tausik_task_step": lambda svc, args: svc.task_step(args["slug"], args["step_num"]),
    "tausik_task_delete": lambda svc, args: svc.task_delete(args["slug"]),
    "tausik_task_review": lambda svc, args: svc.task_review(args["slug"]),
    "tausik_task_move": lambda svc, args: svc.task_move(
        args["slug"], args["new_story_slug"]
    ),
    "tausik_task_log": lambda svc, args: svc.task_log(args["slug"], args["message"]),
    "tausik_task_logs": lambda svc, args: _handle_task_logs(svc, args),
    "tausik_task_claim": lambda svc, args: svc.task_claim(
        args["slug"], args["agent_id"]
    ),
    "tausik_task_unclaim": lambda svc, args: svc.task_unclaim(args["slug"]),
    # --- Sessions ---
    "tausik_session_current": _do_session_current,
    "tausik_session_list": _do_session_list,
    "tausik_session_start": lambda svc, args: svc.session_start(),
    "tausik_session_end": lambda svc, args: svc.session_end(args.get("summary")),
    "tausik_session_extend": lambda svc, args: svc.session_extend(
        args.get("minutes", 60)
    ),
    "tausik_session_handoff": _do_session_handoff,
    "tausik_session_last_handoff": _do_session_last_handoff,
    # --- Hierarchy (Epics & Stories) ---
    "tausik_epic_add": lambda svc, args: svc.epic_add(
        args["slug"], args["title"], args.get("description")
    ),
    "tausik_epic_list": _do_epic_list,
    "tausik_epic_done": lambda svc, args: svc.epic_done(args["slug"]),
    "tausik_epic_delete": lambda svc, args: svc.epic_delete(args["slug"]),
    "tausik_story_add": _do_story_add,
    "tausik_story_list": _do_story_list,
    "tausik_story_done": lambda svc, args: svc.story_done(args["slug"]),
    "tausik_story_delete": lambda svc, args: svc.story_delete(args["slug"]),
    "tausik_roadmap": lambda svc, args: _handle_roadmap(svc, args),
    # --- Knowledge (Memory) ---
    "tausik_memory_add": _do_memory_add,
    "tausik_memory_list": _do_memory_list,
    "tausik_memory_show": _do_memory_show,
    "tausik_memory_delete": lambda svc, args: svc.memory_delete(args["id"]),
    "tausik_memory_search": _do_memory_search,
    # --- Graph Memory ---
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
    # --- Dead End ---
    "tausik_dead_end": _do_dead_end,
    # --- Exploration ---
    "tausik_explore_start": lambda svc, args: svc.exploration_start(
        args["title"], args.get("time_limit", 30)
    ),
    "tausik_explore_end": lambda svc, args: svc.exploration_end(
        args.get("summary"), args.get("create_task", False)
    ),
    "tausik_explore_current": _do_explore_current,
    # --- Audit ---
    "tausik_audit_check": _do_audit_check,
    "tausik_audit_mark": lambda svc, args: svc.audit_mark(),
    # --- Gates ---
    "tausik_gates_status": lambda svc, args: _handle_gates_status(),
    "tausik_gates_enable": lambda svc, args: _handle_gate_toggle(args["name"], True),
    "tausik_gates_disable": lambda svc, args: _handle_gate_toggle(args["name"], False),
    # --- Skills (handlers in handlers_skill.py) ---
    "tausik_skill_list": lambda svc, args: _skill.handle_skill_list(),
    "tausik_skill_activate": lambda svc, args: _skill.handle_skill_activate(
        svc, args["name"]
    ),
    "tausik_skill_deactivate": lambda svc, args: _skill.handle_skill_deactivate(
        svc, args["name"]
    ),
    "tausik_skill_install": lambda svc, args: _skill.handle_skill_install(args["name"]),
    "tausik_skill_uninstall": lambda svc, args: _skill.handle_skill_uninstall(
        args["name"]
    ),
    "tausik_skill_repo_add": lambda svc, args: _skill.handle_skill_repo_add(
        args["url"]
    ),
    "tausik_skill_repo_remove": lambda svc, args: _skill.handle_skill_repo_remove(
        args["name"]
    ),
    "tausik_skill_repo_list": lambda svc, args: _skill.handle_skill_repo_list(),
    # --- Maintenance (handler in handlers_skill.py) ---
    "tausik_update_claudemd": lambda svc, args: _skill.handle_update_claudemd(svc),
    "tausik_fts_optimize": _do_fts_optimize,
    # --- cq (Cross-project Knowledge) ---
    "tausik_cq_query": lambda svc, args: _handle_cq_query(args),
    "tausik_cq_publish": lambda svc, args: _handle_cq_publish(args),
}


def _dispatch_tool(svc: Any, name: str, args: dict) -> str:
    """Internal dispatch — called by handle_tool wrapper."""
    handler = _DISPATCH.get(name)
    if handler:
        return handler(svc, args)
    return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# Helper functions (formatting, external integrations)
# ---------------------------------------------------------------------------


def _get_cq_client() -> Any:
    """Get cq client from project config. Returns None if not configured."""
    try:
        config_path = os.path.join(_project_dir(), ".tausik", "config.json")
        if not os.path.exists(config_path):
            return None
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        from cq_client import get_cq_client

        return get_cq_client(config)
    except Exception:
        return None


def _handle_cq_query(args: dict) -> str:
    """Query cq for cross-project knowledge."""
    client = _get_cq_client()
    if not client:
        return "cq not configured. Add 'cq' section to .tausik/config.json with endpoint and api_key."
    units = client.query(
        domains=args["domains"],
        language=args.get("language", ""),
        framework=args.get("framework", ""),
        limit=args.get("limit", 5),
    )
    if not units:
        return "No cq knowledge found for these domains. cq may be unavailable or no matching entries."
    lines = []
    for u in units:
        insight = u.get("insight", {})
        conf = u.get("evidence", {}).get("confidence", 0)
        lines.append(f"[{conf:.0%}] {insight.get('summary', '?')}")
        if insight.get("action"):
            lines.append(f"  Action: {insight['action']}")
    return "\n".join(lines)


def _handle_cq_publish(args: dict) -> str:
    """Publish knowledge to cq."""
    client = _get_cq_client()
    if not client:
        return "cq not configured. Add 'cq' section to .tausik/config.json."
    result = client.propose(
        domains=args["domains"],
        summary=args["summary"],
        detail=args.get("detail", ""),
        action=args.get("action", ""),
        languages=args.get("languages"),
    )
    if result and result.get("id"):
        return f"Published to cq: {result['id']}"
    return "Failed to publish to cq. Server may be unavailable."


def _handle_health(svc: Any) -> str:
    from tausik_version import __version__

    try:
        info = svc.be.health_info()
        return json.dumps(
            {
                "status": "ok",
                "version": __version__,
                "schema_version": info["schema_version"],
                "tables": info["tables"],
            }
        )
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def _handle_status(svc: Any) -> str:
    data = svc.get_status()
    counts = data["task_counts"]
    total = sum(counts.values())
    done = counts.get("done", 0)
    parts = [f"Tasks: {done}/{total} done"]
    for st in ("planning", "active", "blocked", "review"):
        if counts.get(st):
            parts.append(f"{counts[st]} {st}")
    session = data.get("session")
    parts.append(f"Session: #{session['id']}" if session else "Session: none")
    result = ", ".join(parts)
    # SENAR Rule 9.2: warn if session exceeds duration limit
    duration_warning = svc.session_check_duration()
    if duration_warning:
        result += f"\n⚠ {duration_warning}"
    return result


def _handle_task_list(svc: Any, args: dict) -> str:
    tasks = svc.task_list(
        status=args.get("status"),
        story=args.get("story"),
        epic=args.get("epic"),
        role=args.get("role"),
        stack=args.get("stack"),
        limit=args.get("limit"),
    )
    return _handle_list(
        tasks, lambda t: f"[{t['status']}] {t['slug']}: {t['title']}", "No tasks found."
    )


def _handle_task_show(svc: Any, args: dict) -> str:
    task = svc.task_show(args["slug"])
    lines = [
        f"Task: {task['slug']}",
        f"Title: {task['title']}",
        f"Status: {task['status']}",
    ]
    for field in (
        "role",
        "stack",
        "complexity",
        "goal",
        "notes",
        "acceptance_criteria",
    ):
        if task.get(field):
            lines.append(f"{field}: {task[field]}")
    if task.get("plan"):
        try:
            steps = json.loads(task["plan"])
            done_count = sum(1 for s in steps if s.get("done"))
            lines.append(f"Plan: {done_count}/{len(steps)} steps")
            for i, s in enumerate(steps, 1):
                mark = "x" if s.get("done") else " "
                lines.append(f"  [{mark}] {i}. {s['step']}")
        except (json.JSONDecodeError, TypeError):
            lines.append("Plan: (corrupted)")
    return "\n".join(lines)


def _handle_roadmap(svc: Any, args: dict) -> str:
    data = svc.get_roadmap(args.get("include_done", False))
    if not data:
        return "No epics."
    lines = []
    for epic in data:
        lines.append(f"[{epic['status']}] {epic['slug']}: {epic['title']}")
        for story in epic.get("stories", []):
            lines.append(f"  [{story['status']}] {story['slug']}: {story['title']}")
            for task in story.get("tasks", []):
                lines.append(f"    [{task['status']}] {task['slug']}: {task['title']}")
    return "\n".join(lines)


def _handle_search(svc: Any, args: dict) -> str:
    results = svc.search(args["query"], args.get("scope", "all"))
    lines = []
    for scope, items in results.items():
        if items:
            lines.append(f"--- {scope} ({len(items)}) ---")
            for item in items[:10]:
                if "slug" in item:
                    lines.append(
                        f"  {item['slug']}: {item.get('title', item.get('decision', ''))}"
                    )
                elif "query" in item:
                    lines.append(f"  {item['query']}")
                else:
                    lines.append(f"  {item.get('title', str(item)[:80])}")
    return "\n".join(lines) if lines else "No results."


def _handle_metrics(svc: Any) -> str:
    m = svc.get_metrics()
    parts = [f"Tasks: {m['tasks_done']}/{m['tasks_total']} ({m['completion_pct']}%)"]
    if m["avg_task_hours"]:
        parts.append(f"Avg time: {m['avg_task_hours']}h")
    parts.append(f"Sessions: {m['sessions_total']} ({m['session_hours']}h)")
    return ", ".join(parts)


def _handle_events(svc: Any, args: dict) -> str:
    events = svc.events_list(
        entity_type=args.get("entity_type"),
        entity_id=args.get("entity_id"),
        n=args.get("limit", 50),
    )
    if not events:
        return "No events."
    lines = []
    for ev in events:
        actor = f" by {ev['actor']}" if ev.get("actor") else ""
        lines.append(
            f"[{ev['created_at']}] {ev['entity_type']}/{ev['entity_id']}: {ev['action']}{actor}"
        )
    return "\n".join(lines)


def _handle_gates_status() -> str:
    """Gates status via project_config (no DB needed)."""
    try:
        from project_config import load_gates, load_config

        gates = load_gates()
        cfg = load_config()
        stacks = cfg.get("bootstrap", {}).get("stacks", [])
    except Exception as e:
        return f"Error loading gates: {e}"
    lines = []
    for name, gate in sorted(gates.items()):
        status = "ON" if gate.get("enabled", True) else "OFF"
        sev = gate.get("severity", "warn")
        gate_stacks = gate.get("stacks", [])
        stack_info = f" [{','.join(gate_stacks)}]" if gate_stacks else ""
        lines.append(
            f"[{status}] {name} ({sev}){stack_info}: {gate.get('description', '')}"
        )
    if stacks:
        lines.append(f"\nDetected stacks: {', '.join(stacks)}")
    return "\n".join(lines) if lines else "No gates configured."


def _handle_gate_toggle(name: str, enable: bool) -> str:
    import re

    if not re.match(r"^[a-z0-9][a-z0-9-]*$", name):
        return (
            f"Invalid gate name '{name}': must be lowercase alphanumeric with hyphens."
        )
    try:
        from project_config import load_config, save_config

        cfg = load_config()
        cfg.setdefault("gates", {}).setdefault(name, {})["enabled"] = enable
        save_config(cfg)
        return f"Gate '{name}' {'enabled' if enable else 'disabled'}."
    except Exception as e:
        return f"Error: {e}"

    # _handle_list kept here as it's used by core handlers above


def _handle_list(items: list, fmt, empty_msg: str = "None.") -> str:
    if not items:
        return empty_msg
    return "\n".join(fmt(item) for item in items)
