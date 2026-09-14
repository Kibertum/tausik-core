"""TAUSIK CLI handler for `tausik metrics` — command + subcommand dispatch.

Holds `cmd_metrics` itself, not just its helpers. It previously lived in
project_cli_ops.py while this file — named for the domain — held only the
dispatcher it calls, so the command and its own module were separated by a
line count rather than by a domain (filesize-rejoin-cap-deformed-wrappers,
decision #199).
"""

from __future__ import annotations

from typing import Any

from backend_queries_usage import usage_events_unattributed_rollup
from project_service import ProjectService, normalize_usage_time_bound


#: What the per-task table prints where nothing was measured. Never 0 —
#: a zero there asserts that a task cost nothing, which no one observed
#: (decision #334).
_NOT_MEASURED = "не измерено"


def _print_unattributed_bucket(svc: ProjectService, since: str | None, until: str | None) -> None:
    """Print the «вне задачи» bucket — the events the table above cannot show.

    The per-task rollup selects `task_slug IS NOT NULL`, so work that no task
    claims is absent from it by construction. Since v48 the hook writes such an
    event instead of dropping it (usage-attribution-is-keyed-by-task-not-session),
    and an unprinted bucket would simply move the silence from the write path to
    the read path. Printed only when it is non-empty: a permanent "0" line is
    noise, and there is nothing to hide when there is nothing in it.
    """
    # The SAME window as the table above it: a bucket computed over a different
    # one would be worse than no bucket. Ordering (`since` > `until`) is already
    # refused by the per-task rollup, which runs first on both paths through
    # `_print_usage_cost_rollup`, so the bad-bound case never reaches here.
    bucket = usage_events_unattributed_rollup(
        svc.be,
        normalize_usage_time_bound("since", since),
        normalize_usage_time_bound("until", until),
    )
    if not bucket["event_count"]:
        return
    sessionless = bucket["sessionless_events"]
    tail = f", из них вне сессии: {sessionless}" if sessionless else ""
    tokens = int(bucket["tokens_total"])
    cost = float(bucket["cost_usd"])
    # Same rule as the table above: tokens with a zero cost were never metered,
    # and printing `0.0000 usd` over 201,897 tokens claims a measurement nobody
    # took. Zero tokens AND zero cost is a real zero and prints as one.
    cost_cell = f"{cost:.4f} usd" if cost or not tokens else _NOT_MEASURED
    print(f"\nвне задачи: {bucket['event_count']} событий{tail}, {tokens:,} токенов, {cost_cell}")


def _print_usage_cost_rollup(svc: ProjectService, since: str | None, until: str | None) -> None:
    rows = svc.usage_cost_rollup_by_task(since=since, until=until)
    if not rows:
        print(
            "No usage data for tasks in the selected window (usage_events with non-null task_slug)."
        )
        # NO early return. An empty per-task table is precisely the window in
        # which unattributed work is most likely to exist and most likely to be
        # missed — returning here would print "no usage data" over a bucket that
        # is not empty, which is a lie the old code could not tell only because
        # the hook dropped those events before they were ever written.
        _print_unattributed_bucket(svc, since, until)
        return
    # "calls", not "events": these rows are one per tool call, and that count is
    # the only thing in them that was actually measured. The PostToolUse payload
    # carries no usage — 76 of this project's 54,855 such rows have any tokens at
    # all — so a task's tokens and cost are NOT observed here.
    print("task_slug".ljust(32), "calls".rjust(8), "tokens".rjust(14), "cost_usd".rjust(14))
    unmetered = 0
    for r in rows:
        slug = str(r.get("task_slug") or "")
        ev = int(r.get("event_count") or 0)
        tok = int(r.get("tokens_total") or 0)
        cost = float(r.get("cost_usd") or 0.0)
        if tok == 0:
            # Not `0.0000`. A zero here reads as "this task was free", which is a
            # claim nobody measured; absence is reported as absence (#334).
            unmetered += 1
            print(
                slug[:32].ljust(32),
                str(ev).rjust(8),
                _NOT_MEASURED.rjust(14),
                _NOT_MEASURED.rjust(14),
            )
            continue
        print(
            slug[:32].ljust(32),
            str(ev).rjust(8),
            f"{tok:,}".rjust(14),
            f"{cost:.4f}".rjust(14),
        )
    if unmetered:
        print(
            f"\n{unmetered} of {len(rows)} task(s) have call volume but NO token "
            "measurement: the PostToolUse payload does not carry usage, so per-task "
            "spend is unobserved. Per-SESSION spend is measured — see `tausik metrics`."
        )
    _print_unattributed_bucket(svc, since, until)


def cmd_metrics(svc: ProjectService, args: Any) -> None:
    """The SENAR report. Built by `render_metrics`, which the MCP tool also calls.

    This function used to BUILD the report as it printed it, which is why the
    MCP tool could not reuse it and answered with a one-line summary instead.
    """
    from project_cli_metrics import dispatch_metrics_subcmd
    from render_metrics import metrics_lines

    if dispatch_metrics_subcmd(svc, args):
        return
    print("\n".join(metrics_lines(svc)))


def render_extended_metrics(m: dict[str, Any]) -> None:
    """Print the per-tier/calibration/escape tail. Kept as the printing name it
    always was; the lines themselves now come from `render_metrics`, so there is
    one builder rather than one per surface."""
    from render_metrics import extended_metrics_lines

    print("\n".join(extended_metrics_lines(m)))


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
        # Local now: the helper crossed back from project_cli_ops with cmd_metrics.
        _print_usage_cost_rollup(svc, getattr(args, "since", None), getattr(args, "until", None))
        return True
    if sub == "tokens":
        from service_token_metrics import print_cli

        print_cli(
            int(getattr(args, "last", 10) or 10),
            bool(getattr(args, "as_json", False)),
            rebuild=bool(getattr(args, "rebuild", False)),
        )
        return True
    return False


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
