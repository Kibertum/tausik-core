"""TAUSIK argparse — `task` subcommand parser (extracted from project_parser).

Hosts every `tausik task <subcmd>` flag definition. Imported once from
``project_parser.build_parser`` to keep that orchestrator under the 400-line
filesize gate.
"""

from __future__ import annotations

import argparse

from project_types import VALID_COMPLEXITIES, VALID_TIERS


def _add_scope_acl_flags(parser: argparse.ArgumentParser) -> None:
    """Attach --scope-paths / --scope-tools (SENAR Rule 2 declared ACL)."""
    parser.add_argument(
        "--scope-paths",
        nargs="*",
        default=None,
        dest="scope_paths",
        help="Allowed write paths/globs for this task (JSON list stored; "
        "basis for scope enforcement). Empty = explicit 'nothing allowed'.",
    )
    parser.add_argument(
        "--scope-tools",
        nargs="*",
        default=None,
        dest="scope_tools",
        help="Allowed tool names for this task (optional ACL complement).",
    )


def _add_unit_flags(parser: argparse.ArgumentParser) -> None:
    """Attach --call-budget / --tier / --cost-budget / --token-budget flags."""
    parser.add_argument("--call-budget", type=int, default=None, dest="call_budget")
    parser.add_argument("--tier", default=None, choices=sorted(VALID_TIERS))
    parser.add_argument(
        "--cost-budget",
        type=float,
        default=None,
        dest="cost_budget_usd",
        help="Planned USD cost budget for this task. Warn 1.5×, BLOCKER 2× (advisory).",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=None,
        dest="token_budget",
        help="Planned token-total budget for this task.",
    )


def add_task(sub: argparse._SubParsersAction) -> None:
    """Wire up `tausik task <subcmd>` parsers."""
    task_p = sub.add_parser("task", help="Task management")
    task_sub = task_p.add_subparsers(dest="task_cmd")

    ta = task_sub.add_parser(
        "add",
        epilog='Example: tausik task add "Task title" --story my-story --slug my-task --complexity medium',
    )
    ta.add_argument("title", help="Task title (in quotes)")
    ta.add_argument(
        "--story",
        "--group",
        default=None,
        dest="story_slug",
        help="Parent story slug (optional). --group is deprecated alias.",
    )
    ta.add_argument("--slug", default=None, help="Task slug (auto-generated from title if omitted)")
    ta.add_argument("--stack", default=None)
    ta.add_argument("--complexity", default=None, choices=sorted(VALID_COMPLEXITIES))
    ta.add_argument("--goal", default=None)
    ta.add_argument("--role", default=None)
    ta.add_argument("--defect-of", default=None, help="Parent task slug (defect fix)")
    ta.add_argument(
        "--rollback-plan",
        default=None,
        dest="rollback_plan",
        help="SENAR Rule 6: how to undo this change (git revert / migration "
        "down / feature flag off).",
    )
    _add_scope_acl_flags(ta)
    _add_unit_flags(ta)

    tl = task_sub.add_parser("list")
    tl.add_argument("--status", default=None)
    tl.add_argument("--story", default=None)
    tl.add_argument("--epic", default=None)
    tl.add_argument("--role", default=None)
    tl.add_argument("--stack", default=None)
    tl.add_argument("--limit", type=int, default=None, help="Max tasks to return")
    tl.add_argument(
        "--include-archived",
        action="store_true",
        help="Include soft-archived tasks (archived_at IS NOT NULL). Off by default.",
    )

    ts = task_sub.add_parser("show")
    ts.add_argument("slug")

    tdelegate = task_sub.add_parser(
        "delegate", help="Mark a complexity<=medium task delegated to a worker sub-agent"
    )
    tdelegate.add_argument("slug")
    tundelegate = task_sub.add_parser("undelegate", help="Clear a task's delegation")
    tundelegate.add_argument("slug")
    thandoff = task_sub.add_parser(
        "handoff", help="Print the worker handoff contract (JSON) for a delegated task"
    )
    thandoff.add_argument("slug")
    tsumback = task_sub.add_parser(
        "summary-back", help="Worker → orchestrator: record a structured completion summary"
    )
    tsumback.add_argument("slug")
    tsumback.add_argument("summary")
    tsumback.add_argument("--changed", default=None, help="Changed files/areas")
    tsumback.add_argument("--gates", default=None, help="Gate status (e.g. green)")
    tsumback.add_argument("--ac-evidence", dest="ac_evidence", default=None)
    tsumback.add_argument("--follow-ups", dest="follow_ups", default=None)

    tstart = task_sub.add_parser("start")
    tstart.add_argument("slug")
    tstart.add_argument(
        "--force",
        action="store_true",
        help="Bypass session capacity gate (logs audit event + notes)",
    )

    tdone = task_sub.add_parser("done")
    tdone.add_argument("slug")
    tdone.add_argument(
        "--ac-verified",
        action="store_true",
        help="Confirm all acceptance criteria verified",
    )
    tdone.add_argument(
        "--no-knowledge",
        action="store_true",
        dest="no_knowledge",
        help="Confirm no knowledge to capture",
    )
    tdone.add_argument("--relevant-files", nargs="*", default=None)
    evidence_group = tdone.add_mutually_exclusive_group()
    evidence_group.add_argument(
        "--evidence",
        default=None,
        help='Inline AC verification log — e.g. "AC verified: 1. ✓ 2. ✓ ...". '
        "Saves a separate task_log call.",
    )
    evidence_group.add_argument(
        "--evidence-json",
        default=None,
        dest="evidence_json",
        help='Structured AC evidence as JSON: \'{"ac_evidence":[{"n":1,'
        '"status":"pass","evidence":"tests/foo.py::test_bar"}, ...]}\'. '
        "Converted to canonical prose before logging. "
        "Mutually exclusive with --evidence.",
    )

    tblock = task_sub.add_parser("block")
    tblock.add_argument("slug")
    tblock.add_argument("--reason", default=None)

    tunblock = task_sub.add_parser("unblock")
    tunblock.add_argument("slug")

    treview = task_sub.add_parser("review")
    treview.add_argument("slug")

    tupdate = task_sub.add_parser("update")
    tupdate.add_argument("slug")
    tupdate.add_argument("--title", default=None)
    tupdate.add_argument("--goal", default=None)
    tupdate.add_argument("--notes", default=None)
    tupdate.add_argument(
        "--notes-overwrite",
        action="store_true",
        dest="notes_overwrite",
        help="Allow --notes to REPLACE the append-only journal (default: refuse; "
        "use `task log` to append instead).",
    )
    tupdate.add_argument("--acceptance-criteria", default=None, dest="ac")
    # --stack is validated in the service layer so config-defined custom
    # stacks (cfg.custom_stacks) work alongside the built-in DEFAULT_STACKS.
    tupdate.add_argument("--stack", default=None)
    tupdate.add_argument("--complexity", default=None, choices=sorted(VALID_COMPLEXITIES))
    tupdate.add_argument("--role", default=None)
    tupdate.add_argument("--scope", default=None)
    tupdate.add_argument("--scope-exclude", default=None, dest="scope_exclude")
    tupdate.add_argument(
        "--rollback-plan",
        default=None,
        dest="rollback_plan",
        help="SENAR Rule 6: how to undo this change (git revert / migration "
        "down / feature flag off). Required by QG-0 for medium/complex.",
    )
    tupdate.add_argument(
        "--relevant-files",
        nargs="*",
        default=None,
        dest="update_relevant_files",
        help="JSON-list scope for scoped verify / pytest gate (overwrites prior)",
    )
    _add_scope_acl_flags(tupdate)
    _add_unit_flags(tupdate)

    tdel = task_sub.add_parser("delete")
    tdel.add_argument("slug")

    tplan = task_sub.add_parser("plan")
    tplan.add_argument("slug")
    tplan.add_argument("steps", nargs="+")

    tstep = task_sub.add_parser("step")
    tstep.add_argument("slug")
    tstep.add_argument("step_num", type=int)

    tquick = task_sub.add_parser("quick", help="Quick-create task (auto-slug)")
    tquick.add_argument("title", help="Task title")
    tquick.add_argument("--goal", default=None)
    tquick.add_argument("--role", default=None)
    tquick.add_argument("--stack", default=None)

    tnext = task_sub.add_parser("next", help="Pick next available task")
    tnext.add_argument("--agent", default=None, help="Agent ID to auto-claim")

    tlog = task_sub.add_parser(
        "log",
        epilog='Example: tausik task log my-task "Implemented auth middleware"',
    )
    tlog.add_argument("slug", help="Task slug")
    tlog.add_argument("message", help="Log message (appended to notes with timestamp)")

    tlogs = task_sub.add_parser(
        "logs",
        epilog="Example: tausik task logs my-task --phase review",
    )
    tlogs.add_argument("slug", help="Task slug")
    tlogs.add_argument(
        "--phase",
        help="Filter by phase (planning, implementation, review, testing, done)",
    )

    treason = task_sub.add_parser(
        "reason-step",
        help="Record a RENAR reasoning step (intent|premise|action|verification)",
        epilog='Example: tausik task reason-step my-task premise "FTS5 keeps trace searchable"',
    )
    treason.add_argument("slug", help="Task slug")
    treason.add_argument(
        "kind",
        choices=["intent", "premise", "action", "verification"],
        help="Reasoning step kind (closed list)",
    )
    treason.add_argument("content", help="Reasoning step content")

    treplay = task_sub.add_parser(
        "replay",
        help="Reconstruct a task's chronological timeline (logs + reasoning + events + verification)",
        epilog="Example: tausik task replay my-task --output replay.md",
    )
    treplay.add_argument("slug", help="Task slug")
    treplay.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write the markdown timeline to a file instead of stdout",
    )

    tmove = task_sub.add_parser("move")
    tmove.add_argument("slug")
    tmove.add_argument("new_story_slug")

    tclaim = task_sub.add_parser("claim")
    tclaim.add_argument("slug")
    tclaim.add_argument("agent_id")

    tunclaim = task_sub.add_parser("unclaim")
    tunclaim.add_argument("slug")
