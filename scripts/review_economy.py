"""Worked protocol model for legacy versus bounded L3 review.

The call and green-re-review counts follow the declared state machines for one
repair cycle; they are not measured savings. Model latency and tokens remain
unavailable unless a caller supplies measured token telemetry.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from typing import Any


def _legacy_schedule(members: list[str], red: str) -> list[list[str]]:
    """The previous full regression repeats every per-task review after repair."""
    del red
    return [[task] for task in members] + [[task] for task in members]


def _bounded_schedule(members: list[str], red: str) -> list[list[str]]:
    """One full packet, then only the prior red task for this acceptance case."""
    return [members, [red]]


def economy_benchmark(
    sizes: tuple[int, ...] = (1, 2, 5),
    *,
    repeats: int = 10_000,
    token_telemetry: Mapping[int, Mapping[str, int]] | None = None,
) -> list[dict[str, Any]]:
    """Return modeled protocol counts and any caller-supplied token measurements."""
    if repeats < 1:
        raise ValueError("repeats must be positive")
    rows: list[dict[str, Any]] = []
    for size in sizes:
        if size < 1:
            raise ValueError("cohort size must be positive")
        members = [f"task-{index}" for index in range(size)]
        legacy = _legacy_schedule(members, members[0])
        bounded = _bounded_schedule(members, members[0])
        measured = (token_telemetry or {}).get(size, {})
        legacy_tokens = measured.get("legacy")
        bounded_tokens = measured.get("bounded")
        if legacy_tokens is not None and legacy_tokens < 0:
            raise ValueError("legacy token telemetry cannot be negative")
        if bounded_tokens is not None and bounded_tokens < 0:
            raise ValueError("bounded token telemetry cannot be negative")
        rows.append(
            {
                "tasks": size,
                "evidence_kind": "protocol-model",
                "scenario": "one blocking task repaired after round 1",
                "legacy": {
                    "reviewer_invocations": len(legacy),
                    "re_reviewed_green_tasks": max(0, size - 1),
                    "tokens_total": legacy_tokens,
                },
                "bounded": {
                    "reviewer_invocations": len(bounded),
                    "re_reviewed_green_tasks": 0,
                    "tokens_total": bounded_tokens,
                },
            }
        )
    return rows


def format_row(row: dict[str, Any]) -> str:
    """One line with explicit unavailable telemetry."""
    legacy, bounded = row["legacy"], row["bounded"]

    def tokens(value: int | None) -> str:
        return "unavailable" if value is None else str(value)

    return (
        f"{row['tasks']} task(s): legacy calls={legacy['reviewer_invocations']}, "
        f"green re-reviews={legacy['re_reviewed_green_tasks']}, "
        f"tokens={tokens(legacy['tokens_total'])} | "
        f"bounded calls={bounded['reviewer_invocations']}, "
        f"green re-reviews={bounded['re_reviewed_green_tasks']}, "
        f"tokens={tokens(bounded['tokens_total'])}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=10_000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    rows = economy_benchmark(repeats=args.repeats)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print("Worked protocol model, not measured savings; reviewer latency is unavailable.")
        for row in rows:
            print(format_row(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
