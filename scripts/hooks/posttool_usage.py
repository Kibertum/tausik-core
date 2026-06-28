#!/usr/bin/env python3
"""PostToolUse hook: append a usage_events row attributed to the active task.

Records every tool call as a separate `usage_events` row so that
`tausik metrics cost` can attribute tokens/cost per task. Best-effort
across the whole pipeline — never blocks the harness:

  - Stdin malformed/empty → exit 0, nothing inserted.
  - No active task → row inserted with task_slug=NULL.
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
from cost_pricing import calculate_cost_usd, get_pricing  # noqa: E402

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


def _extract_usage(payload: dict) -> tuple[int, int, str | None]:
    """Pull (tokens_input, tokens_output, model_id) out of the harness payload.

    Anthropic-style extended schema may carry `tool_response.usage` or
    `tool_response.message.usage` with `input_tokens` / `output_tokens`.
    Older schemas don't expose this — return zeros + None.
    """
    response = payload.get("tool_response")
    if not isinstance(response, dict):
        return 0, 0, None
    usage = response.get("usage")
    if not isinstance(usage, dict):
        msg = response.get("message")
        if isinstance(msg, dict):
            usage = msg.get("usage")
    if not isinstance(usage, dict):
        usage = {}
    ti = int(usage.get("input_tokens") or 0)
    to = int(usage.get("output_tokens") or 0)
    model = response.get("model") or (
        response.get("message", {}).get("model")
        if isinstance(response.get("message"), dict)
        else None
    )
    if not isinstance(model, str) or not model.strip():
        model = None
    return ti, to, model


def _current_session_id(conn: sqlite3.Connection) -> int | None:
    """Return id of the most recent open (ended_at IS NULL) session, else None."""
    row = conn.execute(
        "SELECT id FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return int(row[0]) if row else None


def _insert_event(
    conn: sqlite3.Connection,
    session_id: int,
    task_slug: str | None,
    model_id: str | None,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
    tool_name: str | None,
) -> None:
    """Single INSERT into usage_events (source='posttool')."""
    conn.execute(
        "INSERT INTO usage_events("
        "session_id,task_slug,model_id,tokens_input,tokens_output,tokens_total,"
        "cost_usd,tool_calls,source,recorded_at,tool_name"
        ") VALUES(?,?,?,?,?,?,?,?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'),?)",
        (
            session_id,
            task_slug,
            model_id,
            int(tokens_input),
            int(tokens_output),
            int(tokens_input + tokens_output),
            float(cost_usd),
            1,
            "posttool",
            tool_name,
        ),
    )
    conn.commit()


def _record_with_retries(
    db_path: str,
    session_id: int,
    task_slug: str | None,
    model_id: str | None,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
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

    if model_id and get_pricing(model_id) is None and (tokens_input or tokens_output):
        print(
            f"posttool_usage: unknown model_id {model_id!r}; cost_usd=0.0",
            file=sys.stderr,
        )

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

    if session_id is None:
        return 0

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
