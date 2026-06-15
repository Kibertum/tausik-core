#!/usr/bin/env python3
"""PostToolUse hook: per-task cost-budget runaway protection.

Reads the active task's ``cost_budget_usd`` (and optionally ``token_budget``)
and compares against the rolled-up ``usage_events`` since ``started_at``.
Emits a single stderr line at two thresholds:

    >= 1.5× budget AND < 2.0×  -> [TAUSIK cost-budget WARN]
    >= 2.0× budget             -> [TAUSIK cost-budget BLOCKER]

The hook NEVER blocks a tool call — Claude Code hooks can't physically
stop the agent. The BLOCKER message is advisory; the agent reads it next
turn and is expected to stop, re-plan, or run
``tausik task update --cost-budget`` to widen the budget.

Throttling: each ``(slug, level)`` pair is rate-limited to one emission
per ``COST_BUDGET_THROTTLE_SECONDS`` (default 30 s) via
``.tausik/.cost_budget_throttle.json``. Atomic write.

Silent no-op when:
    * 0 active tasks (no task to attribute against)
    * >= 2 active tasks (multi-agent ambiguity — same as task_call_counter)
    * active task has neither cost_budget_usd nor token_budget set
    * TAUSIK_SKIP_HOOKS=1
    * project DB missing / DB locked / malformed stdin

Never raises (subprocess exit 0).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from typing import Any

COST_BUDGET_THROTTLE_SECONDS = 30
_THROTTLE_BASENAME = ".cost_budget_throttle.json"


def _db_path(project_dir: str) -> str | None:
    path = os.path.join(project_dir, ".tausik", "tausik.db")
    return path if os.path.exists(path) else None


def _throttle_path(project_dir: str) -> str:
    return os.path.join(project_dir, ".tausik", _THROTTLE_BASENAME)


def _load_throttle(path: str) -> dict[str, float]:
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return {}
        out: dict[str, float] = {}
        for k, v in raw.items():
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
        return out
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _save_throttle(path: str, data: dict[str, float]) -> None:
    """Atomic write — create temp + rename. Best-effort: errors swallowed."""
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except OSError:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


def _should_emit(
    throttle: dict[str, float],
    slug: str,
    level: str,
    *,
    now: float,
    window: int = COST_BUDGET_THROTTLE_SECONDS,
) -> bool:
    key = f"{slug}:{level}"
    last = throttle.get(key, 0.0)
    return (now - last) >= window


def _active_task_with_budget(conn: sqlite3.Connection) -> dict[str, Any] | None:
    """Return single active task that has at least one of the new budgets set.

    Multi-task ambiguity (>=2 active) → returns None — same policy as
    task_call_counter for >=2 paths, but NULL if 0 budgets among them.
    """
    cur = conn.execute(
        "SELECT slug, started_at, cost_budget_usd, token_budget FROM tasks WHERE status='active'"
    )
    rows = cur.fetchall()
    if len(rows) != 1:
        return None
    slug, started_at, cost_budget, token_budget = rows[0]
    if cost_budget is None and token_budget is None:
        return None
    return {
        "slug": slug,
        "started_at": started_at,
        "cost_budget_usd": cost_budget,
        "token_budget": token_budget,
    }


def _rollup_for_task(conn: sqlite3.Connection, slug: str, since: str | None) -> tuple[float, int]:
    """Return (cost_usd, tokens_total) for usage_events of slug since."""
    if since:
        sql = (
            "SELECT COALESCE(SUM(cost_usd),0) AS cost, "
            "COALESCE(SUM(tokens_total),0) AS toks "
            "FROM usage_events WHERE task_slug=? AND recorded_at>=?"
        )
        params: tuple[Any, ...] = (slug, since)
    else:
        sql = (
            "SELECT COALESCE(SUM(cost_usd),0) AS cost, "
            "COALESCE(SUM(tokens_total),0) AS toks "
            "FROM usage_events WHERE task_slug=?"
        )
        params = (slug,)
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    if row is None:
        return 0.0, 0
    return float(row[0] or 0.0), int(row[1] or 0)


def _classify_level(actual: float, budget: float) -> str | None:
    """Return 'BLOCKER' (>= 2.0×), 'WARN' (>= 1.5× < 2.0×), or None."""
    if budget <= 0:
        return None
    ratio = actual / float(budget)
    if ratio >= 2.0:
        return "BLOCKER"
    if ratio >= 1.5:
        return "WARN"
    return None


def _format_msg(
    slug: str,
    level: str,
    *,
    cost_actual: float,
    cost_budget: float | None,
    tokens_actual: int,
    token_budget: int | None,
    trigger: str,
) -> str:
    """Compose the stderr line for the chosen level + trigger ('cost'|'tokens')."""
    if level == "BLOCKER":
        cap_label = "2× hard cap reached — stop and re-plan or `tausik task update --cost-budget`"
    else:
        cap_label = "1.5× soft cap"
    if trigger == "cost" and cost_budget is not None:
        body = f"task {slug} at ${cost_actual:.4f} / ${float(cost_budget):.4f} ({cap_label})"
    elif trigger == "tokens" and token_budget is not None:
        body = f"task {slug} at {tokens_actual} / {token_budget} tokens ({cap_label})"
    else:
        body = f"task {slug} ({cap_label})"
    return f"[TAUSIK cost-budget {level}] {body}"


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        pass

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    db = _db_path(project_dir)
    if not db:
        return 0

    try:
        conn = sqlite3.connect(db, timeout=2)
        try:
            task = _active_task_with_budget(conn)
            if task is None:
                return 0
            slug = task["slug"]
            cost_budget = task["cost_budget_usd"]
            token_budget = task["token_budget"]
            cost_actual, tokens_actual = _rollup_for_task(conn, slug, task.get("started_at"))
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001 — best-effort hook
        print(f"task_cost_budget_check: {exc}", file=sys.stderr)
        return 0

    cost_level = (
        _classify_level(cost_actual, float(cost_budget)) if cost_budget is not None else None
    )
    token_level = (
        _classify_level(float(tokens_actual), float(token_budget))
        if token_budget is not None
        else None
    )

    chosen_level: str | None = None
    chosen_trigger: str | None = None
    if cost_level == "BLOCKER" or token_level == "BLOCKER":
        chosen_level = "BLOCKER"
        chosen_trigger = "cost" if cost_level == "BLOCKER" else "tokens"
    elif cost_level == "WARN" or token_level == "WARN":
        chosen_level = "WARN"
        chosen_trigger = "cost" if cost_level == "WARN" else "tokens"

    if chosen_level is None or chosen_trigger is None:
        return 0

    throttle_path = _throttle_path(project_dir)
    throttle = _load_throttle(throttle_path)
    now = time.time()
    if not _should_emit(throttle, slug, chosen_level, now=now):
        return 0
    throttle[f"{slug}:{chosen_level}"] = now
    _save_throttle(throttle_path, throttle)

    msg = _format_msg(
        slug,
        chosen_level,
        cost_actual=cost_actual,
        cost_budget=cost_budget,
        tokens_actual=tokens_actual,
        token_budget=token_budget,
        trigger=chosen_trigger,
    )
    print(msg, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
