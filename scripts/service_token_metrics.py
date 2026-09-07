"""TAUSIK token metrics aggregation — read .tausik/token_metrics.jsonl.

Provides per-tool aggregates (median, p50, p90, total) over the last N
distinct sessions. Used by `tausik metrics tokens` CLI to surface baseline
data for v1.4 Phase B Gate A decision (heavy ops > 20% input tokens?).

Robust to partial/corrupt JSONL: skips lines that don't parse, never raises
on bad rows. `aggregate` and `format_table` are read-only; the ONLY path that
writes is `print_cli(rebuild=True)`, which delegates to the writer's
`rebuild_ledger` and prints a receipt of what it rebuilt.

Two things this report refuses to do, both learned from being wrong here
before: it never prints 0 where a value was not measured (decision #334), and
it never presents `input_tokens` as "the input" — with prompt caching that
field is the uncached remainder, literally 2 on every cached call, while the
context that a token-economy claim is about sits in cache_read + cache_create.
"""

from __future__ import annotations

import json
import os
from typing import Any

_JSONL_RELPATH = os.path.join(".tausik", "token_metrics.jsonl")


def _percentile(sorted_values: list[int], pct: float) -> int:
    """Linear-interpolation percentile on a pre-sorted list. Empty → 0."""
    if not sorted_values:
        return 0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = rank - lo
    return int(round(sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac))


def _read_records(jsonl_path: str) -> list[dict[str, Any]]:
    """Stream records from JSONL; silently skip malformed lines."""
    if not os.path.isfile(jsonl_path):
        return []
    records: list[dict[str, Any]] = []
    try:
        with open(jsonl_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(obj, dict):
                    records.append(obj)
    except OSError:
        return []
    return records


def _session_id(record: dict[str, Any]) -> int | None:
    """A record's session id, or None when it has none / it is unusable.

    A row whose timestamp fell outside every session carries `session_id: null`
    on purpose (decision #334). That is a value the report must be able to
    carry, so this never coerces it to a number.
    """
    raw = record.get("session_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _filter_last_n_sessions(records: list[dict[str, Any]], last_n: int) -> list[dict[str, Any]]:
    """Keep only records from the last N distinct session_ids by max session_id.

    Unattributed rows (session_id null) belong to no session and therefore to no
    "last N sessions" window. They are excluded here and counted separately by
    `aggregate` — dropping them silently would turn a measured gap into an
    absence of evidence.
    """
    if last_n <= 0:
        return []
    session_ids = sorted({s for s in (_session_id(r) for r in records) if s is not None})
    if not session_ids:
        return []
    keep = set(session_ids[-last_n:])
    return [r for r in records if _session_id(r) in keep]


def _sessions_in_db(project_dir: str) -> int | None:
    """How many sessions the project has ever had, or None when unknowable.

    The denominator of the coverage claim. Without it "5 session(s) observed"
    reads like completeness; against 227 it reads like a 2% sample, which is
    what it was. None (not 0) when the DB cannot be read: an unmeasurable count
    is reported as unmeasured.
    """
    db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.isfile(db):
        return None
    try:
        import sqlite3
        from pathlib import Path

        conn = sqlite3.connect(Path(db).absolute().as_uri() + "?mode=ro", uri=True, timeout=2)
        try:
            row = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
            return int(row[0]) if row else None
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — a report must not die on an unreadable DB
        return None


def _context(record: dict[str, Any]) -> int | None:
    """A record's full input context, or None when it was not measured.

    Old rows predate the field entirely; new rows carry null when the message's
    usage payload named none of the three input buckets. Both are absence, and
    absence is NOT zero — a zero here would claim a message that read nothing.
    """
    raw = record.get("context_tokens")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def aggregate(
    project_dir: str | None = None,
    last_n: int = 10,
) -> dict[str, Any]:
    """Compute per-tool aggregates over the last N sessions.

    Returns a dict with shape:
      {
        "sessions_observed": int,      # distinct session_ids present in the file
        "sessions_in_db": int | None,  # DENOMINATOR: sessions the project has
                                       # ever had. None when the DB is unreadable
                                       # — unmeasured, not zero.
        "sessions_in_window": int,     # min(last_n, sessions_observed)
        "events": int,                 # records in the window
        "unattributed_events": int,    # rows whose ts fell in no session at all
        "earliest_ts": str | None,     # how far back the series actually goes
        "latest_ts": str | None,
        "per_tool": [
          {
            "tool_name": str,
            "events": int,
            "context_tokens_total": int | None,   # None = never measured
            "context_tokens_p50": int | None,
            "context_measured_events": int,
            "input_tokens_p50": int,
            "input_tokens_p90": int,
            "input_tokens_total": int,
            "output_tokens_total": int,
            "cache_read_total": int,
            "cache_create_total": int,
          },
          ...
        ],
        "totals": {input, output, cache_read, cache_create,
                   context: int | None, context_measured_events,
                   context_missing_events}
      }

    `context` is the quantity a token-economy claim is about (input +
    cache_create + cache_read) and is None — never 0 — when no row in the window
    carried it. Rows sort by context, falling back to call volume for tools
    whose context was never measured.
    """
    proj = project_dir or os.getcwd()
    jsonl_path = os.path.join(proj, _JSONL_RELPATH)
    records = _read_records(jsonl_path)
    coverage: dict[str, Any] = {
        "sessions_in_db": _sessions_in_db(proj),
        "unattributed_events": 0,
        "earliest_ts": None,
        "latest_ts": None,
    }
    if not records:
        return {
            "sessions_observed": 0,
            "sessions_in_window": 0,
            "events": 0,
            "per_tool": [],
            "totals": {
                "input": 0,
                "output": 0,
                "cache_read": 0,
                "cache_create": 0,
                # None, not 0: with no rows at all the context was not measured.
                "context": None,
                "context_measured_events": 0,
                "context_missing_events": 0,
            },
            **coverage,
        }

    sessions_all = {s for s in (_session_id(r) for r in records) if s is not None}
    coverage["unattributed_events"] = sum(1 for r in records if _session_id(r) is None)
    stamps = sorted(str(r.get("ts")) for r in records if r.get("ts"))
    if stamps:
        coverage["earliest_ts"], coverage["latest_ts"] = stamps[0], stamps[-1]
    window = _filter_last_n_sessions(records, last_n)

    by_tool: dict[str, list[dict[str, Any]]] = {}
    totals: dict[str, Any] = {
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "cache_create": 0,
        "context": 0,
        "context_measured_events": 0,
        "context_missing_events": 0,
    }
    for r in window:
        tool = str(r.get("tool_name") or "(unknown)")
        by_tool.setdefault(tool, []).append(r)
        totals["input"] += int(r.get("input_tokens") or 0)
        totals["output"] += int(r.get("output_tokens") or 0)
        totals["cache_read"] += int(r.get("cache_read") or 0)
        totals["cache_create"] += int(r.get("cache_create") or 0)
        ctx = _context(r)
        if ctx is None:
            totals["context_missing_events"] += 1
        else:
            totals["context"] += ctx
            totals["context_measured_events"] += 1
    if totals["context_measured_events"] == 0:
        # Not one row in the window carried a context size. Reporting 0 here
        # would assert "no tokens were read"; the truth is "nobody measured".
        totals["context"] = None

    per_tool: list[dict[str, Any]] = []
    for tool, rows in by_tool.items():
        inputs = sorted(int(x.get("input_tokens") or 0) for x in rows)
        measured = [c for c in (_context(x) for x in rows) if c is not None]
        per_tool.append(
            {
                "tool_name": tool,
                "events": len(rows),
                "input_tokens_p50": _percentile(inputs, 50.0),
                "input_tokens_p90": _percentile(inputs, 90.0),
                "input_tokens_total": sum(inputs),
                "output_tokens_total": sum(int(x.get("output_tokens") or 0) for x in rows),
                "cache_read_total": sum(int(x.get("cache_read") or 0) for x in rows),
                "cache_create_total": sum(int(x.get("cache_create") or 0) for x in rows),
                "context_tokens_total": sum(measured) if measured else None,
                "context_tokens_p50": _percentile(sorted(measured), 50.0) if measured else None,
                "context_measured_events": len(measured),
            }
        )
    # Sort by the quantity a token-economy claim is about — the full context —
    # falling back to call count for tools whose context was never measured.
    per_tool.sort(key=lambda d: (d["context_tokens_total"] or 0, d["events"]), reverse=True)

    return {
        "sessions_observed": len(sessions_all),
        "sessions_in_window": min(last_n, len(sessions_all)),
        "events": len(window),
        "per_tool": per_tool,
        "totals": totals,
        **coverage,
    }


from service_token_metrics_render import (  # noqa: E402
    NOT_MEASURED,
    NOT_MEASURED_CELL,
    format_table,
)

__all__ = [
    "aggregate",
    "format_table",
    "print_cli",
    "NOT_MEASURED",
    "NOT_MEASURED_CELL",
]


def print_cli(last_n: int, as_json: bool, rebuild: bool = False) -> None:
    """Render the `tausik metrics tokens` output to stdout.

    `rebuild` re-derives the ledger from every transcript on disk first. It is
    opt-in because it rewrites a file, and the receipt it prints says what was
    rebuilt — a rebuild that silently found nothing would be indistinguishable
    from one that worked.
    """
    import json as _json

    receipt = None
    if rebuild:
        receipt = _rebuild_ledger()
        if not as_json:
            print(_format_receipt(receipt))
            print()
    agg = aggregate(last_n=last_n)
    if as_json:
        payload = dict(agg)
        if receipt is not None:
            payload["rebuild"] = receipt
        print(_json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_table(agg))


def _rebuild_ledger() -> dict[str, Any]:
    """Call the writer's rebuild, translating an unavailable writer into a receipt."""
    import sys

    hooks = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks")
    if hooks not in sys.path:
        sys.path.insert(0, hooks)
    try:
        from token_rows import rebuild_ledger
    except ImportError as exc:
        return {"error": f"rebuild unavailable: {exc}", "transcripts": 0, "rows": 0}
    receipt: dict[str, Any] = rebuild_ledger()
    return receipt


def _format_receipt(receipt: dict[str, Any]) -> str:
    """One-screen account of a rebuild — including when it produced nothing."""
    if receipt.get("error"):
        return f"REBUILD FAILED: {receipt['error']}"
    lines = [
        f"REBUILD: {receipt['rows']:,} row(s) from {receipt['transcripts']} transcript(s) "
        f"-> {receipt['path']}",
        f"         {receipt['attributed']:,} attributed to {receipt['sessions']} session(s), "
        f"{receipt['unattributed']:,} outside every session",
    ]
    if receipt.get("rows_written", receipt["rows"]) != receipt["rows"]:
        lines.append(
            f"         {receipt['rows_written']:,} written after the size cap trimmed "
            "the oldest rows"
        )
    if receipt.get("context_missing"):
        lines.append(
            f"         context is {NOT_MEASURED} for {receipt['context_missing']:,} row(s)"
        )
    if receipt.get("unreadable"):
        lines.append(f"         unreadable transcript(s): {', '.join(receipt['unreadable'])}")
    return "\n".join(lines)
