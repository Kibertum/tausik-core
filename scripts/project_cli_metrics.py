"""TAUSIK CLI helpers — metrics subcommand dispatch.

Extracted from project_cli_ops.py to keep it under the 400-line filesize
gate (filesize-debt-paydown follow-up). Pure re-org — no semantic changes.
"""

from __future__ import annotations

from typing import Any

from project_service import ProjectService


def dispatch_metrics_subcmd(svc: ProjectService, args: Any) -> bool:
    """Handle `metrics <sub>`: record-session, log-usage, cost, tokens.

    Returns True if a subcommand was dispatched (caller should return),
    False if the request is for the default `metrics` summary view.
    """
    sub = getattr(args, "metrics_cmd", None)
    if sub == "record-session":
        kw = dict(
            tokens_input=args.tokens_input,
            tokens_output=args.tokens_output,
            tokens_total=args.tokens_total,
            cost_usd=args.cost_usd,
            tool_calls=getattr(args, "tool_calls", 0),
            model=getattr(args, "model", ""),
            session_id=getattr(args, "session_id", None),
        )
        print(svc.metrics_record_session(**kw))
        return True
    if sub == "log-usage":
        kw = dict(
            tokens_input=args.tokens_input,
            tokens_output=args.tokens_output,
            tokens_total=args.tokens_total,
            cost_usd=args.cost_usd,
            tool_calls=getattr(args, "tool_calls", 0),
            model=getattr(args, "model", ""),
            task_slug=getattr(args, "task_slug", None),
            session_id=getattr(args, "session_id", None),
        )
        print(svc.metrics_log_usage_event(**kw))
        return True
    if sub == "cost" or getattr(args, "cost", False):
        from project_cli_ops import _print_usage_cost_rollup

        _print_usage_cost_rollup(svc, getattr(args, "since", None), getattr(args, "until", None))
        return True
    if sub == "tokens":
        from service_token_metrics import print_cli

        print_cli(int(getattr(args, "last", 10) or 10), bool(getattr(args, "as_json", False)))
        return True
    return False
