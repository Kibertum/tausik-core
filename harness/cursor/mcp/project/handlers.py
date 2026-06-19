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
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
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
        call_budget=args.get("call_budget"),
        tier=args.get("tier"),
    )


def _do_task_quick(svc: Any, args: dict) -> str:
    return svc.task_quick(args["title"], args.get("goal"), args.get("role"), args.get("stack"))


def _do_task_next(svc: Any, args: dict) -> str:
    task = svc.task_next(args.get("agent_id"))
    if task:
        action = "claimed and started" if args.get("agent_id") else "suggested"
        lines = [f"Next task ({action}): {task['slug']} — {task['title']}"]
        mh = task.get("model_hint")
        if mh:
            lines.append(f"Model hint: {mh['display']} ({mh['model']})")
        return "\n".join(lines)
    return "No available tasks."


def _do_task_done(svc: Any, args: dict) -> str:
    """tausik_task_done — returns structured JSON dict (was task_done_v2 prior to v14b rename).

    Calls the internal `_task_done_report` directly to get the dict report,
    then JSON-encodes for transport. CLI keeps using `svc.task_done()` which
    wraps the same report into the legacy str-or-raise contract.
    """

    def _progress(ev: dict) -> None:
        event = ev.get("event")
        idx = ev.get("index", "?")
        total = ev.get("total", "?")
        name = ev.get("name", "?")
        if event == "gate_start":
            print(f"[gate {idx}/{total}] running {name}...", file=sys.stderr, flush=True)
            return
        status = "PASS" if ev.get("passed") else "FAIL"
        if ev.get("skipped"):
            status = "SKIP"
        dur = ev.get("duration_ms", 0)
        print(
            f"[gate {idx}/{total}] {status} {name} ({dur} ms)",
            file=sys.stderr,
            flush=True,
        )

    result = svc._task_done_report(
        args["slug"],
        relevant_files=args.get("relevant_files"),
        ac_verified=args.get("ac_verified", False),
        no_knowledge=args.get("no_knowledge", False),
        evidence=args.get("evidence"),
        evidence_json=args.get("evidence_json"),
        progress_fn=_progress,
    )
    return json.dumps(result, ensure_ascii=False)


def _do_task_update(svc: Any, args: dict) -> str:
    fields = {k: v for k, v in args.items() if k != "slug"}
    return svc.task_update(args["slug"], **fields) if fields else "No fields to update."


def _do_session_current(svc: Any, args: dict) -> str:
    s = svc.session_current()
    return f"Session #{s['id']} started {s['started_at']}" if s else "No active session."


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
        lambda s: f"#{s['id']} [{s.get('ended_at', 'active')}] {(s.get('summary') or '')[:60]}",
        "No sessions.",
    )


def _do_session_handoff(svc: Any, args: dict) -> str:
    # Reset tool call counter on checkpoint (SENAR Rule 9.3)
    try:
        svc.be.meta_set("tool_call_count", "0")
    except Exception:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
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
    return svc.story_add(args["epic_slug"], args["slug"], args["title"], args.get("description"))


def _do_story_list(svc: Any, args: dict) -> str:
    return _handle_list(
        svc.story_list(args.get("epic_slug")),
        lambda s: f"[{s['status']}] {s['slug']}: {s['title']}",
        "No stories.",
    )


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
    return _handle_list(
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


def _do_memory_search(svc: Any, args: dict) -> str:
    results = svc.memory_search(
        args["query"],
        include_archived=bool(args.get("include_archived", False)),
    )
    return _handle_list(
        results,
        lambda r: (
            f"#{r['id']} [{r['type']}]{' [archived]' if r.get('archived_at') else ''} {r['title']}: {r['content'][:100]}"
        ),
        "No memories found.",
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
    return _handle_list(decs, lambda d: f"#{d['id']} {d['decision'][:80]}", "No decisions.")


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
        tags=_coerce_tags(args.get("tags")),
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
            elapsed = str(int((datetime.now(timezone.utc) - started).total_seconds() / 60))
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


def _do_usage_event_log(svc: Any, args: dict) -> str:
    from tausik_utils import ServiceError

    required = ("tokens_input", "tokens_output", "tokens_total", "cost_usd")
    missing = [k for k in required if k not in args]
    if missing:
        return f"Error: missing required fields: {', '.join(missing)}"

    try:
        return svc.metrics_log_usage_event(
            tokens_input=int(args["tokens_input"]),
            tokens_output=int(args["tokens_output"]),
            tokens_total=int(args["tokens_total"]),
            cost_usd=float(args["cost_usd"]),
            tool_calls=int(args.get("tool_calls") or 0),
            model=str(args.get("model") or ""),
            task_slug=args.get("task_slug"),
            session_id=args.get("session_id"),
        )
    except ServiceError as e:
        return f"Error: {e}"


def _do_snippet_search(svc: Any, args: dict) -> str:
    """Ranked FTS5 search over reusable snippets — JSON envelope for the agent."""
    from snippet_storage import search_snippets_ranked

    query = args.get("query", "")
    language = args.get("language")
    raw_limit = args.get("limit")
    if isinstance(raw_limit, bool):
        limit = 20  # bool is an int subclass — reject True/False as a count
    elif isinstance(raw_limit, (int, float)):
        limit = int(raw_limit)
    elif isinstance(raw_limit, str) and raw_limit.strip().lstrip("-").isdigit():
        limit = int(raw_limit)
    else:
        limit = 20  # missing / non-numeric -> default (never crashes the tool)
    results = search_snippets_ranked(svc.be._conn, query, language=language, limit=limit)
    return json.dumps(
        {"query": query, "language": language, "count": len(results), "results": results},
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------------------------
# Dispatch table: tool name -> handler(svc, args)
# ---------------------------------------------------------------------------

_DISPATCH: dict[str, _Handler] = {
    # --- Health & Status ---
    "tausik_health": lambda svc, args: _handle_health(svc),
    "tausik_self_check": lambda svc, args: _handle_self_check(),
    "tausik_status": lambda svc, args: _handle_status(svc, args),
    "tausik_metrics": lambda svc, args: _handle_metrics(svc),
    "tausik_usage_event_log": _do_usage_event_log,
    "tausik_search": lambda svc, args: _handle_search(svc, args),
    "tausik_snippet_search": _do_snippet_search,
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
    "tausik_task_block": lambda svc, args: svc.task_block(args["slug"], args.get("reason")),
    "tausik_task_unblock": lambda svc, args: svc.task_unblock(args["slug"]),
    "tausik_task_update": _do_task_update,
    "tausik_task_plan": lambda svc, args: svc.task_plan(args["slug"], args["steps"]),
    "tausik_task_step": lambda svc, args: svc.task_step(args["slug"], args["step_num"]),
    "tausik_task_delete": lambda svc, args: svc.task_delete(args["slug"]),
    "tausik_task_review": lambda svc, args: svc.task_review(args["slug"]),
    "tausik_task_move": lambda svc, args: svc.task_move(args["slug"], args["new_story_slug"]),
    "tausik_task_log": lambda svc, args: svc.task_log(args["slug"], args["message"]),
    "tausik_task_logs": lambda svc, args: _handle_task_logs(svc, args),
    "tausik_task_claim": lambda svc, args: svc.task_claim(args["slug"], args["agent_id"]),
    "tausik_task_unclaim": lambda svc, args: svc.task_unclaim(args["slug"]),
    "tausik_reason_step": lambda svc, args: svc.reasoning_step_add(
        args["slug"], args["kind"], args["content"]
    ),
    "tausik_task_replay": lambda svc, args: svc.task_replay(args["slug"], args.get("output")),
    # --- Sessions ---
    "tausik_session_current": _do_session_current,
    "tausik_session_list": _do_session_list,
    "tausik_session_start": lambda svc, args: svc.session_start(),
    "tausik_session_end": lambda svc, args: svc.session_end(args.get("summary")),
    "tausik_session_extend": lambda svc, args: svc.session_extend(args.get("minutes", 60)),
    "tausik_session_handoff": _do_session_handoff,
    "tausik_session_last_handoff": _do_session_last_handoff,
    "tausik_session_open": lambda svc, args: _handle_session_open(svc, args),
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
    "tausik_memory_block": _do_memory_block,
    "tausik_memory_compact": _do_memory_compact,
    "tausik_memory_archive": _do_memory_archive,
    "tausik_memory_dedupe": _do_memory_dedupe,
    "tausik_memory_lint": _do_memory_lint,
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
    "tausik_skill_activate": lambda svc, args: _skill.handle_skill_activate(svc, args["name"]),
    "tausik_skill_deactivate": lambda svc, args: _skill.handle_skill_deactivate(svc, args["name"]),
    "tausik_skill_install": lambda svc, args: _skill.handle_skill_install(args["name"]),
    "tausik_skill_uninstall": lambda svc, args: _skill.handle_skill_uninstall(args["name"]),
    "tausik_skill_repo_add": lambda svc, args: _skill.handle_skill_repo_add(
        args["url"], force=bool(args.get("force"))
    ),
    "tausik_skill_repo_remove": lambda svc, args: _skill.handle_skill_repo_remove(args["name"]),
    "tausik_skill_repo_list": lambda svc, args: _skill.handle_skill_repo_list(),
    "tausik_skill_catalog": lambda svc, args: _skill.handle_skill_catalog(
        repo_name=args.get("repo"),
        as_json=bool(args.get("as_json", False)),
    ),
    # --- Maintenance (handler in handlers_skill.py) ---
    "tausik_update_claudemd": lambda svc, args: _skill.handle_update_claudemd(svc),
    "tausik_fts_optimize": _do_fts_optimize,
    # --- cq (Cross-project Knowledge) ---
    "tausik_cq_query": lambda svc, args: _handle_cq_query(args),
    "tausik_cq_publish": lambda svc, args: _handle_cq_publish(args),
    # --- Stack registry (read + scaffold) ---
    "tausik_stack_list": lambda svc, args: _handle_stack_list(svc),
    "tausik_stack_show": lambda svc, args: _handle_stack_show(args["name"]),
    "tausik_stack_lint": lambda svc, args: _handle_stack_lint(),
    "tausik_stack_diff": lambda svc, args: _handle_stack_diff(args["name"]),
    "tausik_stack_scaffold": lambda svc, args: _handle_stack_scaffold(args),
    # --- Doctor / verify / stack reset+export ---
    "tausik_doctor": lambda svc, args: _handle_doctor(svc),
    "tausik_verify": lambda svc, args: _handle_verify(
        svc,
        args.get("task_slug"),
        scope=args.get("scope", "standard"),
        trigger=args.get("trigger", "verify"),
    ),
    "tausik_stack_reset": lambda svc, args: _handle_stack_reset(args["name"]),
    "tausik_stack_export": lambda svc, args: _handle_stack_export(args["name"]),
    # --- Roles (CRUD) ---
    "tausik_role_list": lambda svc, args: _handle_role_list(svc),
    "tausik_role_show": lambda svc, args: _handle_role_show(svc, args["slug"]),
    "tausik_role_create": lambda svc, args: _handle_role_create(svc, args),
    "tausik_role_update": lambda svc, args: _handle_role_update(svc, args),
    "tausik_role_delete": lambda svc, args: _handle_role_delete(svc, args),
    "tausik_role_seed": lambda svc, args: _handle_role_seed(svc),
}

# --- SPEC artifacts (handlers in handlers_spec.py) ---
import handlers_spec as _spec  # noqa: E402

_DISPATCH.update(_spec.SPEC_HANDLERS)

# --- ADAPT artifacts (handlers in handlers_adapt.py) ---
import handlers_adapt as _adapt  # noqa: E402

_DISPATCH.update(_adapt.ADAPT_HANDLERS)


def _handle_role_list(svc: Any) -> str:
    import json as _json

    from service_roles import role_list

    return _json.dumps(role_list(svc.be), indent=2, ensure_ascii=False)


def _handle_role_show(svc: Any, slug: str) -> str:
    import json as _json

    from service_roles import role_show

    try:
        return _json.dumps(role_show(svc.be, slug), indent=2, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"


def _handle_role_create(svc: Any, args: dict) -> str:
    import json as _json

    from service_roles import role_create

    try:
        row = role_create(
            svc.be,
            args["slug"],
            args["title"],
            args.get("description"),
            args.get("extends"),
        )
        return _json.dumps(row, indent=2, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"


def _handle_role_update(svc: Any, args: dict) -> str:
    import json as _json

    from service_roles import role_update

    try:
        row = role_update(svc.be, args["slug"], args.get("title"), args.get("description"))
        return _json.dumps(row, indent=2, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"


def _handle_role_delete(svc: Any, args: dict) -> str:
    from service_roles import role_delete

    try:
        return role_delete(svc.be, args["slug"], args.get("force", False))
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"


def _handle_role_seed(svc: Any) -> str:
    import json as _json

    from service_roles import seed_existing_roles

    return _json.dumps(seed_existing_roles(svc.be), indent=2)


def _handle_doctor(svc: Any) -> str:
    import io as _io
    import sys as _sys

    from project_cli_doctor import _capture_db_state, cmd_doctor

    _capture_db_state()
    buf = _io.StringIO()
    saved_out, saved_err = _sys.stdout, _sys.stderr
    _sys.stdout = _sys.stderr = buf

    class _Ns:
        pass

    try:
        cmd_doctor(svc, _Ns())
    except SystemExit:
        pass
    finally:
        _sys.stdout, _sys.stderr = saved_out, saved_err
    return buf.getvalue()


def _handle_verify(
    svc: Any,
    task_slug: str | None,
    *,
    scope: str = "standard",
    trigger: str = "verify",
) -> str:
    """v1.4 Verify-First Contract — delegate to public service method.

    Layering rule: handlers call the service; the service owns the SQLite
    connection. Behavior parity with the CLI:
      - task_slug optional (full-suite when omitted)
      - scope/trigger optional with sensible defaults
    """
    from tausik_utils import ServiceError

    try:
        result = svc.run_verify_for_task(task_slug=task_slug, scope=scope, trigger=trigger)
    except ServiceError as e:
        return f"Error: {e}"
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"
    gates = [r.get("name", "?") for r in result.get("results", [])]
    return (
        f"verify task='{task_slug or '-'}' "
        f"passed={result['passed']} "
        f"status={result['status']} "
        f"trigger={result['trigger']} "
        f"gates={gates}"
    )


def _handle_stack_reset(name: str) -> str:
    import shutil as _sh

    from tausik_utils import validate_slug

    try:
        validate_slug(name)
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"
    user_dir = os.path.join(os.getcwd(), ".tausik", "stacks", name)
    if not os.path.isdir(user_dir):
        return f"No user override at {user_dir}"
    _sh.rmtree(user_dir)
    return f"Removed {user_dir}"


def _handle_stack_export(name: str) -> str:
    import json as _json

    from service_stack_ops import stack_show

    try:
        return _json.dumps(stack_show(name), indent=2, ensure_ascii=False)
    except KeyError as e:
        return f"Error: {e}"


def _handle_stack_list(svc: Any) -> str:
    import json as _json

    return _json.dumps(svc.stack_list(), indent=2, ensure_ascii=False)


def _handle_stack_show(name: str) -> str:
    import json as _json

    from service_stack_ops import stack_show

    try:
        return _json.dumps(stack_show(name), indent=2, ensure_ascii=False)
    except KeyError as e:
        return f"Error: {e}"


def _handle_stack_lint() -> str:
    import json as _json

    from service_stack_ops import stack_lint

    return _json.dumps(stack_lint(), indent=2, ensure_ascii=False)


def _handle_stack_diff(name: str) -> str:
    import json as _json

    from service_stack_ops import stack_diff

    return _json.dumps(stack_diff(name), indent=2, ensure_ascii=False)


def _handle_stack_scaffold(args: dict) -> str:
    import json as _json

    from service_stack_ops import stack_scaffold

    try:
        result = stack_scaffold(
            args["name"],
            args.get("extends_builtin"),
            args.get("force", False),
        )
        return _json.dumps(result, indent=2, ensure_ascii=False)
    except FileExistsError as e:
        return f"Refused: {e}"
    except (ValueError, KeyError) as e:
        return f"Error: {e}"


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
        from tausik_utils import tausik_config_path

        config_path = tausik_config_path(_project_dir())
        if not os.path.exists(config_path):
            return None
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        from cq_client import get_cq_client

        return get_cq_client(config)
    except Exception:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return None


def _handle_cq_query(args: dict) -> str:
    """Query cq for cross-project knowledge."""
    client = _get_cq_client()
    if not client:
        return (
            "cq not configured. Add 'cq' section to .tausik/config.json with endpoint and api_key."
        )
    units = client.query(
        domains=args["domains"],
        language=args.get("language", ""),
        framework=args.get("framework", ""),
        limit=args.get("limit", 5),
    )
    if not units:
        return (
            "No cq knowledge found for these domains. cq may be unavailable or no matching entries."
        )
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
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return json.dumps({"status": "error", "error": str(e)})


def _handle_self_check() -> str:
    """v14b-mcp-stale-module-detector — return MCP-server freshness report."""
    try:
        import self_check  # type: ignore[import-not-found]

        return json.dumps(self_check.collect(), ensure_ascii=False, default=str)
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return json.dumps(
            {
                "server": "tausik-project",
                "drift_detected": None,
                "error": f"self_check unavailable: {e}",
                "remediation": (
                    "self_check module failed to load — likely an old MCP "
                    "server. Restart IDE so a fresh server boots with the "
                    "diagnostic available."
                ),
            },
            ensure_ascii=False,
        )


def _handle_status(svc: Any, args: dict | None = None) -> str:
    from project_config import DEFAULT_SESSION_MAX_MINUTES, load_config
    from tausik_utils import format_status_compact_json

    args = args or {}
    data = svc.get_status()
    cfg = load_config()
    max_min = cfg.get("session_max_minutes", DEFAULT_SESSION_MAX_MINUTES)
    duration_warning = svc.session_check_duration(max_min)
    # v14b-session-active-time: surface active/wall minutes alongside the
    # session id. Active is the SENAR Rule 9.2 metric (sum of bounded
    # inter-tool-call deltas, capped at idle threshold per gap); wall is
    # informational. active_seconds carries sub-minute precision for callers
    # that aggregate deltas over short bursts (e.g. capacity dashboards).
    session = data.get("session")
    active_min = wall_min = 0
    active_sec = 0
    if session:
        try:
            active_sec = svc.session_active_seconds()
            active_min = svc.session_active_minutes()
            wall_min = svc.session_wall_minutes()
        except Exception:  # noqa: BLE001 — never fail status on metric calc
            active_sec = active_min = wall_min = 0
        data["active_minutes"] = active_min
        data["active_seconds"] = active_sec
        data["wall_minutes"] = wall_min
    data["session_max_minutes"] = max_min
    # v14b-status-exploration-audit-signals: enrich data with SENAR 5.1
    # (open exploration) and 9.5 (audit overdue) so /start Phase 1 batch
    # can drop the dedicated MCP calls. Both lookups are best-effort.
    exp: dict | None = None
    try:
        exp = svc.exploration_current()
    except Exception:  # noqa: BLE001 — never fail status on metric calc
        exp = None
    if exp:
        data["exploration"] = exp
    audit_overdue = 0
    try:
        audit_overdue = int(svc.audit_overdue_sessions())
    except (AttributeError, ValueError, TypeError):
        audit_overdue = 0
    if audit_overdue:
        data["audit_overdue_sessions"] = audit_overdue
    if args.get("compact"):
        return format_status_compact_json(data, duration_warning)
    counts = data["task_counts"]
    total = sum(counts.values())
    done = counts.get("done", 0)
    parts = [f"Tasks: {done}/{total} done"]
    for st in ("planning", "active", "blocked", "review"):
        if counts.get(st):
            parts.append(f"{counts[st]} {st}")
    if session:
        sess_part = f"Session: #{session['id']} (active {active_min}m / {max_min}m"
        if args.get("verbose"):
            sess_part += f", wall {wall_min}m"
        sess_part += ")"
        parts.append(sess_part)
    else:
        parts.append("Session: none")
    result = ", ".join(parts)
    if duration_warning:
        result += f"\n⚠ {duration_warning}"
    if exp:
        elapsed = exp.get("elapsed_min", "?")
        over = " — OVER LIMIT" if exp.get("over_limit") else ""
        result += (
            f"\n⚠ Open exploration #{exp.get('id')}: {exp.get('title', '')} ({elapsed}m{over})"
        )
    if audit_overdue:
        result += f"\n⚠ SENAR Rule 9.5: {audit_overdue} sessions since last audit. Run /review then audit mark."
    return result


def _handle_session_open(svc: Any, args: dict | None = None) -> str:
    """v14b-session-open-compound-rpc — single envelope for /start Phase 1.

    Replaces 5 sequential MCP calls (session_start + status compact +
    last_handoff + task_list active+blocked + self_check) with one
    round-trip. Each sub-section is best-effort: a sub-call failure
    surfaces as an "error" key inside that section so /start can render
    a degraded dashboard rather than aborting. On self_check.drift_detected
    the agent still falls back to CLI per /start SKILL.md.
    """
    args = args or {}
    # 1. Session — start (idempotent) + current dict snapshot.
    try:
        svc.session_start()  # text return ignored — we rebuild from session_current
        session_data = svc.session_current()
    except Exception as e:  # noqa: BLE001 — never fail open on any sub-error
        session_data = {"error": str(e)}
    # 2. Status (compact JSON identical to tausik_status compact:true).
    try:
        status_data = json.loads(_handle_status(svc, {"compact": True}))
    except Exception as e:  # noqa: BLE001
        status_data = {"error": str(e)}
    # 3. Last handoff (None if absent — caller distinguishes from error).
    try:
        handoff = svc.session_last_handoff()
    except Exception as e:  # noqa: BLE001
        handoff = {"error": str(e)}

    # 4. Active + blocked tasks. Each task slimmed to slug/title/status.
    def _slim(t: dict) -> dict:
        return {"slug": t["slug"], "title": t["title"], "status": t["status"]}

    try:
        tasks = {
            "active": [_slim(t) for t in svc.task_list(status="active")],
            "blocked": [_slim(t) for t in svc.task_list(status="blocked")],
        }
    except Exception as e:  # noqa: BLE001
        tasks = {"active": [], "blocked": [], "error": str(e)}
    # 5. Self-check (re-use existing handler — already serialized).
    try:
        self_check_data = json.loads(_handle_self_check())
    except Exception as e:  # noqa: BLE001
        self_check_data = {"error": str(e)}
    return json.dumps(
        {
            "session": session_data,
            "status": status_data,
            "handoff": handoff,
            "tasks": tasks,
            "self_check": self_check_data,
        },
        indent=2,
        ensure_ascii=False,
        default=str,
    )


def _handle_task_list(svc: Any, args: dict) -> str:
    tasks = svc.task_list(
        status=args.get("status"),
        story=args.get("story"),
        epic=args.get("epic"),
        role=args.get("role"),
        stack=args.get("stack"),
        limit=args.get("limit"),
        include_archived=bool(args.get("include_archived", False)),
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
                    lines.append(f"  {item['slug']}: {item.get('title', item.get('decision', ''))}")
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
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error loading gates: {e}"
    lines = []
    for name, gate in sorted(gates.items()):
        status = "ON" if gate.get("enabled", True) else "OFF"
        sev = gate.get("severity", "warn")
        gate_stacks = gate.get("stacks", [])
        stack_info = f" [{','.join(gate_stacks)}]" if gate_stacks else ""
        lines.append(f"[{status}] {name} ({sev}){stack_info}: {gate.get('description', '')}")
    if stacks:
        lines.append(f"\nDetected stacks: {', '.join(stacks)}")
    return "\n".join(lines) if lines else "No gates configured."


def _handle_gate_toggle(name: str, enable: bool) -> str:
    import re

    if not re.match(r"^[a-z0-9][a-z0-9-]*$", name):
        return f"Invalid gate name '{name}': must be lowercase alphanumeric with hyphens."
    try:
        from project_config import load_config, save_config

        cfg = load_config()
        cfg.setdefault("gates", {}).setdefault(name, {})["enabled"] = enable
        save_config(cfg)
        return f"Gate '{name}' {'enabled' if enable else 'disabled'}."
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"

    # _handle_list kept here as it's used by core handlers above


def _handle_list(items: list, fmt, empty_msg: str = "None.") -> str:
    if not items:
        return empty_msg
    return "\n".join(fmt(item) for item in items)
