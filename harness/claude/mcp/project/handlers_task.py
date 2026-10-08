"""MCP handlers for the task domain — the task lifecycle and its journal.

Split out of handlers.py by mcp-handlers-god-module-split. Follows the
convention already set by handlers_spec.py / handlers_adapt.py: the module owns
its handlers AND the slice of the dispatch table that names them, and
handlers.py merges it with `_DISPATCH.update(...)`.
"""

from __future__ import annotations

import json
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


def _do_task_start(svc: Any, args: dict) -> str:
    if args.get("package"):
        from task_start_result import serialize_start_with_context

        return serialize_start_with_context(svc, args["slug"])
    return svc.task_start(args["slug"])


def _order() -> Any:
    """The ordering module, imported lazily.

    Ordering functions are module-level rather than `ProjectService` methods
    (its public surface is ratcheted and may only shrink), so there is no
    `svc.` to reach them through. Imported inside the call so the MCP server
    keeps its current import graph.
    """
    import service_task_order

    return service_task_order


def _do_task_next(svc: Any, args: dict) -> str:
    """Transport over the one renderer. This used to be a second copy.

    It claimed in its own docstring to print the same three states as the CLI,
    and it did not: it reported HOW MANY tasks were withheld where the CLI
    reports WHICH. Nothing compared the two, so the claim survived the drift.
    """
    from render_task import task_next_lines

    return "\n".join(task_next_lines(svc, args.get("agent_id")))


def _do_task_done(svc: Any, args: dict) -> str:
    """tausik_task_done — returns structured JSON dict (was task_done_v2 prior to v14b rename).

    Calls the internal `_task_done_report` directly to get the dict report,
    then JSON-encodes for transport. CLI keeps using `svc.task_done()` which
    wraps the same report into the legacy str-or-raise contract.
    """

    if args.get("compound") is not None:
        try:
            request = json.loads(args["compound"])
        except (TypeError, ValueError) as exc:
            raise ValueError("compound must be a JSON object") from exc
        allowed = {"message", "step", "verify"}
        if not isinstance(request, dict) or set(request) - allowed:
            raise ValueError("compound permits only message, step and verify")
        from task_progress_close import run_progress_close

        result = run_progress_close(
            svc,
            args["slug"],
            request.get("message"),
            request.get("step"),
            close=True,
            verify=request.get("verify", False),
            verify_handle=args.get("verify_handle"),
            ac_verified=args.get("ac_verified", False),
            relevant_files=args.get("relevant_files"),
            evidence=args.get("evidence"),
            evidence_json=args.get("evidence_json"),
            no_knowledge=args.get("no_knowledge", False),
            no_file_changes=args.get("no_file_changes", False),
            no_changelog=args.get("no_changelog", False),
            zero_gate_ack=bool(args.get("gates_not_applicable", False)),
            # Per-gate progress is deterministic runner state, not a model
            # decision boundary. The final bounded report carries the result.
            progress_fn=None,
        )
        return json.dumps(result, ensure_ascii=False)

    result = svc._task_done_report(
        args["slug"],
        relevant_files=args.get("relevant_files"),
        ac_verified=args.get("ac_verified", False),
        no_knowledge=args.get("no_knowledge", False),
        evidence=args.get("evidence"),
        evidence_json=args.get("evidence_json"),
        progress_fn=None,
        no_file_changes=args.get("no_file_changes", False),
        no_changelog=args.get("no_changelog", False),
        # Read explicitly: the MCP dispatch does no schema validation, so an
        # argument this handler does not name is silently dropped (memory #368,
        # mcp-server-drops-unknown-arguments-silently). Advertising it in
        # tools.py is not what makes it arrive.
        verify_handle=args.get("verify_handle"),
        zero_gate_ack=bool(args.get("gates_not_applicable", False)),
    )
    from verify_compact_output import compact_task_done_report

    result = compact_task_done_report(svc, result, args["slug"])
    return json.dumps(result, ensure_ascii=False)


def _do_task_update(svc: Any, args: dict) -> str:
    fields = {k: v for k, v in args.items() if k != "slug"}
    return svc.task_update(args["slug"], **fields) if fields else "No fields to update."


def _handle_task_logs(svc: Any, args: dict) -> str:
    """Transport. The copy this replaces cut the timestamp to minutes and
    printed empty parentheses where a line had no phase."""
    from render_task import task_logs_lines

    return "\n".join(task_logs_lines(svc, args["slug"], args.get("phase")))


def _do_task_step(svc: Any, args: dict) -> str:
    if args.get("message") is None:
        return svc.task_step(args["slug"], args["step_num"])
    from task_progress_close import serialize_progress_close

    return serialize_progress_close(svc, args["slug"], args["message"], args["step_num"])


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
    if args.get("packet") is not None:
        from work_packet import serialize_work_packet

        try:
            request = json.loads(args["packet"])
        except (TypeError, ValueError) as exc:
            raise ValueError("packet must be a JSON object") from exc
        if not isinstance(request, dict) or set(request) - {"query", "sources", "max_bytes"}:
            raise ValueError("packet permits only query, sources and max_bytes")
        return serialize_work_packet(
            svc,
            args["slug"],
            request.get("query"),
            request.get("sources"),
            max_bytes=request.get("max_bytes", 16_384),
        )
    if args.get("mode") == "package":
        from task_context_package import serialize_task_context_package

        return serialize_task_context_package(
            svc, args["slug"], max_bytes=args.get("max_bytes", 8192)
        )
    task = svc.task_show(args["slug"])
    lines = [
        f"Task: {task['slug']}",
        f"Title: {task['title']}",
        f"Status: {task['status']}",
    ]
    # The same field list as `tausik task show` (scripts/task_detail_fields):
    # scope_paths and rollback_plan are what the gates judge the agent by.
    from task_detail_fields import detail_lines

    lines.extend(detail_lines(task))
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
    lines.extend(task.get("relevant_memory") or [])
    return "\n".join(lines)


TASK_HANDLERS = {
    "tausik_task_list": lambda svc, args: _handle_task_list(svc, args),
    "tausik_task_show": lambda svc, args: _handle_task_show(svc, args),
    "tausik_task_add": _do_task_add,
    "tausik_task_quick": _do_task_quick,
    "tausik_task_next": _do_task_next,
    "tausik_task_depends": lambda svc, args: _order().task_depends(
        svc, args["slug"], args["after"]
    ),
    "tausik_task_undepends": lambda svc, args: _order().task_undepends(
        svc, args["slug"], args["after"]
    ),
    "tausik_task_start": _do_task_start,
    "tausik_task_done": _do_task_done,
    "tausik_task_block": lambda svc, args: svc.task_block(
        args["slug"], args.get("reason"), args.get("question"), args.get("unblock_criteria")
    ),
    "tausik_task_unblock": lambda svc, args: svc.task_unblock(
        args["slug"], args.get("criterion_met"), args.get("by")
    ),
    "tausik_task_update": _do_task_update,
    "tausik_task_plan": lambda svc, args: svc.task_plan(args["slug"], args["steps"]),
    "tausik_task_step": _do_task_step,
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
