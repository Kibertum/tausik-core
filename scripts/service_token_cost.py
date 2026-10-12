"""Price-weighted cost of the recorded calls, in total and per task.

Separate from `service_token_metrics` for one reason worth naming: that module
answers "how many tokens", this one answers "how much money and for which task".
The split also kept both files under the 500-line cap, which is the lesser reason
and the one that would not justify a module on its own.

WHY PER TASK. Every turn re-sends the whole prefix, so a change that shrinks one
request while adding a turn is invisible per request and plain per task. Session
#277 measured cache_read at 99.5% of all input across 5964 recorded calls, which
is what makes the turn count the dominant term rather than the prefix size.
"""

from __future__ import annotations

import os
from typing import Any

from service_token_metrics import (
    _JSONL_RELPATH,
    _filter_last_n_sessions,
    _read_records,
)


def _comparable(stamp: Any) -> str | None:
    """An ISO stamp cut to second precision with a single spelling of UTC.

    Two eras of this database spell the zone differently -- `2026-03-14T11:37:49+00:00`
    and `2026-09-26T16:30:59.287Z` -- and a plain string comparison between them is
    wrong in a way that shows as "no data": `+` sorts before `Z`, so an old window
    never contains a new call. Millisecond precision is dropped because one side
    never had it.
    """
    if not isinstance(stamp, str) or len(stamp) < 19:
        return None
    return stamp[:19] + "Z"


def per_task(rows: list[dict[str, Any]], windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cost and turns per task slug. Rows outside every window are dropped.

    `windows` is `[{slug, started_at, completed_at}]`. A call is attributed to the
    task whose window contains its timestamp and is NARROWEST -- tasks overlap
    (one opened while another waits), and the narrower window is the one the work
    was actually inside. The rule is stated because any rule here is arguable, and
    a silent one would make the numbers unreadable.

    Cost per TASK rather than per request is the point: every turn re-sends the
    whole prefix, so a change that shrinks a request while adding a turn is only
    visible at this granularity. Session #277 measured cache_read at 99.5% of all
    input, which is what makes the turn count the dominant term.
    """
    from token_price import breakdown, load_prices

    prices = load_prices()
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        stamp = _comparable(row.get("ts"))
        if stamp is None:
            continue
        best: tuple[str, str] | None = None
        for window in windows:
            start = _comparable(window.get("started_at"))
            end = _comparable(window.get("completed_at"))
            if start is None or end is None:
                continue
            if start <= stamp <= end and (best is None or end < best[1]):
                best = (str(window["slug"]), end)
        if best:
            buckets.setdefault(best[0], []).append(row)
    out: list[dict[str, Any]] = []
    for slug, task_rows in buckets.items():
        cost = breakdown(task_rows, prices)
        cache_read = cost["tokens"]["cache_read"]
        fresh = cost["tokens"]["input"] + cost["tokens"]["cache_create"]
        out.append(
            {
                "slug": slug,
                "turns": len(task_rows),
                "usd_total": cost["usd_total"],
                "cache_hit_share": (
                    round(cache_read / (cache_read + fresh), 4) if cache_read + fresh else None
                ),
                "tokens": cost["tokens"],
                "unpriced_calls": cost["unpriced_calls"],
            }
        )
    out.sort(key=lambda entry: entry["turns"], reverse=True)
    return out


def task_windows() -> list[dict[str, Any]]:
    """Closed tasks with both timestamps, read through the backend, not raw SQL.

    Takes no project argument: `get_service` resolves the project itself, and a
    second way to say where the project is would be a second source of truth.
    """
    try:
        from service_factory import get_service

        svc = get_service()
    except Exception:  # noqa: BLE001 — no database: no attribution, not a crash
        return []
    try:
        # НЕ limit=400: список отдаёт САМЫЕ СТАРЫЕ задачи, и на этом дереве первые
        # четыреста закрыты в марте-апреле, тогда как телеметрия начинается в
        # сентябре. Ограничение здесь дало бы честный ноль по неверной причине.
        tasks = svc.task_list("done", None, None, None, None, limit=100000)
    except Exception:  # noqa: BLE001
        return []
    return [
        {"slug": t["slug"], "started_at": t["started_at"], "completed_at": t["completed_at"]}
        for t in tasks
        if t.get("started_at") and t.get("completed_at")
    ]


def cost_section(last_n: int = 10) -> dict[str, Any]:
    """Price-weighted cost for the window, plus the same figures per task.

    Cost is reported at TASK granularity as well as in total, because every turn
    re-sends the whole prefix: a change that shrinks one request while adding a
    turn only shows its true price here. Session #277 measured cache_read at 99.5%
    of all input, which is what makes the turn count the dominant term.
    """
    from token_price import breakdown, load_prices

    path = os.path.join(os.getcwd(), _JSONL_RELPATH)
    rows = _filter_last_n_sessions(_read_records(path), last_n)
    prices = load_prices()
    total = breakdown(rows, prices)
    return {"window_sessions": last_n, "total": total, "per_task": per_task(rows, task_windows())}


def format_cost(section: dict[str, Any], top: int = 8) -> str:
    """Human lines for `cost_section`.

    The per-task table is sorted by TURNS rather than by dollars: with an unpriced
    model the dollar column is absent by design, and a table that collapses when
    prices are unset would be read as a broken feature rather than as an honest one.
    """
    from token_price import format_breakdown

    lines = [f"Cost over the last {section['window_sessions']} session(s):", ""]
    lines.append(format_breakdown(section["total"]))
    # Сортировка ЗДЕСЬ, а не только в `per_task`: подпись обещает "top by turns",
    # и таблица, напечатанная в порядке вызывающего, сделала бы подпись ложной.
    rows = sorted(section["per_task"], key=lambda entry: entry.get("turns", 0), reverse=True)
    if not rows:
        lines.append("")
        lines.append(
            "Per task: nothing attributed. A call belongs to a task whose window "
            "contains it, so an unclosed task or telemetry older than every window "
            "leaves this empty."
        )
        return "\n".join(lines)
    lines.append("")
    lines.append(f"Per task (top {min(top, len(rows))} by turns):")
    lines.append(f"  {'turns':>6}  {'cache':>6}  {'usd':>9}  slug")
    for entry in rows[:top]:
        usd = f"{entry['usd_total']:.4f}" if entry["usd_total"] is not None else "unpriced"
        share = f"{entry['cache_hit_share']:.1%}" if entry["cache_hit_share"] is not None else "—"
        lines.append(f"  {entry['turns']:>6}  {share:>6}  {usd:>9}  {entry['slug']}")
    return "\n".join(lines)


__all__ = ["cost_section", "format_cost", "per_task", "task_windows"]
