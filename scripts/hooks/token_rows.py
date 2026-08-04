#!/usr/bin/env python3
"""Per-tool token rows and the `.tausik/token_metrics.jsonl` writer.

Split out of `session_metrics` at the 400-line cap. One coherent concern:
walk a transcript, emit one row per tool_use, and persist the rows for a
session — separate from the session-level rollup that computes cost and
writes `session-metrics.json`.

The writer REPLACES a session's rows rather than appending. `extract_token_rows`
re-derives a session's complete set from the transcript on every call, so
appending duplicated every row on each SessionEnd re-run — the file reached
191 MB that way. Replace-by-session is idempotent by construction.

Names are re-exported from `session_metrics` for existing callers.
"""

import json
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def extract_token_rows(path: str, session_id: int) -> list[dict]:
    """Walk transcript JSONL, emit one row per tool_use occurrence.

    Schema matches service_token_metrics.aggregate(): ts, session_id, tool_name,
    input_tokens, output_tokens, cache_read, cache_create, model. API usage is
    message-level, so per-tool attribution divides input/output/cache_* equally
    across tool_use blocks in the same assistant entry; the last block absorbs
    the integer-division remainder so totals stay exact. Pure-text turns and
    entries without tool_use blocks emit no rows.
    """
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "assistant":
                continue
            msg = entry.get("message") if isinstance(entry.get("message"), dict) else {}
            usage = entry.get("usage") or msg.get("usage") or {}
            if not isinstance(usage, dict) or not usage:
                continue
            content = entry.get("content") or msg.get("content") or []
            if not isinstance(content, list):
                continue
            tool_uses = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
            if not tool_uses:
                continue
            n = len(tool_uses)
            ts = entry.get("timestamp") or ""
            input_tokens = int(usage.get("input_tokens") or 0)
            output_tokens = int(usage.get("output_tokens") or 0)
            cache_read = int(usage.get("cache_read_input_tokens") or 0)
            cache_create = int(usage.get("cache_creation_input_tokens") or 0)
            entry_model = entry.get("model") or msg.get("model") or None
            if not isinstance(entry_model, str) or not entry_model.strip():
                entry_model = None

            def _split(total: int, idx: int) -> int:
                base = total // n
                if idx == n - 1:
                    return total - base * (n - 1)
                return base

            for i, tu in enumerate(tool_uses):
                rows.append(
                    {
                        "ts": ts,
                        "session_id": session_id,
                        "tool_name": tu.get("name") or "(unknown)",
                        "input_tokens": _split(input_tokens, i),
                        "output_tokens": _split(output_tokens, i),
                        "cache_read": _split(cache_read, i),
                        "cache_create": _split(cache_create, i),
                        "model": entry_model,
                    }
                )
    return rows


#: Size ceiling for .tausik/token_metrics.jsonl. The file had no cap at all and
#: reached 191 MB on this project. Oldest rows are dropped first: token
#: attribution is only useful for recent sessions, and the DB keeps the
#: authoritative per-session totals regardless.
TOKEN_METRICS_MAX_BYTES = 32 * 1024 * 1024


def _surviving_lines(path: str, drop_sessions: set, max_bytes: int) -> list[str]:
    """Existing lines to keep: not from `drop_sessions`, newest within `max_bytes`.

    Streams the file and holds at most `max_bytes` of it, because the file this
    was written for was 191 MB — reading it whole would trade a disk problem for
    a memory one. Unparseable lines are dropped rather than aborting the write:
    losing one malformed metrics row is strictly better than losing the file.
    """
    kept: deque[str] = deque()
    size = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                try:
                    if json.loads(line).get("session_id") in drop_sessions:
                        continue
                except (json.JSONDecodeError, AttributeError):
                    continue
                kept.append(line)
                size += len(line.encode("utf-8")) + 1
                while size > max_bytes and kept:
                    size -= len(kept.popleft().encode("utf-8")) + 1
    except OSError as exc:
        print(f"token_metrics.jsonl read failed: {exc}", file=sys.stderr)
        return []
    return list(kept)


def replace_session_token_rows(
    rows: list[dict],
    project_dir: str | None = None,
    max_bytes: int = TOKEN_METRICS_MAX_BYTES,
) -> str | None:
    """Record `rows` in .tausik/token_metrics.jsonl. Returns path or None on no-op.

    REPLACES the rows already stored for the sessions in `rows` rather than
    appending to them. `extract_token_rows` re-derives a session's *complete*
    set from the transcript on every call, so appending duplicated every row on
    every re-run of the SessionEnd hook — which is how the file reached 191 MB.
    Replace-by-session makes a re-run idempotent by construction, with no need
    to track offsets or per-row identity.

    Writes via a temp file and os.replace so an interrupted run cannot leave a
    truncated metrics file behind.
    """
    if not rows:
        return None
    proj = project_dir or os.getcwd()
    tausik_dir = os.path.join(proj, ".tausik")
    if not os.path.isdir(tausik_dir):
        return None
    path = os.path.join(tausik_dir, "token_metrics.jsonl")

    new_lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    sessions = {r.get("session_id") for r in rows}
    budget = max(0, max_bytes - sum(len(s.encode("utf-8")) + 1 for s in new_lines))
    old_lines = _surviving_lines(path, sessions, budget) if os.path.exists(path) else []

    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            for line in old_lines:
                fh.write(line + "\n")
            for line in new_lines:
                fh.write(line + "\n")
        os.replace(tmp, path)
    except OSError as exc:
        print(f"token_metrics.jsonl write failed: {exc}", file=sys.stderr)
        try:
            os.remove(tmp)
        except OSError:
            pass
        return None
    return path
