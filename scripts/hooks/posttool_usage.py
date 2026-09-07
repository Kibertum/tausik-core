#!/usr/bin/env python3
"""PostToolUse hook: append a usage_events row attributed to the active task.

Records every tool call as a separate `usage_events` row so that
`tausik metrics cost` can attribute tokens/cost per task. Best-effort
across the whole pipeline — never blocks the harness:

  - Stdin malformed/empty → exit 0, nothing inserted.
  - No active task → row inserted with task_slug=NULL.
  - No open session → row inserted with session_id=NULL (v48; it used to
    be dropped whole, losing the task attribution it already had).
  - Unknown model_id (not in cost_pricing) → cost_usd=0.0 + stderr warn.
  - DB locked → up to 3 retries, then stderr warn + exit 0.
  - No `.tausik/tausik.db` (not a TAUSIK project) → exit 0 silently.

Token counts come from the harness payload when present (Anthropic
extended hook schema sometimes includes `usage` in tool_response). When
absent, the row is still written with tokens=0 + tool_calls=1 so the
event count itself remains accurate for per-task attribution.

Skipped via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _common import current_active_task_slug  # noqa: E402
from cost_pricing import calculate_cost_usd  # noqa: E402

_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_SEC = 0.05


def _load_payload() -> dict:
    """Best-effort stdin JSON load. Empty/malformed → empty dict."""
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


#: Where a usage dict has been seen to live, in the order the shapes are tried.
#: Each entry is a path through the payload. A shape nobody has seen is not
#: guessed at: it yields ABSENCE, and absence is a different statement from zero.
_USAGE_PATHS: tuple[tuple[str, ...], ...] = (
    ("tool_response", "usage"),
    ("tool_response", "message", "usage"),
    ("usage",),
    ("message", "usage"),
)

#: Where the model id has been seen to live. Same rule.
_MODEL_PATHS: tuple[tuple[str, ...], ...] = (
    ("tool_response", "model"),
    ("tool_response", "message", "model"),
    ("model",),
    ("message", "model"),
)


def _dig(payload: dict, path: tuple[str, ...]):
    """Walk `path` through nested dicts; None the moment a step is not a dict."""
    node = payload
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _extract_usage(payload: dict) -> tuple[int | None, int | None, str | None]:
    """(tokens_input, tokens_output, model_id), where None means NOT MEASURED.

    THE NUMBERS ARE None WHEN NOTHING CARRIED THEM, never 0. Measured on this
    project in session #231 before the change: 55,288 of 55,583 usage_events —
    99.5% — recorded 0/0 with no model, and 55,471 recorded a cost of exactly
    $0.00. Not one row said "unknown". The product asserted 55,471 times that a
    piece of work had cost nothing.

    The cause was reading `tool_response.usage`. A TOOL result structurally has
    no usage; usage belongs to the model's message. Bash (26,129 rows), Read
    (7,385), Edit (6,346), Grep, Write and every MCP tool never carried it and
    never will. `Agent` is the only tool that does, at 75 rows.

    So the shapes are tried as ADAPTERS and an unknown one yields absence — which
    is what decision #334 requires and what SQLite's SUM then handles for free,
    skipping NULL and returning NULL when there was nothing to add.

    A genuine zero survives as zero: a payload that really says
    `input_tokens: 0` is a measurement, and flattening it into absence would be
    the same crime in the other direction.
    """
    usage = None
    for path in _USAGE_PATHS:
        candidate = _dig(payload, path)
        if isinstance(candidate, dict):
            usage = candidate
            break

    model = None
    for path in _MODEL_PATHS:
        candidate = _dig(payload, path)
        if isinstance(candidate, str) and candidate.strip():
            model = candidate
            break

    if usage is None:
        return None, None, model

    ti = _as_token_count(usage.get("input_tokens"))
    to = _as_token_count(usage.get("output_tokens"))
    if ti is None and to is None:
        # The dict was there and said nothing readable about tokens. Still not a
        # measurement — reporting 0 here would launder an unparseable payload
        # into a number.
        return None, None, model
    return ti, to, model


def _as_token_count(raw) -> int | None:
    """A non-negative int, or None when the value is missing or unreadable."""
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _current_session_id(conn: sqlite3.Connection) -> int | None:
    """Return id of the most recent open (ended_at IS NULL) session, else None."""
    row = conn.execute(
        "SELECT id FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return int(row[0]) if row else None


def _total_or_none(ti: int | None, to: int | None) -> int | None:
    """Sum of what was measured, or None when neither side was.

    NOT `(ti or 0) + (to or 0)`: a payload that reported input and not output
    has measured one of the two, and calling the missing half zero would put a
    total in the row that no payload supports.
    """
    if ti is None and to is None:
        return None
    return (ti or 0) + (to or 0)


def _insert_event(
    conn: sqlite3.Connection,
    session_id: int | None,
    task_slug: str | None,
    model_id: str | None,
    tokens_input: int | None,
    tokens_output: int | None,
    cost_usd: float | None,
    tool_name: str | None,
) -> None:
    """Single INSERT into usage_events (source='posttool').

    None reaches the database as NULL and means NOT MEASURED. The row is still
    written: the tool call happened and `tool_calls` records it. What the row
    stops claiming is a token count and a price nobody observed.
    """
    conn.execute(
        "INSERT INTO usage_events("
        "session_id,task_slug,model_id,tokens_input,tokens_output,tokens_total,"
        "cost_usd,tool_calls,source,recorded_at,tool_name"
        ") VALUES(?,?,?,?,?,?,?,?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'),?)",
        (
            session_id,
            task_slug,
            model_id,
            None if tokens_input is None else int(tokens_input),
            None if tokens_output is None else int(tokens_output),
            _total_or_none(tokens_input, tokens_output),
            None if cost_usd is None else float(cost_usd),
            1,
            "posttool",
            tool_name,
        ),
    )
    conn.commit()


def _record_with_retries(
    db_path: str,
    session_id: int | None,
    task_slug: str | None,
    model_id: str | None,
    tokens_input: int | None,
    tokens_output: int | None,
    cost_usd: float | None,
    tool_name: str | None,
) -> bool:
    """Open DB and INSERT; retry on SQLITE_BUSY. Returns True on success."""
    last_exc: Exception | None = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            conn = sqlite3.connect(db_path, timeout=2, isolation_level=None)
            try:
                _insert_event(
                    conn,
                    session_id,
                    task_slug,
                    model_id,
                    tokens_input,
                    tokens_output,
                    cost_usd,
                    tool_name,
                )
                return True
            finally:
                conn.close()
        except sqlite3.OperationalError as exc:
            last_exc = exc
            if "lock" not in str(exc).lower() and "busy" not in str(exc).lower():
                break
            time.sleep(_RETRY_BACKOFF_SEC * (attempt + 1))
        except sqlite3.Error as exc:
            last_exc = exc
            break
    if last_exc is not None:
        print(f"posttool_usage: insert failed after retries: {last_exc}", file=sys.stderr)
    return False


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    db_path = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(db_path):
        return 0

    payload = _load_payload()

    tool_name_raw = payload.get("tool_name") if isinstance(payload, dict) else None
    tool_name = (str(tool_name_raw).strip() if tool_name_raw else "") or None

    tokens_input, tokens_output, model_id = _extract_usage(payload)

    # The unpriced-model warning is owned by `calculate_cost_usd` now: it fires
    # once per id and, unlike the old inline check here, consults the project's
    # `llm_pricing_usd_per_million` override before calling a model unpriced —
    # so a GLM/custom model the project HAS priced no longer prints a false
    # "unknown model" line and then records a non-zero cost.
    cost_usd = calculate_cost_usd(model_id, tokens_input, tokens_output)
    task_slug = current_active_task_slug(project_dir)

    try:
        conn = sqlite3.connect(db_path, timeout=2, isolation_level=None)
        try:
            session_id = _current_session_id(conn)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        print(f"posttool_usage: cannot read session: {exc}", file=sys.stderr)
        return 0

    # NO DROP WHEN THERE IS NO OPEN SESSION. Until v48 this read
    # `if session_id is None: return 0` — the event was thrown away WHOLE even
    # though `task_slug` was already known one line above. The schema forced it:
    # `usage_events.session_id` was NOT NULL, so there was nowhere to put an
    # event that belonged to a task but to no session. v48 makes the column
    # optional and the task the primary attribution, so the row is simply
    # written with session_id=NULL. An event with neither task nor session is
    # written too, and surfaces in the «вне задачи» bucket of
    # `tausik metrics cost` — it is not allowed to disappear quietly either.
    _record_with_retries(
        db_path,
        session_id,
        task_slug,
        model_id,
        tokens_input,
        tokens_output,
        cost_usd,
        tool_name,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
