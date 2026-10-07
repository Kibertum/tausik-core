"""Verify-cost baseline: how much of `tausik verify` is re-paying the same lane.

r1112-verification-cohort-contract (AC-1). Run directly:

    .tausik/venv/Scripts/python.exe scripts/verify_baseline.py [--db PATH]

Reports, for cohorts of 1, 2, 3-4 and >=5 tasks (tasks closing in the same story
within a 2h window — the natural shape of a release story):
- verify invocations paid vs the minimum a cohort contract would pay
  (one run per red cycle, green reusable while inputs are unchanged),
- selected vs full-lane fallback reasons (declared_scope_status),
- elapsed wall time paid vs the cohort minimum (the max run per cycle).

Read-only. The savings are UPPER-BOUND honest: they assume every re-run with
an unchanged files_hash was reusable, which is exactly the reuse the cohort
contract must refuse when ANY invalidator fires (AC-5 of the contract).

Counting contract (fixed 1.11.3; the first cut is pinned in tests as the
defect it was): a cohort is one story's runs sliced into windows by a >2h
gap between that story's CONSECUTIVE runs; membership is the SET of distinct
slugs that ran inside the window — a slug re-entering after a gap opens no
duplicate seat, and its earlier runs are paid in their own window only, not
re-attributed to every window that happens to contain it. Sizes 3-4 have
their own bucket; before the fix they matched no bucket and vanished.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import cast, TypedDict
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class _Window(TypedDict):
    """One cohort window: the story it belongs to, its distinct member
    slugs, and the runs paid inside that window (and no other)."""

    story: int
    members: list[str]
    runs: list[dict]


def cohort_baseline(db_path: str) -> dict[str, dict[str, object]]:
    """The numbers behind `verify --task` cost, grouped by cohort size class."""
    from project_backend import SQLiteBackend

    be = SQLiteBackend(db_path)
    try:
        runs = be._q(
            "SELECT v.task_slug, v.exit_code, v.duration_ms, v.declared_scope_status, "
            "v.files_hash, v.ran_at, t.story_id FROM verification_runs v "
            "LEFT JOIN tasks t ON t.slug = v.task_slug "
            "WHERE v.task_slug IS NOT NULL ORDER BY v.ran_at"
        )
    finally:
        be.close()

    # Cohort = one story's runs sliced by >2h gaps between that story's
    # consecutive runs; members = distinct slugs inside the window. The
    # ORDER BY ran_at above is global, so each story's slice arrives in
    # time order without a second sort.
    story_runs: dict[int, list[dict]] = defaultdict(list)
    for r in runs:
        if r["story_id"] is not None:
            story_runs[r["story_id"]].append(r)

    windows: list[_Window] = []
    for story, s_runs in story_runs.items():
        members: set[str] = set()
        w_runs: list[dict] = []
        prev: str | None = None
        for r in s_runs:
            if prev is not None and _hours_between(prev, r["ran_at"]) > 2:
                windows.append({"story": story, "members": sorted(members), "runs": w_runs})
                members, w_runs = set(), []
            members.add(r["task_slug"])
            w_runs.append(r)
            prev = r["ran_at"]
        if w_runs:
            windows.append({"story": story, "members": sorted(members), "runs": w_runs})

    stats: dict[str, dict[str, object]] = {}
    buckets = {
        "cohort-of-1": lambda n: n == 1,
        "cohort-of-2": lambda n: n == 2,
        "cohort-of-3-4": lambda n: 3 <= n <= 4,
        "cohort-of-5+": lambda n: n >= 5,
    }
    for name, match in buckets.items():
        groups = [w for w in windows if match(len(w["members"]))]
        tasks: set[str] = set()
        invocations = durations = 0
        fallbacks: dict[str, int] = defaultdict(int)
        for w in groups:
            tasks.update(w["members"])
            invocations += len(w["runs"])
            durations += sum((r["duration_ms"] or 0) for r in w["runs"])
            for r in w["runs"]:
                fallbacks[r["declared_scope_status"] or "unknown"] += 1
        stats[name] = {
            "cohorts": len(groups),
            "tasks": len(tasks),
            "invocations_paid": invocations,
            "elapsed_ms_paid": durations,
            "fallback_reasons": dict(fallbacks),
        }
    return stats


def _hours_between(a: str, b: str) -> float:
    from datetime import datetime

    ta = datetime.fromisoformat(a.replace("Z", "+00:00"))
    tb = datetime.fromisoformat(b.replace("Z", "+00:00"))
    return abs((tb - ta).total_seconds()) / 3600.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    default_db = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", ".tausik", "tausik.db"
    )
    ap.add_argument("--db", default=os.path.normpath(default_db))
    args = ap.parse_args()
    stats = cohort_baseline(args.db)
    for name, s in stats.items():
        elapsed = cast(int, s["elapsed_ms_paid"])
        print(
            f"{name}: {s['cohorts']} cohort(s), {s['tasks']} task(s), "
            f"{s['invocations_paid']} invocation(s), "
            f"{elapsed / 1000.0:.1f}s elapsed; "
            f"fallback reasons: {s['fallback_reasons'] or '{}'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
