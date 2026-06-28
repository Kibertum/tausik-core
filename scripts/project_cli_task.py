"""TAUSIK CLI handlers — task subcommand dispatch + task-specific helpers.

Extracted from project_cli.py to keep that module under the 400-line filesize
gate (filesize-debt-paydown-2). Pure re-org — no semantic changes. Helpers
that are only referenced by cmd_task (_auto_slug, _print_task_detail,
_print_with_warnings) live here; _print_table stays in project_cli.py because
other commands (epic/story/session/decisions) still need it.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_service import ProjectService


def cmd_task(svc: ProjectService, args: Any) -> None:
    from project_cli import _print_table

    c = args.task_cmd
    if c == "add":
        slug = args.slug or _auto_slug(args.title)
        story_slug = getattr(args, "story_slug", None)
        defect_of = getattr(args, "defect_of", None)
        print(
            svc.task_add(
                story_slug,
                slug,
                args.title,
                args.stack,
                args.complexity,
                args.goal,
                args.role,
                defect_of,
                getattr(args, "call_budget", None),
                getattr(args, "tier", None),
                cost_budget_usd=getattr(args, "cost_budget_usd", None),
                token_budget=getattr(args, "token_budget", None),
            )
        )
        rb = getattr(args, "rollback_plan", None)
        if rb:
            svc.task_update(slug, rollback_plan=rb)
        acl = {
            f: getattr(args, f, None)
            for f in ("scope_paths", "scope_tools")
            if getattr(args, f, None) is not None
        }
        if acl:
            svc.task_update(slug, **acl)
    elif c == "list":
        tasks = svc.task_list(
            args.status,
            args.story,
            args.epic,
            args.role,
            args.stack,
            limit=getattr(args, "limit", None),
            include_archived=getattr(args, "include_archived", False),
        )
        _print_table(tasks, ["slug", "title", "status", "story_slug", "role", "stack"])
    elif c == "show":
        task = svc.task_show(args.slug)
        _print_task_detail(task)
        deleg = svc.task_delegation(args.slug)
        if deleg:
            print(
                f"delegated: worker sub-agent (model {deleg.get('display')}, "
                f"parent session #{deleg.get('parent_session') or 'unknown'})"
            )
        wsum = svc.task_worker_summary(args.slug)
        if wsum:
            print(
                f"worker-summary: {wsum.get('summary')}"
                + (f" | gates: {wsum.get('gates')}" if wsum.get("gates") else "")
            )
    elif c == "delegate":
        print(svc.task_delegate(args.slug))
    elif c == "undelegate":
        print(svc.task_undelegate(args.slug))
    elif c == "handoff":
        from ow_handoff import serialize_contract

        print(serialize_contract(svc.task_handoff(args.slug)))
    elif c == "summary-back":
        print(
            svc.task_summary_back(
                args.slug,
                args.summary,
                changed=getattr(args, "changed", None),
                gates=getattr(args, "gates", None),
                ac_evidence=getattr(args, "ac_evidence", None),
                follow_ups=getattr(args, "follow_ups", None),
            )
        )
    elif c == "start":
        _print_with_warnings(svc.task_start(args.slug, force=getattr(args, "force", False)))
    elif c == "done":
        # v1.4 r14-mcp-streaming-progress: emit a one-line "Running N gates,
        # max ~Σ seconds" hint to stderr at the start of the gate run, then a
        # short status per gate. MCP hosts (VS Code Claude Extension) render
        # this as the live "doing-stuff" indicator so the user knows whether
        # to wait. Quiet by default (TAUSIK_QUIET=1).
        import os as _os
        import sys as _sys

        def _stderr_progress(ev: dict[str, Any]) -> None:
            if _os.environ.get("TAUSIK_QUIET"):
                return
            kind = ev.get("event")
            if kind == "run_start":
                _sys.stderr.write(
                    f"[gates] Running {ev.get('total', '?')} gate(s) "
                    f"(trigger={ev.get('trigger', '?')}, max ~"
                    f"{ev.get('max_seconds', '?')}s).\n"
                )
            elif kind == "gate_start":
                _sys.stderr.write(
                    f"[gates] {ev.get('index')}/{ev.get('total')} {ev.get('name')} ...\n"
                )
            elif kind == "gate_done":
                status = "SKIP" if ev.get("skipped") else ("PASS" if ev.get("passed") else "FAIL")
                _sys.stderr.write(
                    f"[gates] {ev.get('index')}/{ev.get('total')} "
                    f"{ev.get('name')} {status} "
                    f"({ev.get('duration_ms', 0)} ms)\n"
                )
            _sys.stderr.flush()

        _print_with_warnings(
            svc.task_done(
                args.slug,
                args.relevant_files,
                args.ac_verified,
                getattr(args, "no_knowledge", False),
                evidence=getattr(args, "evidence", None),
                evidence_json=getattr(args, "evidence_json", None),
                progress_fn=_stderr_progress,
            )
        )
    elif c == "block":
        print(svc.task_block(args.slug, args.reason))
    elif c == "unblock":
        print(svc.task_unblock(args.slug))
    elif c == "review":
        print(svc.task_review(args.slug))
    elif c == "update":
        import json as _json

        fields = {}
        for k in (
            "title",
            "goal",
            "notes",
            "stack",
            "complexity",
            "role",
            "scope",
            "scope_exclude",
            "scope_paths",
            "scope_tools",
            "rollback_plan",
            "call_budget",
            "tier",
            "cost_budget_usd",
            "token_budget",
        ):
            v = getattr(args, k, None)
            if v is not None:
                fields[k] = v
        if getattr(args, "notes_overwrite", False):
            if getattr(args, "notes", None) is None:
                print("--notes-overwrite has no effect without --notes.", file=sys.stderr)
                return
            fields["notes_overwrite"] = True
        if args.ac is not None:
            fields["acceptance_criteria"] = args.ac
        rf = getattr(args, "update_relevant_files", None)
        if rf is not None:
            fields["relevant_files"] = _json.dumps(list(rf))
        if fields:
            print(svc.task_update(args.slug, **fields))
        else:
            print("No fields to update.")
    elif c == "delete":
        print(svc.task_delete(args.slug))
    elif c == "plan":
        print(svc.task_plan(args.slug, args.steps))
    elif c == "step":
        print(svc.task_step(args.slug, args.step_num))
    elif c == "move":
        print(svc.task_move(args.slug, args.new_story_slug))
    elif c == "claim":
        print(svc.task_claim(args.slug, args.agent_id))
    elif c == "unclaim":
        print(svc.task_unclaim(args.slug))
    elif c == "quick":
        print(
            svc.task_quick(
                args.title, args.goal, args.role, args.stack, getattr(args, "acceptance", None)
            )
        )
    elif c == "next":
        next_task = svc.task_next(args.agent)
        if next_task:
            action = "claimed and started" if args.agent else "suggested"
            print(f"Next task ({action}): {next_task['slug']} — {next_task['title']}")
            mh = next_task.get("model_hint")
            if mh:
                print(f"Model hint: {mh['display']} ({mh['model']})")
        else:
            print("No available tasks.")
    elif c == "reason-step":
        print(svc.reasoning_step_add(args.slug, args.kind, args.content))
    elif c == "replay":
        print(svc.task_replay(args.slug, getattr(args, "output", None)))
    elif c == "log":
        print(svc.task_log(args.slug, args.message))
    elif c == "logs":
        logs = svc.task_logs(args.slug, phase=getattr(args, "phase", None))
        if not logs:
            print(f"No logs for '{args.slug}'.")
        else:
            for entry in logs:
                phase_tag = f" [{entry['phase']}]" if entry.get("phase") else ""
                print(f"[{entry['created_at']}]{phase_tag} {entry['message']}")
    else:
        subcmds = "add, list, show, start, done, block, unblock, review, update, delete, delegate, undelegate, handoff, summary-back, plan, step, quick, next, move, claim, unclaim, reason-step, replay, log, logs"
        if c:
            from difflib import get_close_matches

            matches = get_close_matches(c, subcmds.replace(" ", "").split(","), n=2, cutoff=0.5)
            if matches:
                print(
                    f"Unknown subcommand 'task {c}'. Did you mean: {', '.join(matches)}?",
                    file=sys.stderr,
                )
                return
        print(f"Usage: tausik task [{subcmds}]")


def _print_with_warnings(result: str) -> None:
    """Print result, routing WARNING/NOTE lines to stderr."""
    for line in result.split("\n"):
        if line.startswith("WARNING:") or line.startswith("NOTE:"):
            print(f"  {line}", file=sys.stderr)
        else:
            print(line)


def _auto_slug(title: str) -> str:
    """Generate slug from title."""
    from tausik_utils import slugify

    return slugify(title)


def _print_task_detail(task: dict[str, Any]) -> None:
    """Print full task details."""
    print(f"Task: {task['slug']}")
    print(f"Title: {task['title']}")
    print(f"Status: {task['status']}")
    for field in (
        "story_slug",
        "epic_slug",
        "role",
        "stack",
        "complexity",
        "goal",
        "acceptance_criteria",
        "scope",
        "scope_exclude",
        "scope_paths",
        "scope_tools",
        "rollback_plan",
        "notes",
        "started_at",
        "completed_at",
        "blocked_at",
        "relevant_files",
        "defect_of",
        "claimed_by",
        "attempts",
        "started_model_id",
        "started_model_version",
        "done_model_id",
        "done_model_version",
        "model_mismatch",
    ):
        val = task.get(field)
        if val:
            print(f"{field}: {val}")
    cost_budget = task.get("cost_budget_usd")
    cost_actual = task.get("cost_actual_usd")
    if cost_budget is not None or cost_actual is not None:
        cb_str = f"${float(cost_budget):.4f}" if cost_budget is not None else "—"
        ca_str = f"${float(cost_actual):.4f}" if cost_actual is not None else "—"
        print(f"cost: actual={ca_str} / budget={cb_str}")
    token_budget = task.get("token_budget")
    tokens_actual = task.get("tokens_actual")
    if token_budget is not None or tokens_actual is not None:
        tb_str = str(int(token_budget)) if token_budget is not None else "—"
        ta_str = str(int(tokens_actual)) if tokens_actual is not None else "—"
        print(f"tokens: actual={ta_str} / budget={tb_str}")
    if task.get("plan"):
        try:
            steps = json.loads(task["plan"])
            done_count = sum(1 for s in steps if s.get("done"))
            print(f"Plan: {done_count}/{len(steps)} steps done")
            for i, s in enumerate(steps, 1):
                mark = "x" if s.get("done") else " "
                print(f"  [{mark}] {i}. {s['step']}")
        except (json.JSONDecodeError, TypeError):
            print("Plan: (corrupted data)")
    decisions = task.get("decisions", [])
    if decisions:
        print(f"Decisions ({len(decisions)}):")
        for d in decisions:
            print(f"  - {d['decision']}")
    steps = task.get("reasoning_steps", [])
    if steps:
        print(f"Reasoning trace ({len(steps)}):")
        for s in steps:
            print(f"  {s['seq']}. ({s['kind']}) {s['content']}")
    specs = task.get("specs", [])
    if specs:
        print(f"SPECs ({len(specs)}):")
        for sp in specs:
            ref = f" -> {sp['content_ref']}" if sp.get("content_ref") else ""
            print(f"  [{sp['type']}] {sp['slug']} {sp['version']} ({sp['relation']}){ref}")
