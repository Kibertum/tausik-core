"""L3 review-cost baseline for natural task cohorts.

Run directly:

    .tausik/venv/Scripts/python.exe scripts/review_baseline.py [--db PATH]

The report is read-only.  A natural cohort is one story's L3 records in an
activity session, split after more than two hours of inactivity between
consecutive records.  Standalone tasks form cohorts of one.  The baseline
reports what the database can prove and labels missing telemetry instead of
estimating it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, TypedDict, cast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class _Window(TypedDict):
    key: str
    members: list[str]
    rows: list[dict[str, Any]]


def _hours_between(a: str, b: str) -> float:
    left = datetime.fromisoformat(a.replace("Z", "+00:00"))
    right = datetime.fromisoformat(b.replace("Z", "+00:00"))
    return abs((right - left).total_seconds()) / 3600.0


def _usage(row: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(row.get("usage_json") or "null")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _windows(rows: list[dict[str, Any]]) -> list[_Window]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        story = row.get("story_id")
        key = f"story:{story}" if story is not None else f"task:{row['task_slug']}"
        grouped[key].append(row)

    result: list[_Window] = []
    for key, group in grouped.items():
        members: set[str] = set()
        current: list[dict[str, Any]] = []
        previous: str | None = None
        for row in group:
            if previous is not None and _hours_between(previous, row["run_at"]) > 2:
                result.append({"key": key, "members": sorted(members), "rows": current})
                members, current = set(), []
            members.add(str(row["task_slug"]))
            current.append(row)
            previous = str(row["run_at"])
        if current:
            result.append({"key": key, "members": sorted(members), "rows": current})
    return result


def review_baseline(db_path: str) -> dict[str, dict[str, object]]:
    """Return measured L3 cost grouped by natural cohort size."""
    from project_backend import SQLiteBackend

    backend = SQLiteBackend(db_path)
    try:
        rows = backend._q(
            "SELECT r.id,r.task_slug,r.run_at,r.reviewer_invocations,r.critical_findings,"
            "r.high_findings,r.warnings,r.usage_json,r.reviewed_state_fingerprint,t.story_id "
            "FROM reviews r LEFT JOIN tasks t ON t.slug=r.task_slug WHERE r.run_type='L3' "
            "UNION ALL "
            "SELECT cr.id,cr.task_slug,cr.created_at AS run_at,"
            "CASE WHEN cr.id=(SELECT MIN(first.id) FROM review_cohort_results first "
            "WHERE first.cohort_pk=cr.cohort_pk AND first.round_number=cr.round_number "
            "AND first.carried_forward=0) THEN rr.reviewer_invocations ELSE 0 END,"
            "cr.critical_findings,cr.high_findings,cr.warnings,"
            "CASE WHEN cr.id=(SELECT MIN(first.id) FROM review_cohort_results first "
            "WHERE first.cohort_pk=cr.cohort_pk AND first.round_number=cr.round_number "
            "AND first.carried_forward=0) THEN rr.usage_json ELSE NULL END,"
            "cr.reviewed_state_fingerprint,t.story_id "
            "FROM review_cohort_results cr JOIN review_cohort_rounds rr "
            "ON rr.cohort_pk=cr.cohort_pk AND rr.round_number=cr.round_number "
            "LEFT JOIN tasks t ON t.slug=cr.task_slug WHERE cr.carried_forward=0 "
            "ORDER BY 3,1"
        )
    finally:
        backend.close()

    windows = _windows(rows)
    buckets = {
        "cohort-of-1": lambda n: n == 1,
        "cohort-of-2": lambda n: n == 2,
        "cohort-of-3-4": lambda n: 3 <= n <= 4,
        "cohort-of-5+": lambda n: n >= 5,
    }
    stats: dict[str, dict[str, object]] = {}
    for name, matches in buckets.items():
        selected = [window for window in windows if matches(len(window["members"]))]
        task_slugs: set[str] = set()
        records = invocations = invocation_records = repeated_tasks = repeated_states = 0
        fingerprint_records = 0
        critical = high = warnings = token_records = tokens = cost_records = 0
        cost = 0.0
        for window in selected:
            task_slugs.update(window["members"])
            records += len(window["rows"])
            task_counts = Counter(str(row["task_slug"]) for row in window["rows"])
            repeated_tasks += sum(max(0, count - 1) for count in task_counts.values())
            state_counts = Counter(
                (str(row["task_slug"]), str(row["reviewed_state_fingerprint"]))
                for row in window["rows"]
                if row.get("reviewed_state_fingerprint")
            )
            fingerprint_records += sum(state_counts.values())
            repeated_states += sum(max(0, count - 1) for count in state_counts.values())
            for row in window["rows"]:
                recorded_calls = int(row.get("reviewer_invocations") or 0)
                if recorded_calls > 0:
                    invocation_records += 1
                    invocations += recorded_calls
                critical += int(row.get("critical_findings") or 0)
                high += int(row.get("high_findings") or 0)
                warnings += int(row.get("warnings") or 0)
                usage = _usage(row)
                if isinstance(usage.get("tokens_total"), int):
                    token_records += 1
                    tokens += int(usage["tokens_total"])
                if isinstance(usage.get("cost_usd"), (int, float)):
                    cost_records += 1
                    cost += float(usage["cost_usd"])
        stats[name] = {
            "cohorts": len(selected),
            "tasks": len(task_slugs),
            "task_seats": sum(len(window["members"]) for window in selected),
            "review_records": records,
            "reviewer_invocations_paid": invocations,
            "invocation_records_measured": invocation_records,
            "repeated_task_reviews": repeated_tasks,
            "fingerprint_records_measured": fingerprint_records,
            "repeated_unchanged_state_reviews": repeated_states if fingerprint_records else None,
            "critical_findings": critical,
            "high_findings": high,
            "warnings": warnings,
            "token_records_measured": token_records,
            "tokens_total_measured": tokens,
            "cost_records_measured": cost_records,
            "cost_usd_measured": round(cost, 6),
        }
    return stats


def format_baseline_line(name: str, values: dict[str, object]) -> str:
    """Render one honest CLI line, including every telemetry denominator."""
    measured = cast(int, values["invocation_records_measured"])
    records = cast(int, values["review_records"])
    fingerprint_measured = cast(int, values["fingerprint_records_measured"])
    repeated_state = values["repeated_unchanged_state_reviews"]
    token_measured = cast(int, values["token_records_measured"])
    cost_measured = cast(int, values["cost_records_measured"])
    token_text = str(values["tokens_total_measured"]) if token_measured else "unavailable"
    cost_text = (
        f"{cast(float, values['cost_usd_measured']):.6f}" if cost_measured else "unavailable"
    )
    repeated_state_text = str(repeated_state) if repeated_state is not None else "unavailable"
    return (
        f"{name}: {values['cohorts']} cohort(s), {values['task_seats']} task seat(s), "
        f"{records} review record(s), {values['reviewer_invocations_paid']} measured "
        f"reviewer invocation(s) ({measured}/{records} records), "
        f"{values['repeated_task_reviews']} repeated task review(s), "
        f"{repeated_state_text} repeated unchanged-state review(s) "
        f"({fingerprint_measured}/{records} fingerprinted), "
        f"tokens={token_text} ({token_measured}/{records} records), "
        f"cost_usd={cost_text} ({cost_measured}/{records} records)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_db = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", ".tausik", "tausik.db"
    )
    parser.add_argument("--db", default=os.path.normpath(default_db))
    args = parser.parse_args()
    for name, values in review_baseline(args.db).items():
        print(format_baseline_line(name, values))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
