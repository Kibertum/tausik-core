"""Rendering for `tausik metrics tokens` — aggregate in, text out.

Split from `service_token_metrics` at the 500-line cap, at the seam that was
already there: everything here turns an aggregate into lines, and nothing in the
aggregator knows those lines exist.

Two refusals live in this file, and they are the point of it. A value that was
not measured prints as absence, never as 0 — a zero asserts a measurement nobody
took (decision #334). And `input_tokens` is never presented as "the input": with
prompt caching it is the uncached remainder, literally 2 on every cached call,
while the context a token-economy claim is about sits in cache_read +
cache_create.
"""

from __future__ import annotations

import json
import os
from typing import Any

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


def _read_ledger_line(project_dir: str) -> list[str]:
    """What the read ledger actually saved, or nothing at all.

    A claim of economy without a counter is forbidden (this task's AC4), and the
    counter belongs where the economy is reported rather than in a log nobody
    opens. Printed only when the ledger exists — the mechanism is opt-in, and a
    permanent "0 saved" line on projects that never enabled it would be noise
    dressed as a measurement.
    """
    path = os.path.join(project_dir, ".tausik", "read_ledger.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    saved = int(data.get("saved_reads") or 0)
    if not saved:
        return []
    return [
        f"READ LEDGER: {saved} re-read(s) of unchanged files refused this session "
        f"({len(data.get('files') or {})} file(s) tracked over "
        f"{int(data.get('calls') or 0)} read call(s)). Tokens NOT saved are not "
        "counted here: what a refused read would have cost is unknown, and "
        "guessing it would be the same invention this report exists to stop."
    ]


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
    lines.extend(_read_ledger_line(os.getcwd()))
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
