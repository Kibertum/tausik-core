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


def _cost_cell(model_id: Any, tokens_total: int, cost_usd: float) -> str:
    """`$X` for a priced model, an explicit absence for one we cannot price.

    A model with no price row records cost_usd=0.0 because the DB column is NOT
    NULL, so the stored zero is indistinguishable from "this was free". It is
    distinguishable HERE, where the price table can still be consulted: tokens
    on an unpriced model are reported as unpriced, not as $0.00 (decision #334 —
    a quantity that cannot be measured yields absence, not zero). Zero TOKENS on
    a known model is still $0.0000; that zero is a measurement.
    """
    if tokens_total > 0:
        # A stored zero against real tokens means the cost was NOT metered when
        # the row was written — whatever the price table says today. Consulting
        # only today's table asks "can we price this model NOW", which answers a
        # different question: `claude-fable-5-1` showed 4,282,326 tokens at
        # $0.0000 here because it had no price row when those sessions were
        # recorded and acquired one afterwards. The tokens were never metered,
        # and the report has no business calling that free.
        if cost_usd == 0.0:
            return f"not priced ({tokens_total:,} tokens unmetered)"
        try:
            from cost_pricing import get_pricing

            if get_pricing(model_id) is None:
                return f"not priced ({tokens_total:,} tokens unmetered)"
        except Exception:  # noqa: BLE001 — a broken import must not hide the table
            pass
    return f"${cost_usd:.4f}"


def format_model_usage_section(rows: list[dict[str, Any]]) -> list[str]:
    """Render the 'LLM Usage by Model' metrics subsection (empty if no rows)."""
    if not rows:
        return []
    lines = ["--- LLM Usage by Model ---", "model_id | events | tokens | cost_usd"]
    for r in rows:
        tokens = int(r.get("tokens_total") or 0)
        lines.append(
            f"{r.get('model_id') or '—'} | {int(r.get('event_count') or 0)} | "
            f"{tokens} | {_cost_cell(r.get('model_id'), tokens, float(r.get('cost_usd') or 0.0))}"
        )
    return lines
