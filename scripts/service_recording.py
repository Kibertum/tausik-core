"""Helpers for recording agent-native task metrics on close (SENAR sizing).

Currently houses the single function `record_call_actual`, separated from
service_task.py to keep that file under the project filesize budget.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from project_backend import SQLiteBackend


# `task start --force` used to bypass the session capacity gate with an audit
# event. 1.10 retired the gate itself (decision #376): capacity is a signal
# printed with the start, so there is nothing left to force. The flag is kept
# only to say so — silently accepting it would teach the old habit.
FORCE_RETIRED = (
    "`--force` is retired: session capacity is no longer a gate on task start "
    "(decision #376, TAUSIK 1.10). Start the task without it; capacity is "
    "printed as a signal with the start."
)


def session_capacity_advisory(be: "SQLiteBackend", slug: str, task: dict[str, Any]) -> str:
    """Session capacity as a SIGNAL: what the numbers say about this start, never a refusal.

    Until 1.10 this was `check_session_capacity`, a gate: a task whose budget
    exceeded the remaining call capacity could not start, and `--force` was
    the audited way past it. Measured over 70 sessions (#196-#265) the capacity gate
    ended 13 of them and drove nine restarts in a row (#252-#260) - the agent
    stood at a gate that has no declared prevented effect on the system or on
    the task record (SENAR 1.5 §8.6(a)), so it was never a Quality Gate.
    Decision #376: capacity is printed with the start and refuses nothing.

    What stays from decision #223: an ABSENT session is still named, not
    passed over in silence - it is an unmeasured capacity, and the same
    `tausik session start` restores token metrics, model pinning and the
    per-session brain slice. A budget-less task gets no line at all: the
    signal has an opinion only about what asked to be accounted for.

    Returns the advisory text, or "" when there is nothing to say.
    """
    budget = task.get("call_budget")
    if not budget or budget <= 0:
        return ""
    from project_config import DEFAULT_SESSION_CAPACITY_CALLS, load_config

    cfg = load_config()
    cap = cfg.get("session_capacity_calls", DEFAULT_SESSION_CAPACITY_CALLS)
    summary = be.session_capacity_summary(cap)
    if summary["session"] is None:
        return (
            f"Session capacity: '{slug}' declares budget={budget}, but no session is "
            f"open, so nothing accounts for it - an absent session is unmeasured "
            f"capacity, not unlimited. `tausik session start` also restores token "
            f"metrics, model pinning and the per-session brain slice."
        )
    if budget > summary["remaining"]:
        return (
            f"Session capacity: '{slug}' budget={budget} exceeds remaining "
            f"{summary['remaining']}/{cap} this session. A signal, not a gate: "
            f"consider a checkpoint, a split or a delegation. Basis for the number: "
            f"docs/ru/session-active-time.md (SENAR 1.5 §9.4(c))."
        )
    return ""


def start_advisories(be: "SQLiteBackend", slug: str, task: dict[str, Any]) -> list[str]:
    """Every advisory a task start prints, already prefixed, in a stable order.

    One function rather than a growing list of assignments at the call site: each
    advisory is the same kind of thing -- a signal, never a refusal (decision #376)
    -- and service_task.py sits at its 500-line ceiling, so a third one added there
    would have to displace something.

    An empty list is the common case: capacity is quiet until a budget is exceeded,
    and the necessity question is quiet on simple tasks by measurement.
    """
    from code_necessity import code_necessity_prompt

    out = [session_capacity_advisory(be, slug, task), code_necessity_prompt({**task, "slug": slug})]
    return [f"ℹ {line}" for line in out if line]


def record_call_actual(be: "SQLiteBackend", slug: str, task: dict[str, Any]) -> str:
    """Compute and persist call_actual = events + per-task tool counter.

    Returns a budget-overrun warning string if call_budget is set and
    actual exceeds 1.5× the budget; empty string otherwise. Always clears
    the meta counter so a future re-open starts from zero.
    """
    events_count = be.task_event_count_in_window(slug)
    meta_key = f"tool_calls:{slug}"
    raw_meta = be.meta_get(meta_key)
    try:
        tool_calls = int(raw_meta) if raw_meta else 0
    except (TypeError, ValueError):
        tool_calls = 0
    actual = events_count + tool_calls
    be.task_set_call_actual(slug, actual)
    if raw_meta is not None:
        be.meta_set(meta_key, "0")
    budget = task.get("call_budget")
    if isinstance(budget, int) and budget > 0 and actual > int(budget * 1.5):
        return (
            f"WARNING: call_actual={actual} exceeds 1.5× call_budget={budget} "
            f"for '{slug}'. Re-calibrate budget for similar tasks."
        )
    return ""


def record_cost_actual(be: "SQLiteBackend", slug: str, task: dict[str, Any]) -> str:
    """Roll up usage_events for the task window, persist cost/tokens actuals.

    Returns a budget-overrun warning string when ``cost_budget_usd`` (or
    ``token_budget``) is set and the rolled-up actual exceeds 1.5× of it;
    empty string otherwise. Pairs with :func:`record_call_actual` — sister
    function called once at task_done from service_task_done.

    Window: ``[task.started_at, ∞)``. When ``started_at`` is None (task
    closed without ever being started), uses created_at as a conservative
    lower bound. Never raises — DB / type errors return empty warning so
    task_done lifecycle never breaks.
    """
    try:
        since = task.get("started_at") or task.get("created_at") or None
        rollup = be.usage_events_cost_rollup_for_task(slug, since=since)
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return ""
    # None all the way through: a task whose events carried no measurement gets
    # NULL, not 0. `float(x or 0.0)` was the last place the absence was quietly
    # converted into the claim that the work had been free.
    raw_cost = rollup.get("cost_usd")
    raw_tokens = rollup.get("tokens_total")
    cost_actual = None if raw_cost is None else float(raw_cost)
    tokens_actual = None if raw_tokens is None else int(raw_tokens)
    try:
        be.task_set_cost_actual(slug, cost_actual)
        be.task_set_tokens_actual(slug, tokens_actual)
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return ""
    cost_budget = task.get("cost_budget_usd")
    token_budget = task.get("token_budget")
    warns: list[str] = []
    # An unmeasured cost cannot exceed a budget, and must not be read as being
    # comfortably under one either. The budget simply has nothing to compare.
    if (
        cost_actual is not None
        and isinstance(cost_budget, (int, float))
        and float(cost_budget) > 0
        and cost_actual > float(cost_budget) * 1.5
    ):
        warns.append(
            f"WARNING: cost_actual_usd=${cost_actual:.4f} exceeds 1.5× "
            f"cost_budget_usd=${float(cost_budget):.4f} for '{slug}'."
        )
    if (
        tokens_actual is not None
        and isinstance(token_budget, int)
        and token_budget > 0
        and tokens_actual > int(token_budget * 1.5)
    ):
        warns.append(
            f"WARNING: tokens_actual={tokens_actual} exceeds 1.5× "
            f"token_budget={token_budget} for '{slug}'."
        )
    return " ".join(warns)
