"""MCP handlers for the task domain — the task lifecycle and its journal.

Split out of handlers.py by mcp-handlers-god-module-split. Follows the
convention already set by handlers_spec.py / handlers_adapt.py: the module owns
its handlers AND the slice of the dispatch table that names them, and
handlers.py merges it with `_DISPATCH.update(...)`.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from handlers_render import render_list


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
    return svc.task_quick(
        args["title"],
        args.get("goal"),
        args.get("role"),
        args.get("stack"),
        args.get("acceptance"),
    )


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
        no_file_changes=args.get("no_file_changes", False),
        no_changelog=args.get("no_changelog", False),
        # Read explicitly: the MCP dispatch does no schema validation, so an
        # argument this handler does not name is silently dropped (memory #368,
        # mcp-server-drops-unknown-arguments-silently). Advertising it in
        # tools.py is not what makes it arrive.
        verify_handle=args.get("verify_handle"),
    )
    return json.dumps(result, ensure_ascii=False)


def _do_task_update(svc: Any, args: dict) -> str:
    fields = {k: v for k, v in args.items() if k != "slug"}
    return svc.task_update(args["slug"], **fields) if fields else "No fields to update."


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
    return render_list(
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


TASK_HANDLERS = {
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
}
