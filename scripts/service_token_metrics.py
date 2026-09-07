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


def _attribution_caveat() -> list[str]:
    """The limitation a reader must see BEFORE the numbers, not after them.

    These columns look like per-tool cost and are not. API usage is reported
    per MESSAGE, not per tool call, which the capture hook says of itself
    ("PostToolUse payload carried per-tool API usage. It does not"). What
    survives in the file is a message-level figure stamped onto whichever tool
    happened to run: `in_p50`/`in_p90` come out as the same tiny number for
    every tool, `in_total` is that number times the call count — a call counter
    wearing a cost label — and summing `cache_read` re-counts one cached
    conversation on every call, which is why a single tool can appear to have
    read hundreds of millions of tokens.

    Printing this caveat is the whole fix (decision #201). A table that asserts
    an attribution nobody measured is the same defect as a health check that
    reports a comparison it skipped: the reader cannot tell, so they believe it.
    """
    return [
        "NOTE: these are MESSAGE-level figures stamped onto the tool that ran, not",
        "      per-tool cost. in_* is the UNCACHED REMAINDER of the input, not the",
        "      input: with prompt caching on it is literally 2 tokens per message on",
        "      this project, while the real context sits in cache_r + cache_c. ctx_*",
        "      is that full context (input + cache_create + cache_read) and is the",
        "      quantity a token-economy claim is about. Summed cache_read re-counts one",
        "      cached context per call, so read it as VOLUME OF READS, not as distinct",
        "      tokens. Attributing cost per tool needs a transcript-level parser",
        "      (decision #201).",
    ]


#: What the report prints where a number does not exist. Never 0 — a zero here
#: asserts a measurement that was never taken, which is the failure this
#: instrument was rebuilt to stop making (decision #334).
NOT_MEASURED = "не измерено"
NOT_MEASURED_CELL = "n/a"


def _cell(value: int | None, width: int) -> str:
    """Right-aligned number, or the absence marker — never a stand-in zero."""
    if value is None:
        return f"{NOT_MEASURED_CELL:>{width}}"
    return f"{value:>{width},}"


def _coverage_lines(agg: dict[str, Any]) -> list[str]:
    """How wide the series actually is — the denominator, stated up front.

    "5 session(s) observed" reads as completeness until you learn the project
    has had 227. A longitudinal claim ("it got cheaper") is unverifiable without
    knowing what fraction of the history the ledger covers, so the fraction is
    printed whether or not it flatters the instrument.
    """
    in_db = agg.get("sessions_in_db")
    observed = agg.get("sessions_observed", 0)
    if in_db is None:
        coverage = f"{observed} session(s) with rows; total sessions {NOT_MEASURED} (DB unreadable)"
    elif in_db > 0:
        coverage = (
            f"{observed} of {in_db} session(s) in the DB carry rows "
            f"({100.0 * observed / in_db:.1f}% of the project's history)"
        )
    else:
        coverage = f"{observed} session(s) with rows; DB reports no sessions"
    lines = [f"COVERAGE: {coverage}"]
    span_from = agg.get("earliest_ts")
    span_to = agg.get("latest_ts")
    if span_from and span_to:
        lines.append(f"          rows span {span_from} .. {span_to}")
    else:
        lines.append(f"          row time span {NOT_MEASURED}")
    unattributed = agg.get("unattributed_events", 0)
    if unattributed:
        lines.append(
            f"          {unattributed} row(s) fall outside every session and are "
            "attributed to none (not counted in the window below)"
        )
    return lines


def format_table(agg: dict[str, Any]) -> str:
    """Render aggregate as a fixed-width table for CLI output."""
    if agg["events"] == 0:
        return "\n".join(
            [
                "No token metrics recorded yet — token economy is "
                f"{NOT_MEASURED.upper()}, not zero.",
                "The SessionEnd hook writes .tausik/token_metrics.jsonl after bootstrap "
                "installs it; allow at least one full session.",
                *_coverage_lines(agg),
            ]
        )
    lines: list[str] = []
    lines.append(
        f"Token metrics — last {agg['sessions_in_window']} session(s), {agg['events']} event(s)"
    )
    lines.extend(_coverage_lines(agg))
    lines.extend(_attribution_caveat())
    # 40 columns, not 24: every `mcp__tausik-project__tausik_*` name collapsed
    # to the same `mcp__tausik-project__tau` at 24, so a report whose job is to
    # say WHERE the tokens go could not distinguish twenty of its own tools.
    header = (
        f"{'tool':<40} {'events':>7} {'ctx_p50':>10} {'ctx_total':>13} "
        f"{'in_total':>9} {'out_total':>10} {'cache_r':>12} {'cache_c':>11}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for row in agg["per_tool"]:
        lines.append(
            f"{(row['tool_name'] or '-')[:40]:<40} "
            f"{row['events']:>7} "
            f"{_cell(row['context_tokens_p50'], 10)} "
            f"{_cell(row['context_tokens_total'], 13)} "
            f"{_cell(row['input_tokens_total'], 9)} "
            f"{_cell(row['output_tokens_total'], 10)} "
            f"{_cell(row['cache_read_total'], 12)} "
            f"{_cell(row['cache_create_total'], 11)}"
        )
    t = agg["totals"]
    lines.append("-" * len(header))
    ctx = t.get("context")
    ctx_text = NOT_MEASURED if ctx is None else f"{ctx:,}"
    lines.append(
        f"Totals: context={ctx_text}  input={t['input']:,}  output={t['output']:,}  "
        f"cache_read={t['cache_read']:,}  cache_create={t['cache_create']:,}"
    )
    missing = t.get("context_missing_events", 0)
    if missing:
        lines.append(
            f"        context is {NOT_MEASURED} for {missing} of "
            f"{agg['events']} event(s) — those events contribute nothing to the "
            "context total rather than a zero"
        )
    return "\n".join(lines)
