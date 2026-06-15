"""TAUSIK token metrics aggregation — read .tausik/token_metrics.jsonl.

Provides per-tool aggregates (median, p50, p90, total) over the last N
distinct sessions. Used by `tausik metrics tokens` CLI to surface baseline
data for v1.4 Phase B Gate A decision (heavy ops > 20% input tokens?).

Robust to partial/corrupt JSONL: skips lines that don't parse, never raises
on bad rows. Read-only — never modifies the JSONL.
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


def _filter_last_n_sessions(records: list[dict[str, Any]], last_n: int) -> list[dict[str, Any]]:
    """Keep only records from the last N distinct session_ids by max session_id."""
    if last_n <= 0:
        return []
    session_ids = sorted({int(r["session_id"]) for r in records if "session_id" in r})
    if not session_ids:
        return []
    keep = set(session_ids[-last_n:])
    return [r for r in records if int(r.get("session_id", -1)) in keep]


def aggregate(
    project_dir: str | None = None,
    last_n: int = 10,
) -> dict[str, Any]:
    """Compute per-tool aggregates over the last N sessions.

    Returns a dict with shape:
      {
        "sessions_observed": int,         # distinct session_ids present
        "sessions_in_window": int,        # min(last_n, sessions_observed)
        "events": int,                    # total records in window
        "per_tool": [
          {
            "tool_name": str,
            "events": int,
            "input_tokens_p50": int,
            "input_tokens_p90": int,
            "input_tokens_total": int,
            "output_tokens_total": int,
            "cache_read_total": int,
            "cache_create_total": int,
          },
          ...
        ],
        "totals": {input, output, cache_read, cache_create}
      }
    """
    proj = project_dir or os.getcwd()
    jsonl_path = os.path.join(proj, _JSONL_RELPATH)
    records = _read_records(jsonl_path)
    if not records:
        return {
            "sessions_observed": 0,
            "sessions_in_window": 0,
            "events": 0,
            "per_tool": [],
            "totals": {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0},
        }

    sessions_all = {int(r["session_id"]) for r in records if "session_id" in r}
    window = _filter_last_n_sessions(records, last_n)

    by_tool: dict[str, list[dict[str, Any]]] = {}
    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0}
    for r in window:
        tool = str(r.get("tool_name") or "(unknown)")
        by_tool.setdefault(tool, []).append(r)
        totals["input"] += int(r.get("input_tokens") or 0)
        totals["output"] += int(r.get("output_tokens") or 0)
        totals["cache_read"] += int(r.get("cache_read") or 0)
        totals["cache_create"] += int(r.get("cache_create") or 0)

    per_tool: list[dict[str, Any]] = []
    for tool, rows in by_tool.items():
        inputs = sorted(int(x.get("input_tokens") or 0) for x in rows)
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
            }
        )
    per_tool.sort(key=lambda d: d["input_tokens_total"], reverse=True)

    return {
        "sessions_observed": len(sessions_all),
        "sessions_in_window": min(last_n, len(sessions_all)),
        "events": len(window),
        "per_tool": per_tool,
        "totals": totals,
    }


def print_cli(last_n: int, as_json: bool) -> None:
    """Render the `tausik metrics tokens` output to stdout."""
    import json as _json

    agg = aggregate(last_n=last_n)
    if as_json:
        print(_json.dumps(agg, ensure_ascii=False, indent=2))
    else:
        print(format_table(agg))


def format_table(agg: dict[str, Any]) -> str:
    """Render aggregate as a fixed-width table for CLI output."""
    if agg["events"] == 0:
        return (
            "No token metrics recorded yet. The PostToolUse hook starts capturing "
            "after bootstrap installs it; allow at least one full session to "
            "populate .tausik/token_metrics.jsonl."
        )
    lines: list[str] = []
    lines.append(
        f"Token metrics — last {agg['sessions_in_window']} session(s), "
        f"{agg['events']} event(s) ({agg['sessions_observed']} session(s) observed total)"
    )
    header = (
        f"{'tool':<24} {'events':>7} {'in_p50':>9} {'in_p90':>9} "
        f"{'in_total':>11} {'out_total':>11} {'cache_r':>10} {'cache_c':>10}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for row in agg["per_tool"]:
        lines.append(
            f"{(row['tool_name'] or '-')[:24]:<24} "
            f"{row['events']:>7} "
            f"{row['input_tokens_p50']:>9,} "
            f"{row['input_tokens_p90']:>9,} "
            f"{row['input_tokens_total']:>11,} "
            f"{row['output_tokens_total']:>11,} "
            f"{row['cache_read_total']:>10,} "
            f"{row['cache_create_total']:>10,}"
        )
    t = agg["totals"]
    lines.append("-" * len(header))
    lines.append(
        f"Totals: input={t['input']:,}  output={t['output']:,}  "
        f"cache_read={t['cache_read']:,}  cache_create={t['cache_create']:,}"
    )
    return "\n".join(lines)
