#!/usr/bin/env python3
"""PreToolUse hook: check shared-brain web_cache before WebSearch/WebFetch.

If the brain mirror holds a fresh hit (fetched_at within ttl_web_cache_days)
matching the query/URL, block the outgoing network call and surface the
cached snippet. This avoids re-fetching pages the user (or team) has already
paid for and stored.

Bypass: if the last user turn contains the marker `refresh: web_cache`,
the hook allows the network fetch (escape hatch for stale/wrong cache).

Exit codes: 0 = allow, 2 = block.
Skipped via TAUSIK_SKIP_HOOKS=1. Silently no-ops when brain is disabled
or the mirror DB is missing.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sqlite3
import sys

_HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.dirname(_HOOK_DIR)
if _HOOK_DIR not in sys.path:
    sys.path.insert(0, _HOOK_DIR)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from _common import last_user_prompt_text, marker_present_anchored  # noqa: E402


_BYPASS_MARKER = "refresh: web_cache"
_WATCHED_TOOLS = ("WebSearch", "WebFetch")


# Claude Code hook payloads are small JSON dicts — cap the read to defuse
# a malformed/huge stdin that could otherwise keep the hook alive past
# the subprocess timeout.
_STDIN_SIZE_CAP = 1_048_576  # 1 MiB


def _read_stdin_json() -> dict:
    try:
        raw = sys.stdin.read(_STDIN_SIZE_CAP + 1)
    except (OSError, ValueError):
        return {}
    if len(raw) > _STDIN_SIZE_CAP:
        # Oversized payload — refuse to parse. Hook degrades to allow-all,
        # which is safe: a legitimately large payload would be a different
        # kind of bug.
        return {}
    try:
        data = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _bypass_present(transcript_path: str) -> bool:
    return marker_present_anchored(
        last_user_prompt_text(transcript_path), _BYPASS_MARKER
    )


def _extract_query(tool_name: str, tool_input: dict) -> tuple[str, str]:
    """Return (fts_query, exact_url). Either or both may be empty strings.

    WebSearch's query is the FTS query and there is no URL.
    WebFetch's url is used for an exact lookup; only the prompt feeds FTS —
    folding the URL into the FTS phrase would turn a phrase query that can
    never match existing content into a noisy false-negative.
    """
    if tool_name == "WebSearch":
        q = tool_input.get("query") or ""
        return (q if isinstance(q, str) else "", "")
    if tool_name == "WebFetch":
        url = tool_input.get("url") or ""
        prompt = tool_input.get("prompt") or ""
        url_s = url if isinstance(url, str) else ""
        prompt_s = prompt if isinstance(prompt, str) else ""
        return (prompt_s, url_s)
    return ("", "")


def _parse_iso_to_epoch(s: str) -> float | None:
    """Parse an ISO-8601 timestamp (Notion style) to a UTC epoch seconds float.

    Accepts both '2026-04-24T10:00:00Z' and '2026-04-24T10:00:00.000Z' forms.
    Returns None on any parse failure.
    """
    if not isinstance(s, str) or not s:
        return None
    try:
        txt = s.replace("Z", "+00:00")
        dt = _dt.datetime.fromisoformat(txt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def _lookup_exact_url(conn: sqlite3.Connection, url: str) -> dict | None:
    """Return the freshest web_cache row whose url matches exactly, or None.

    ORDER BY on the raw TEXT fetched_at is lexicographic, which disagrees
    with chronological order when different ISO formats co-exist (e.g.
    '...Z' vs '...000Z'). Fetch all matches and sort in Python by the
    parsed epoch — misparse sorts last (treated as oldest).
    """
    try:
        rows = conn.execute(
            "SELECT notion_page_id, url, fetched_at, name "
            "FROM brain_web_cache WHERE url = ?",
            (url,),
        ).fetchall()
    except sqlite3.Error:
        return None
    if not rows:
        return None

    def _key(r: sqlite3.Row) -> float:
        epoch = _parse_iso_to_epoch(r["fetched_at"] or "")
        return epoch if epoch is not None else float("-inf")

    best = max(rows, key=_key)
    return {
        "notion_page_id": best["notion_page_id"],
        "url": best["url"],
        "fetched_at": best["fetched_at"],
        "name": best["name"],
    }


def _lookup_fts(conn: sqlite3.Connection, query: str) -> dict | None:
    """FTS5 search on web_cache. Returns the top bm25 hit (freshest tiebreak)."""
    try:
        from brain_search import sanitize_fts_query
    except Exception:  # noqa: BLE001
        return None
    safe = sanitize_fts_query(query)
    if not safe:
        return None
    sql = (
        "SELECT t.notion_page_id, t.url, t.fetched_at, t.name, bm25(fts_brain_web_cache) AS _score "
        "FROM fts_brain_web_cache f "
        "JOIN brain_web_cache t ON t.id = f.rowid "
        "WHERE fts_brain_web_cache MATCH ? "
        "ORDER BY _score ASC, t.fetched_at DESC LIMIT 1"
    )
    try:
        row = conn.execute(sql, (safe,)).fetchone()
    except sqlite3.Error:
        # Broader than OperationalError: DatabaseError, IntegrityError etc.
        # If the mirror DB is corrupt or locked mid-read, we fail closed
        # (allow the net fetch) rather than crash the hook.
        return None
    if row is None:
        return None
    return {
        "notion_page_id": row["notion_page_id"],
        "url": row["url"],
        "fetched_at": row["fetched_at"],
        "name": row["name"],
    }


def _is_fresh(fetched_at: str, ttl_days: int | None, now_epoch: float) -> bool:
    """Return True if fetched_at is within ttl_days of now. ttl_days=None means never expire."""
    if ttl_days is None:
        return True
    if not isinstance(ttl_days, int) or ttl_days <= 0:
        return False
    epoch = _parse_iso_to_epoch(fetched_at)
    if epoch is None:
        return False
    return (now_epoch - epoch) <= (ttl_days * 86400)


def _emit_block(hit: dict, query: str, tool_name: str) -> None:
    lines = [
        f"BLOCKED: {tool_name} — shared-brain web_cache has a fresh hit.",
        f"  page: {hit.get('notion_page_id') or '?'}  url: {hit.get('url') or '?'}",
        f"  name: {hit.get('name') or '?'}",
        f"  fetched_at: {hit.get('fetched_at') or '?'}",
        "  Use the cached snippet via `brain_get <page_id>` or `brain_search`.",
        "  To force a network fetch anyway, reply with the marker "
        "`refresh: web_cache` in your next message, then retry.",
    ]
    if query:
        lines.insert(1, f"  query: {query[:120]}")
    print("\n".join(lines), file=sys.stderr)


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not os.path.exists(os.path.join(project_dir, ".tausik", "tausik.db")):
        return 0

    event = _read_stdin_json()
    tool_name = event.get("tool_name")
    if tool_name not in _WATCHED_TOOLS:
        return 0

    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

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

    raw_mirror = cfg.get("local_mirror_path") or DEFAULT_BRAIN["local_mirror_path"]
    try:
        mirror_path = os.path.abspath(
            os.path.expandvars(os.path.expanduser(str(raw_mirror)))
        )
    except (TypeError, ValueError):
        return 0
    if not os.path.isfile(mirror_path):
        return 0

    query, exact_url = _extract_query(tool_name, tool_input)
    if not query and not exact_url:
        return 0

    try:
        conn = sqlite3.connect(mirror_path)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return 0

    try:
        hit: dict | None = None
        if exact_url:
            hit = _lookup_exact_url(conn, exact_url)
        if hit is None and query:
            hit = _lookup_fts(conn, query)
    finally:
        conn.close()

    if hit is None:
        return 0

    ttl_days = cfg.get("ttl_web_cache_days")
    now_epoch = _dt.datetime.now(tz=_dt.timezone.utc).timestamp()
    if not _is_fresh(hit.get("fetched_at") or "", ttl_days, now_epoch):
        return 0

    if _bypass_present(event.get("transcript_path") or ""):
        return 0

    _emit_block(hit, query or exact_url, tool_name)
    return 2


if __name__ == "__main__":
    sys.exit(main())
