#!/usr/bin/env python3
"""Which TAUSIK session a transcript timestamp belongs to.

`token_metrics.jsonl` used to stamp every row with `resolve_session_id()` — the
NEWEST session in the DB — while `extract_token_rows` re-walks the WHOLE
transcript on every SessionEnd. One Claude Code transcript spans several TAUSIK
sessions, so each of them received a copy of the entire transcript. Measured on
this project's own ledger (session #227): 3840 of 5301 rows (72.4%) were
cross-session duplicates, sessions 221/222/223 all began at the same
2026-09-06T16:13:29.282Z, session 223 ran for 25 minutes and carried 1409 rows
spanning 16 hours, and the summed cache_read was inflated exactly 2.03x before
any semantic objection to summing it at all.

A row belongs to the session whose [started_at, ended_at) interval CONTAINS its
timestamp, and to NO session when none does. The second half is not a detail: a
timestamp outside every session yields ABSENCE (None), never the nearest guess
(decision #334). Unattributed rows stay in the ledger and are counted as
unattributed by the report — dropping them would hide the gap instead of
showing it.

Read-only by construction: the DB is opened through a `mode=ro` URI, and every
failure path (missing file, locked, unreadable, malformed timestamps) yields an
empty window list rather than an exception. This runs inside a SessionEnd hook,
and a hook has no right to break the session it is measuring.
"""

from __future__ import annotations

import os
import sqlite3
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path

#: One session's span: (start, end_or_None, session_id). Ends are exclusive so
#: two adjacent sessions cannot both claim the instant they touch at.
Window = tuple[datetime, "datetime | None", int]


def parse_ts(value: object) -> datetime | None:
    """ISO-8601 string -> aware UTC datetime. Anything unparseable -> None.

    Both sides of the comparison arrive in mixed shapes: the DB holds
    `2026-03-14T11:32:22+00:00` for early sessions and `2026-09-07T13:51:40Z`
    for later ones, transcripts hold `2026-09-06T16:40:37.350Z`. Lexicographic
    comparison is WRONG across those: `'…:40Z' > '…:40.350Z'` because `Z` sorts
    after `.`, so a sub-second timestamp would fall on the wrong side of a
    boundary. Parse, then compare. A naive value is read as UTC — every producer
    here writes UTC, and inventing a local offset would move rows across
    session boundaries.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _db_path(project_dir: str | None = None) -> str:
    return os.path.join(project_dir or os.getcwd(), ".tausik", "tausik.db")


def load_session_windows(project_dir: str | None = None) -> list[Window]:
    """Session spans sorted by start, or [] when the DB cannot be read.

    A session with no `ended_at` is still OPEN. Its span is closed at the next
    session's start rather than left running to infinity: an abandoned session
    that was never ended would otherwise claim every later timestamp, which is
    the same "nearest guess" failure this module exists to remove. The newest
    open session keeps an unbounded end, because work happening now genuinely
    belongs to it.
    """
    db = _db_path(project_dir)
    if not os.path.exists(db):
        return []
    try:
        uri = Path(db).absolute().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=2)
    except (sqlite3.Error, ValueError, OSError):
        return []
    try:
        rows = conn.execute("SELECT id, started_at, ended_at FROM sessions").fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    spans: list[Window] = []
    for sid, started, ended in rows:
        start = parse_ts(started)
        if start is None:
            continue  # a session we cannot place in time attributes nothing
        end = parse_ts(ended)
        if end is not None and end < start:
            end = None  # nonsense interval: treat as open, let the next start close it
        try:
            spans.append((start, end, int(sid)))
        except (TypeError, ValueError):
            continue
    spans.sort(key=lambda w: w[0])

    closed: list[Window] = []
    for idx, (start, end, sid) in enumerate(spans):
        if end is None and idx + 1 < len(spans):
            end = spans[idx + 1][0]
        closed.append((start, end, sid))
    return closed


def _locate(moment: datetime, starts: list[datetime], windows: list[Window]) -> int | None:
    """Containing session for an already-parsed instant, or None."""
    idx = bisect_right(starts, moment) - 1
    if idx < 0:
        return None  # earlier than the first session ever recorded
    _start, end, sid = windows[idx]
    if end is not None and moment >= end:
        return None  # in the gap between two sessions
    return sid


def session_for_ts(ts: object, windows: list[Window]) -> int | None:
    """Session containing `ts`, or None — outside every span, or unparseable.

    None is a RESULT, not an error: the ledger keeps the row and the report
    counts it as unattributed. Attribution is by containment only; the nearest
    session is never used as a fallback (decision #334).
    """
    moment = parse_ts(ts)
    if moment is None or not windows:
        return None
    return _locate(moment, [w[0] for w in windows], windows)


def make_session_resolver(project_dir: str | None = None):
    """Callable `ts -> session_id | None`, with the windows loaded once.

    `extract_token_rows` calls this per row over transcripts with thousands of
    entries; re-reading the DB per row would turn a metrics hook into a
    measurable cost of its own.
    """
    windows = load_session_windows(project_dir)
    starts = [w[0] for w in windows]

    def resolve(ts: object) -> int | None:
        moment = parse_ts(ts)
        if moment is None or not windows:
            return None
        return _locate(moment, starts, windows)

    return resolve
