"""RENAR per-task model pinning helpers (v16r-model-pinning).

Pure helpers, kept out of service_task_done.py / project_cli_ops.py so those
stay under the 400-line filesize cap. Pin the agent model at task start/done
and flag mid-task model changes via the usage_events↔task link.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


def session_model(be: SQLiteBackend) -> tuple[str | None, str | None]:
    """(model_id, model_version) of the current open session, or (None, None)."""
    sess = be.session_current()
    if not sess:
        return None, None
    return sess.get("model_id"), sess.get("model_version")


def model_start_updates(be: SQLiteBackend) -> dict[str, Any]:
    """tasks columns to set at task_start — pins the model active at start."""
    mid, ver = session_model(be)
    return {"started_model_id": mid, "started_model_version": ver}


def model_done_updates(
    be: SQLiteBackend, task: dict[str, Any]
) -> tuple[dict[str, Any], str | None]:
    """tasks columns to set at task_done, plus an optional mismatch message.

    ``model_mismatch`` is 1 when more than one distinct model_id appears across
    {started, done} ∪ usage_events.model_id for the task — i.e. the model
    changed at some point between activation and closure.
    """
    slug = task["slug"]
    done_id, done_ver = session_model(be)
    started_id = task.get("started_model_id")
    used = set(be.task_model_ids(slug))
    distinct = {m for m in ({started_id, done_id} | used) if m}
    mismatch = 1 if len(distinct) > 1 else 0
    updates: dict[str, Any] = {
        "done_model_id": done_id,
        "done_model_version": done_ver,
        "model_mismatch": mismatch,
    }
    msg = None
    if mismatch:
        # 'WARNING:' prefix so the CLI routes it to stderr like other warnings.
        msg = (
            f"WARNING: Model mismatch — task touched multiple models: {', '.join(sorted(distinct))}"
        )
    return updates, msg


def format_model_usage_section(rows: list[dict[str, Any]]) -> list[str]:
    """Render the 'LLM Usage by Model' metrics subsection (empty if no rows)."""
    if not rows:
        return []
    lines = ["--- LLM Usage by Model ---", "model_id | events | tokens | cost_usd"]
    for r in rows:
        lines.append(
            f"{r.get('model_id') or '—'} | {int(r.get('event_count') or 0)} | "
            f"{int(r.get('tokens_total') or 0)} | ${float(r.get('cost_usd') or 0.0):.4f}"
        )
    return lines
