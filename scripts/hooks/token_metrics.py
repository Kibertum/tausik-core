#!/usr/bin/env python3
"""PostToolUse hook: append a token_metrics row to .tausik/token_metrics.jsonl.

Captures per-tool-call token usage (incl. prompt-cache fields) for baseline
analysis and Phase B Gate A decision. Distinct from posttool_usage.py which
records to the usage_events DB table for per-task cost rollup; this hook
writes append-only JSONL telemetry suitable for cross-session aggregation.

Schema (one JSON object per line):
    {
      "ts": "2026-05-06T12:34:56Z",
      "session_id": 53,
      "tool_name": "Read",
      "input_tokens": 1234,
      "output_tokens": 56,
      "cache_read": 4321,
      "cache_create": 0,
      "model": "claude-opus-4-7"
    }

Best-effort across the entire pipeline — never blocks the harness:
  - Stdin malformed/empty → exit 0, nothing appended.
  - Missing usage block → exit 0, nothing appended (avoid noise).
  - No `.tausik/` dir (not a TAUSIK project) → exit 0 silently.
  - JSONL write IO error → stderr warning, exit 0.

Skipped via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time

_JSONL_RELPATH = os.path.join(".tausik", "token_metrics.jsonl")


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


def _extract_usage(payload: dict) -> dict[str, int | str | None]:
    """Pull token counters + model out of the harness payload.

    Anthropic-style schema may carry `tool_response.usage` or
    `tool_response.message.usage` with `input_tokens`, `output_tokens`,
    `cache_read_input_tokens`, `cache_creation_input_tokens`. Older schemas
    don't expose this — return zeros + None.
    """
    response = payload.get("tool_response")
    if not isinstance(response, dict):
        return {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0, "model": None}
    usage = response.get("usage")
    if not isinstance(usage, dict):
        msg = response.get("message")
        if isinstance(msg, dict):
            usage = msg.get("usage")
    if not isinstance(usage, dict):
        usage = {}
    model = response.get("model") or (
        response.get("message", {}).get("model")
        if isinstance(response.get("message"), dict)
        else None
    )
    if not isinstance(model, str) or not model.strip():
        model = None
    return {
        "input": int(usage.get("input_tokens") or 0),
        "output": int(usage.get("output_tokens") or 0),
        "cache_read": int(usage.get("cache_read_input_tokens") or 0),
        "cache_create": int(usage.get("cache_creation_input_tokens") or 0),
        "model": model,
    }


def _current_session_id(db_path: str) -> int | None:
    """Return id of the most recent open session, or None on any error."""
    try:
        conn = sqlite3.connect(db_path, timeout=2, isolation_level=None)
        try:
            row = conn.execute(
                "SELECT id FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return int(row[0]) if row else None
        finally:
            conn.close()
    except sqlite3.Error:
        return None


def _utcnow_iso() -> str:
    """ISO-8601 UTC timestamp with 'Z' suffix (matches tausik_utils.utcnow_iso)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    tausik_dir = os.path.join(project_dir, ".tausik")
    if not os.path.isdir(tausik_dir):
        return 0
    db_path = os.path.join(tausik_dir, "tausik.db")
    if not os.path.exists(db_path):
        return 0

    payload = _load_payload()
    tool_name_raw = payload.get("tool_name") if isinstance(payload, dict) else None
    tool_name = (str(tool_name_raw).strip() if tool_name_raw else "") or None

    usage = _extract_usage(payload)
    # Skip events with no usage signal at all — keeps the JSONL high-signal.
    if not (usage["input"] or usage["output"] or usage["cache_read"] or usage["cache_create"]):
        return 0

    session_id = _current_session_id(db_path)
    if session_id is None:
        return 0

    record = {
        "ts": _utcnow_iso(),
        "session_id": session_id,
        "tool_name": tool_name,
        "input_tokens": usage["input"],
        "output_tokens": usage["output"],
        "cache_read": usage["cache_read"],
        "cache_create": usage["cache_create"],
        "model": usage["model"],
    }

    jsonl_path = os.path.join(project_dir, _JSONL_RELPATH)
    try:
        with open(jsonl_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"token_metrics: append failed: {exc}", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
