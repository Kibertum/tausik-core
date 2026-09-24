"""Journal freshness is a signal, not a rule the agent must remember (1.10, story E).

"Log after every step" lived only as a line in CLAUDE.md — the class of rule
that fails under context pressure, and a compaction then loses whatever
happened between two entries. Measured before this module (session #266, the
last 80 closed tasks, 218 gaps between consecutive task-log entries, calls
counted from `usage_events` per task): median 0, p90 2, 9 gaps of 20 calls or
more, 3 of 40 or more, maximum 209. Logging is usually immediate; the tail is
real. The default threshold of 40 catches that tail (1.4% of gaps).

Per TASK, not per session: the count comes from `usage_events` rows attributed
to the task since its last log entry, so the signal works with no session open.
A signal only — no closure is refused on it (decision #376: hygiene is a
signal); a refusal would teach writing an empty log line before `task done`.
"""

from __future__ import annotations

from typing import Any

DEFAULT_THRESHOLD = 40


def calls_since_last_log(be: Any, slug: str) -> int:
    """Tool calls attributed to `slug` since its last log entry (or since it started)."""
    logs = be.task_log_list(slug)
    task = be.task_get(slug) or {}
    since = logs[-1]["created_at"] if logs else task.get("started_at")
    rows = be.usage_events_cost_rollup_by_task(since=since) if since else []
    return sum(int(r["event_count"]) for r in rows if r["task_slug"] == slug)


def freshness_advice(be: Any, threshold: int = DEFAULT_THRESHOLD) -> str:
    """Advice for active tasks whose journal went quiet, once per ten-call bucket."""
    if threshold <= 0:
        return ""  # 0 switches the signal off
    lines: list[str] = []
    for task in be.task_list(status="active") or []:
        slug = task["slug"]
        n = calls_since_last_log(be, slug)
        key = f"journal_warn_bucket:{slug}"
        if n < threshold:
            if be.meta_get(key):
                be.meta_delete(key)
            continue
        bucket = n // 10
        try:
            last = int(be.meta_get(key) or 0)
        except (ValueError, TypeError):
            last = 0
        if bucket <= last:
            continue
        be.meta_set(key, str(bucket))
        lines.append(
            f"\n⚠ Journal: '{slug}' has {n} tool calls since its last log entry — "
            f'record the step: tausik task log {slug} "…"'
        )
    return "".join(lines)
