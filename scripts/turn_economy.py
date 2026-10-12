"""What a finished task costs, counted in TURNS — the unit the billing actually follows.

THE MEASUREMENT THAT MAKES THIS THE RIGHT UNIT. Over 5,964 telemetry rows the input side was
99.5% `cache_read`: 2,876,911,173 tokens against 22,099 of fresh input. The prefix is re-sent
on every call, so one extra CALL costs about 482,000 tokens while shortening the prompt saves
a few hundred. An edit that trims the request and adds a turn loses by roughly a hundred to
one. Cost per REQUEST is therefore the wrong denominator; cost per finished task is the right
one, and this module reports it.

WHAT IT FOUND, and it is not a rounding error: the median closed task went from 6 calls in
April to 31.5 in September, with p90 from 35 to 114. Five times more turns per task over six
months. Meanwhile the whole prose-compression lever is worth about 2% of output, and output
is the small side of the ledger.

WHERE THE TURNS GO: `Bash` is 87.6% of all measured calls and 3.64 of 4.07 billion
`cache_read`. That is the lever — not the length of what the agent writes, but how many
separate shell round-trips it takes to get a task done.

HONEST ABOUT WHAT IT CANNOT SEE. Both halves are local: `call_actual` is recorded per task in
this project's database, and the telemetry sidecar is written by a hook on this machine.
Neither travels. A number that is not there is reported as absent, never as zero.
"""

from __future__ import annotations

import json
import os
import sqlite3
from statistics import median
from typing import Any, Final

#: Measured cost of one call on the input side, in `cache_read` tokens: the prefix is re-sent
#: whole every time, measured over 5,964 rows. It is the price of a TURN, which is why turns
#: are what this module counts.
CACHE_READ_PER_CALL: Final[int] = 482_000

#: Below this many closed tasks a median says more about the sample than about the habit.
MIN_TASKS: Final[int] = 20


def _pct(values: list[int], q: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * q))]


def calls_per_task(db_path: str) -> dict[str, Any]:
    """Turns per finished task, overall and by month. ``{}`` when the database has none."""
    if not os.path.isfile(db_path):
        return {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT completed_at, call_actual FROM tasks "
            "WHERE status='done' AND call_actual IS NOT NULL AND call_actual > 0"
        ).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        conn.close()
    if not rows:
        return {}
    calls = [int(r["call_actual"]) for r in rows]
    by_month: dict[str, list[int]] = {}
    for r in rows:
        stamp = r["completed_at"] or ""
        if len(stamp) >= 7:
            by_month.setdefault(stamp[:7], []).append(int(r["call_actual"]))
    return {
        "tasks": len(calls),
        "median": median(calls),
        "p90": _pct(calls, 0.9),
        "max": max(calls),
        "total": sum(calls),
        "by_month": {
            m: {"tasks": len(v), "median": median(v), "p90": _pct(v, 0.9)}
            for m, v in sorted(by_month.items())
        },
    }


def tool_mix(sidecar: str) -> dict[str, Any]:
    """Which tools the turns go to. ``{}`` when the sidecar is absent or unreadable.

    A truncated tail line is skipped rather than refused: the file is append-only and the
    last line can be half-written while a session runs.
    """
    if not os.path.isfile(sidecar):
        return {}
    calls: dict[str, int] = {}
    reads: dict[str, int] = {}
    total = 0
    with open(sidecar, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            name = str(rec.get("tool_name") or "?")
            calls[name] = calls.get(name, 0) + 1
            reads[name] = reads.get(name, 0) + int(rec.get("cache_read") or 0)
            total += 1
    if not total:
        return {}
    ranked = sorted(calls, key=lambda k: -calls[k])
    return {
        "calls": total,
        "cache_read": sum(reads.values()),
        "tools": [
            {
                "tool": name,
                "calls": calls[name],
                "share": round(100.0 * calls[name] / total, 1),
                "cache_read": reads[name],
            }
            for name in ranked
        ],
    }


def report(db_path: str, sidecar: str) -> dict[str, Any]:
    return {
        "per_task": calls_per_task(db_path),
        "mix": tool_mix(sidecar),
        "price": CACHE_READ_PER_CALL,
    }


def render(rep: dict[str, Any], top: int = 5) -> str:
    """The report. Absence is stated in words, never as a zero somebody could average."""
    per, mix = rep.get("per_task") or {}, rep.get("mix") or {}
    price = rep.get("price") or CACHE_READ_PER_CALL
    lines: list[str] = []
    if not per:
        lines.append(
            "Turns per task: no closed task on this machine records a call count — "
            "absent, not zero. The count is local and does not travel."
        )
    elif per["tasks"] < MIN_TASKS:
        lines.append(
            f"Turns per task: {per['tasks']} closed task(s) with a count — below {MIN_TASKS}, "
            "so a median here would describe the sample rather than the habit."
        )
    else:
        lines.append(
            f"Turns per finished task over {per['tasks']} closures: median {per['median']:.0f}, "
            f"p90 {per['p90']}, max {per['max']}."
        )
        lines.append(
            f"  At {price:,} cache_read tokens per turn that is "
            f"{per['median'] * price / 1e6:.1f}M per median task, "
            f"{per['p90'] * price / 1e6:.1f}M at p90."
        )
        months = list((per.get("by_month") or {}).items())
        if len(months) >= 2:
            first, last = months[0], months[-1]
            lines.append(
                f"  Trend: {first[0]} median {first[1]['median']:.0f} → "
                f"{last[0]} median {last[1]['median']:.0f} "
                f"(p90 {first[1]['p90']} → {last[1]['p90']})."
            )
    if not mix:
        lines.append("Tool mix: no telemetry sidecar on this machine — absent, not zero.")
    else:
        lines.append(f"Where the turns go, over {mix['calls']:,} measured calls:")
        for row in mix["tools"][:top]:
            lines.append(
                f"  {row['tool']:<28} {row['calls']:>6} calls  {row['share']:>5.1f}%  "
                f"cache_read {row['cache_read'] / 1e9:.2f}B"
            )
    lines.append("")
    lines.append(
        "READ IT THIS WAY: one extra turn costs about the whole prefix again, so an edit that "
        "shortens a request and adds a round-trip loses by about a hundred to one. The lever "
        "is fewer, larger turns — not shorter ones."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    p = argparse.ArgumentParser(description="What a finished task costs, counted in turns")
    p.add_argument("--tausik-dir", default=".tausik")
    p.add_argument("--json", action="store_true", dest="as_json")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rep = report(
        os.path.join(args.tausik_dir, "tausik.db"),
        os.path.join(args.tausik_dir, "token_metrics.jsonl"),
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2) if args.as_json else render(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
