#!/usr/bin/env python3
"""PostToolUse hook: auto-cache WebFetch results into brain.web_cache.

Companion to `brain_search_proactive.py`: that PreToolUse hook reads
the cache to block redundant network calls; this one writes to it so
the next read has something to find.

Scope — WebFetch only:
  The tool gives us a clean (url, content) pair. We write one row per
  fetched URL.

WebSearch is intentionally NOT cached: a WebSearch response is a block
of markdown covering several result URLs at once, and attributing a
single canonical URL to that blob would be lossy. The pre-hook already
services WebSearch queries via FTS over web_cache content written by
WebFetch, which covers the interesting case (someone searched, someone
else fetched a result, next search hits the cache).

Non-blocking: always exits 0 — a write failure must not break the main
flow. Skip conditions (all silent): TAUSIK_SKIP_HOOKS set, brain disabled,
token missing, mirror DB missing, URL matches `brain.private_url_patterns`,
URL already in the mirror fresh (within ttl_web_cache_days), content
empty or oversized, stdin malformed.

Diagnostics go to stderr only when TAUSIK_BRAIN_HOOK_DEBUG=1.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sqlite3
import sys

_HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.dirname(_HOOK_DIR)
if _HOOK_DIR not in sys.path:
    sys.path.insert(0, _HOOK_DIR)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)


# Claude Code hook payloads are small; cap the read so a malformed or
# hostile stdin can't keep the hook alive past its subprocess timeout.
_STDIN_SIZE_CAP = 1_048_576  # 1 MiB

# Upper bound on the `content` field we store in Notion. Notion's rich_text
# chunker in brain_mcp_write handles long content, but we also don't want
# to mirror multi-megabyte pages — the local FTS gets slow and the write
# burns API time. Truncate above this threshold.
_CONTENT_SIZE_CAP = 200_000  # ~200 KB of text


def _debug(msg: str) -> None:
    if os.environ.get("TAUSIK_BRAIN_HOOK_DEBUG"):
        print(f"[brain_post_webfetch] {msg}", file=sys.stderr)


def _read_stdin_json() -> dict:
    try:
        raw = sys.stdin.read(_STDIN_SIZE_CAP + 1)
    except (OSError, ValueError):
        return {}
    if len(raw) > _STDIN_SIZE_CAP:
        return {}
    try:
        data = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _extract_webfetch(tool_input: dict, tool_response: object) -> tuple[str, str, str]:
    """Return (url, content, query) from a WebFetch tool_response.

    tool_input shape (Claude Code): {"url": str, "prompt": str, ...}
    tool_response shape (observed): dict with keys {"result": str, "url": str,
      "code": int, "bytes": int, "durationMs": int, ...}. Some environments
      surface the response as a bare string (the `result` text). Support both.

    Returns empty strings when anything is missing — caller skips on empty.
    """
    url = tool_input.get("url") if isinstance(tool_input, dict) else None
    prompt = tool_input.get("prompt") if isinstance(tool_input, dict) else None

    content = ""
    if isinstance(tool_response, dict):
        # Prefer explicit response.url over input.url — redirects can change it.
        resp_url = tool_response.get("url")
        if isinstance(resp_url, str) and resp_url:
            url = resp_url
        raw_content = tool_response.get("result") or tool_response.get("content")
        if isinstance(raw_content, str):
            content = raw_content
        # HTTP code gate — skip cache for error responses.
        code = tool_response.get("code")
        if isinstance(code, int) and code >= 400:
            return ("", "", "")
    elif isinstance(tool_response, str):
        content = tool_response

    url_s = url if isinstance(url, str) else ""
    query_s = prompt if isinstance(prompt, str) else ""

    if len(content) > _CONTENT_SIZE_CAP:
        content = content[:_CONTENT_SIZE_CAP]

    return (url_s, content, query_s)


def _compile_private_patterns(patterns: list | None) -> list[re.Pattern]:
    if not patterns:
        return []
    out: list[re.Pattern] = []
    for pat in patterns:
        if not isinstance(pat, str):
            continue
        try:
            out.append(re.compile(pat, re.IGNORECASE))
        except re.error:
            continue
    return out


def _is_private_url(url: str, compiled: list[re.Pattern]) -> bool:
    if not url:
        return True  # empty URL is never cacheable
    for p in compiled:
        if p.search(url):
            return True
    return False


def _url_already_fresh(mirror_path: str, url: str, ttl_days: int | None) -> bool:
    """True iff `brain_web_cache` has a row for `url` that is within TTL."""
    try:
        from brain_hook_utils import (
            is_fresh as _is_fresh_util,
            lookup_exact_url as _lookup_util,
        )
    except Exception:  # noqa: BLE001
        return False
    try:
        conn = sqlite3.connect(mirror_path)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return False
    try:
        hit = _lookup_util(conn, url)
    finally:
        conn.close()
    if hit is None:
        return False
    now_epoch = _dt.datetime.now(tz=_dt.timezone.utc).timestamp()
    return _is_fresh_util(hit.get("fetched_at") or "", ttl_days, now_epoch)


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not os.path.exists(os.path.join(project_dir, ".tausik", "tausik.db")):
        return 0

    event = _read_stdin_json()
    tool_name = event.get("tool_name")
    # Only WebFetch — see module docstring for why WebSearch is skipped.
    if tool_name != "WebFetch":
        return 0

    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    tool_response = event.get("tool_response")
    if tool_response is None:
        tool_response = event.get("tool_result")

    try:
        from brain_config import DEFAULT_BRAIN, load_brain
    except Exception:  # noqa: BLE001
        return 0

    try:
        cfg = load_brain()
    except Exception:  # noqa: BLE001
        return 0
    if not cfg.get("enabled"):
        return 0

    token_env = cfg.get("notion_integration_token_env") or ""
    if not token_env or not os.environ.get(token_env):
        _debug("skip: token env unset")
        return 0

    raw_mirror = cfg.get("local_mirror_path") or DEFAULT_BRAIN["local_mirror_path"]
    try:
        mirror_path = os.path.abspath(
            os.path.expandvars(os.path.expanduser(str(raw_mirror)))
        )
    except (TypeError, ValueError):
        return 0
    if not os.path.isfile(mirror_path):
        _debug("skip: mirror missing")
        return 0

    url, content, query = _extract_webfetch(tool_input, tool_response)
    if not url or not content:
        _debug("skip: empty url or content")
        return 0

    compiled = _compile_private_patterns(cfg.get("private_url_patterns"))
    if _is_private_url(url, compiled):
        _debug(f"skip: private url ({url[:80]})")
        return 0

    ttl_days = cfg.get("ttl_web_cache_days")
    if _url_already_fresh(mirror_path, url, ttl_days):
        _debug(f"skip: already fresh ({url[:80]})")
        return 0

    try:
        from brain_runtime import try_brain_write_web_cache
    except Exception:  # noqa: BLE001
        return 0

    ok, reason = try_brain_write_web_cache(url, content, cfg, query=query)
    if not ok:
        # Scrubbing blocks on private-url regex or project_names blocklist are
        # expected — not a bug. Log everything to stderr in debug mode only.
        _debug(f"write failed: {reason}")
    else:
        _debug(f"cached: {url[:80]} -> {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
