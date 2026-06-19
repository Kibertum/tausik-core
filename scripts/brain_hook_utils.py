"""Shared helpers for brain-integrated hooks (read + write paths).

Both `scripts/hooks/brain_search_proactive.py` (PreToolUse — cache read)
and `scripts/hooks/brain_post_webfetch.py` (PostToolUse — cache write)
need the same pieces:

  - parse Notion-style ISO timestamps into UTC epoch seconds,
  - do an exact-URL lookup against `brain_web_cache`,
  - check freshness against `ttl_web_cache_days`.

Keeping this in a brain-scoped module (not scripts/hooks/_common.py,
which holds generic hook utilities) because everything here is tightly
coupled to the brain_web_cache schema and cfg keys.

Zero external deps. No logging — callers decide how to surface failures.
Connection ownership is the caller's responsibility; these functions
never close or mutate schema.
"""

from __future__ import annotations

import datetime as _dt
import sqlite3


def parse_iso_to_epoch(s: str) -> float | None:
    """Parse an ISO-8601 timestamp (Notion style) to UTC epoch seconds.

    Accepts both '2026-04-24T10:00:00Z' and '2026-04-24T10:00:00.000Z'
    forms. Naive timestamps are assumed to be UTC. Returns None on any
    parse failure — callers treat that as "unknown age" (usually oldest).
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


def lookup_exact_url(conn: sqlite3.Connection, url: str) -> dict | None:
    """Return the freshest `brain_web_cache` row whose URL matches exactly.

    Multiple rows can share a URL (per-project writes) — we fetch all and
    pick the newest in Python. Sorting by the raw TEXT `fetched_at` in
    SQL is lexicographic, which diverges from chronological order when
    different ISO formats co-exist (e.g. trailing `Z` vs `.000Z`).
    Parse each timestamp and compare as epoch seconds; misparse sorts
    last (treated as oldest).

    Returns {notion_page_id, url, fetched_at, name} or None.
    """
    if not url:
        return None
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
        epoch = parse_iso_to_epoch(r["fetched_at"] or "")
        return epoch if epoch is not None else float("-inf")

    best = max(rows, key=_key)
    return {
        "notion_page_id": best["notion_page_id"],
        "url": best["url"],
        "fetched_at": best["fetched_at"],
        "name": best["name"],
    }


def is_fresh(fetched_at: str, ttl_days: int | None, now_epoch: float) -> bool:
    """Return True if `fetched_at` is within `ttl_days` of `now_epoch`.

    ttl_days=None means "never expire" (cache is always fresh).
    ttl_days<=0 or non-int means "always stale" (defensive — config
    validation rejects this, but a manually-edited config could slip
    through and we prefer not to block on garbage).
    """
    if ttl_days is None:
        return True
    if not isinstance(ttl_days, int) or ttl_days <= 0:
        return False
    epoch = parse_iso_to_epoch(fetched_at)
    if epoch is None:
        return False
    return (now_epoch - epoch) <= (ttl_days * 86400)
