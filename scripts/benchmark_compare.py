"""Honest comparison of naturally accumulated TAUSIK project cohorts."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from tausik_utils import utcnow_iso
from benchmark_compare_support import (
    cost_breakdown as _cost_breakdown,
    cost_reason as _cost_reason,
    parse_rate_card as _parse_rate_card,
    persist_snapshot,
    measured_reviewer_invocations,
    render_comparison,
    task_cost as _task_cost,
)

__all__ = ["compare_cohorts", "persist_snapshot", "render_comparison"]

_IDENTITY = (
    "tausik_version",
    "host",
    "host_version",
    "provider",
    "model",
    "reasoning_effort",
    "speed_mode",
)
_TOKEN_COLUMNS = {
    "input": "tokens_input",
    "cached_input": "tokens_cached_input",
    "output": "tokens_output",
    "reasoning_output": "tokens_reasoning_output",
}
_DISTRIBUTIONS = (
    "response_rounds",
    "tool_calls",
    "active_duration_ms",
    "attempts",
    "retries",
    "input",
    "cached_input",
    "uncached_input",
    "output",
    "reasoning_output",
    "total_tokens",
)


def compare_cohorts(
    conn: sqlite3.Connection,
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    config: Mapping[str, Any] | None = None,
    minimum_sample: int = 5,
    maturation_days: int = 30,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Compare two selectors without inventing missing measurements or causality."""
    if minimum_sample < 1 or maturation_days < 0:
        raise ValueError("minimum_sample must be positive and maturation_days non-negative")
    generated_at = generated_at or utcnow_iso()
    tasks, source_coverage = _natural_tasks(conn, generated_at, maturation_days)
    selected = {
        "left": _select(tasks, _selector(left, "left")),
        "right": _select(tasks, _selector(right, "right")),
    }
    card = _parse_rate_card(config or {}, generated_at)
    cohorts = {side: _summarize(rows, card, minimum_sample) for side, rows in selected.items()}
    reasons: list[str] = []
    for side, cohort in cohorts.items():
        if cohort["sample_size"] < minimum_sample:
            reasons.append(f"{side}-below-minimum-sample")
        if not cohort["identity_homogeneous"]:
            reasons.append(f"{side}-mixed-version-or-model-settings")
        elif not cohort["identity_complete"]:
            reasons.append(f"{side}-incomplete-identity")
    reasons.extend(_comparability_reasons(cohorts["left"], cohorts["right"] or {}))
    task_mix_warnings = _task_mix_warnings(cohorts["left"], cohorts["right"])
    query = {
        "left": _selector(left, "left"),
        "right": _selector(right, "right"),
        "minimum_sample": minimum_sample,
        "maturation_days": maturation_days,
    }
    result = {
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "inconclusive" if reasons else "comparable",
        "reasons": sorted(set(reasons)),
        "claim_boundary": "observational comparison; no version or model causality inferred",
        "query": query,
        "source_coverage": source_coverage,
        "rate_card": card["public"],
        "subscription": {
            "credits": None,
            "included_quota": None,
            "note": "separate from API-equivalent USD; not attributable from project evidence",
        },
        "cohorts": cohorts,
        "task_mix_warnings": task_mix_warnings,
        "membership_hashes": {side: _membership_hash(rows) for side, rows in selected.items()},
    }
    return result


def _natural_tasks(
    conn: sqlite3.Connection, generated_at: str, maturation_days: int
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    conn.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in conn.execute(
            """SELECT b.*, t.status, t.resolution, t.attempts, t.complexity,
                      t.assurance_profiles, t.assurance_impact, t.completed_at
               FROM benchmark_observations b
               JOIN tasks t ON t.slug=b.task_slug
               WHERE b.attribution_confidence='exact'
                 AND t.status='done' AND t.resolution IS NULL
               ORDER BY b.observed_at,b.id"""
        )
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["task_slug"])].append(row)
    verification = _rows_by_task(conn, "verification_runs", "id")
    reviews = _rows_by_task(conn, "reviews", "id")
    defects = defaultdict(list)
    for row in conn.execute(
        "SELECT slug,defect_of,status,resolution,created_at FROM tasks WHERE defect_of IS NOT NULL"
    ):
        defects[str(row["defect_of"])].append(dict(row))
    result = []
    for slug, task_rows in grouped.items():
        identities = {tuple(row.get(key) for key in _IDENTITY) for row in task_rows}
        first = task_rows[0]
        item: dict[str, Any] = {
            "slug": slug,
            "identities": identities,
            "identity": dict(zip(_IDENTITY, next(iter(identities)), strict=True))
            if len(identities) == 1
            else None,
            "observed_at": [row.get("observed_at") for row in task_rows if row.get("observed_at")],
            "completed_at": first.get("completed_at"),
            "complexity": first.get("complexity") or "unknown",
            "assurance_profiles": _json_list(first.get("assurance_profiles")),
            "assurance_impact": _impact_label(first.get("assurance_impact")),
            "response_rounds": sum(int(row.get("response_rounds") or 0) for row in task_rows),
            "attempts": int(first["attempts"]) if first.get("attempts") else None,
        }
        item["retries"] = item["attempts"] - 1 if item["attempts"] is not None else None
        for name, column in _TOKEN_COLUMNS.items():
            item[name] = _complete_sum(task_rows, column)
        item["uncached_input"] = _uncached(item.get("input"), item.get("cached_input"))
        item["total_tokens"] = (
            item["input"] + item["output"]
            if item.get("input") is not None and item.get("output") is not None
            else None
        )
        item["tool_calls"] = _complete_sum(task_rows, "tool_calls")
        if item["tool_calls"] is None:
            item["tool_calls"] = _task_tool_calls(conn, slug)
        item["active_duration_ms"] = _complete_sum(task_rows, "active_duration_ms")
        item["quality"] = _quality(
            verification.get(slug, []),
            reviews.get(slug, []),
            defects.get(slug, []),
            first.get("completed_at"),
            generated_at,
            maturation_days,
        )
        result.append(item)
    return result, {
        "accepted_observations": len(rows),
        "accepted_tasks": len(result),
        "mixed_identity_tasks": sum(len(row["identities"]) != 1 for row in result),
    }


def _select(tasks: list[dict[str, Any]], selector: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for task in tasks:
        identity = task.get("identity") or {}
        if any(
            selector.get(key) is not None and identity.get(key) != selector[key]
            for key in _IDENTITY
        ):
            continue
        dates = task.get("observed_at") or []
        parsed_dates = [_date(str(value)) for value in dates]
        if selector.get("since") and (
            not parsed_dates or max(parsed_dates) < _date(str(selector["since"]))
        ):
            continue
        if selector.get("until") and (
            not parsed_dates or min(parsed_dates) > _date(str(selector["until"]))
        ):
            continue
        result.append(task)
    return result


def _summarize(
    tasks: list[dict[str, Any]], card: Mapping[str, Any], minimum_sample: int
) -> dict[str, Any]:
    identities = {
        tuple((task.get("identity") or {}).get(key) for key in _IDENTITY) for task in tasks
    }
    homogeneous = (
        bool(tasks) and all(len(task["identities"]) == 1 for task in tasks) and len(identities) == 1
    )
    complete = homogeneous and all(next(iter(identities), ()))
    identity = dict(zip(_IDENTITY, next(iter(identities)), strict=True)) if homogeneous else None
    metrics = {name: _distribution([task.get(name) for task in tasks]) for name in _DISTRIBUTIONS}
    costs = [_task_cost(task, card) for task in tasks]
    known_costs = [cost["total"] for cost in costs if cost["total"] is not None]
    cost_total = sum(known_costs) if len(known_costs) == len(tasks) and tasks else None
    strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        key = json.dumps(
            {
                "complexity": task["complexity"],
                "profiles": task["assurance_profiles"],
                "impact": task["assurance_impact"],
            },
            sort_keys=True,
        )
        strata[key].append(task)
    return {
        "sample_size": len(tasks),
        "minimum_sample": minimum_sample,
        "identity_homogeneous": homogeneous,
        "identity_complete": complete,
        "identity": identity,
        "tasks": [task["slug"] for task in tasks],
        "metrics": metrics,
        "api_equivalent_usd": {
            "total": round(cost_total, 6) if cost_total is not None else None,
            "coverage": {"known": len(known_costs), "total": len(tasks)},
            "status": card["status"] if cost_total is not None else _cost_reason(costs, card),
            "breakdown": _cost_breakdown(costs, len(tasks)),
        },
        "quality": _quality_summary(tasks),
        "task_mix": {
            "complexity": dict(sorted(Counter(task["complexity"] for task in tasks).items())),
            "assurance_profiles": dict(
                sorted(
                    Counter(
                        profile for task in tasks for profile in task["assurance_profiles"]
                    ).items()
                )
            ),
            "assurance_impact": dict(
                sorted(Counter(task["assurance_impact"] for task in tasks).items())
            ),
        },
        "strata": [
            {
                **json.loads(key),
                "sample_size": len(rows),
                "metrics": {
                    name: _distribution([row.get(name) for row in rows]) for name in _DISTRIBUTIONS
                },
            }
            for key, rows in sorted(strata.items())
        ],
    }


def _quality_summary(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    qualities = [task["quality"] for task in tasks]
    runs = sum(item["verification_runs"] for item in qualities)
    failed = sum(item["verification_failed_runs"] for item in qualities)
    mix = Counter(level for item in qualities for level in item["review_levels"])
    mature = [item for item in qualities if item["defect_mature"]]
    invocations = [item["reviewer_invocations"] for item in qualities]
    return {
        "verification_failure_rate": round(failed / runs, 6) if runs else None,
        "verification_retry_rate": round(
            sum(max(item["verification_runs"] - 1, 0) for item in qualities) / runs, 6
        )
        if runs
        else None,
        "review_mix": {level: mix.get(level, 0) for level in ("L1", "L2", "L3", "deep")},
        "reviewer_invocations": sum(invocations)
        if all(v is not None for v in invocations)
        else None,
        "confirmed_findings": sum(item["confirmed_findings"] for item in qualities)
        if qualities and all(item["confirmed_findings"] is not None for item in qualities)
        else None,
        "downstream_defect_escapes": sum(item["defect_escapes"] for item in mature)
        if mature
        else None,
        "defect_maturation": {"mature": len(mature), "total": len(tasks)},
    }


def _quality(
    verification: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    defects: list[dict[str, Any]],
    completed_at: str | None,
    generated_at: str,
    maturation_days: int,
) -> dict[str, Any]:
    levels = [str(row["run_type"]) for row in reviews if row.get("run_type")]
    if any(_route_deep(row.get("route_json")) for row in reviews):
        levels.append("deep")
    mature = _mature(completed_at, generated_at, maturation_days)
    return {
        "verification_runs": len(verification),
        "verification_failed_runs": sum(int(row.get("exit_code", 1)) != 0 for row in verification),
        "review_levels": levels,
        "reviewer_invocations": measured_reviewer_invocations(reviews),
        "confirmed_findings": sum(
            int(row.get("critical_findings") or 0) + int(row.get("high_findings") or 0)
            for row in reviews
        )
        if reviews
        else None,
        "defect_mature": mature,
        "defect_escapes": sum(row.get("resolution") is None for row in defects) if mature else None,
    }


def _selector(raw: Mapping[str, Any], fallback_label: str) -> dict[str, Any]:
    allowed = set(_IDENTITY) | {"since", "until", "label"}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"Unknown cohort selector field(s): {', '.join(sorted(unknown))}")
    result = {key: raw.get(key) for key in allowed if raw.get(key) is not None}
    result["label"] = str(result.get("label") or fallback_label)
    return result


def _comparability_reasons(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[str]:
    if (
        not left.get("identity_homogeneous")
        or not right.get("identity_homogeneous")
        or not left.get("identity_complete")
        or not right.get("identity_complete")
    ):
        return []
    one, two = left["identity"], right["identity"]
    changed = {key for key in _IDENTITY if one.get(key) != two.get(key)}
    if not changed:
        return []
    if changed == {"tausik_version"} or changed == {"model"}:
        return []
    return ["multiple-identity-dimensions-changed"]


def _task_mix_warnings(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[str]:
    warnings = []
    for key in ("complexity", "assurance_profiles", "assurance_impact"):
        if left["task_mix"][key] != right["task_mix"][key]:
            warnings.append(
                f"{key} distribution differs; use strata before interpreting pooled values"
            )
    return warnings


def _distribution(values: list[Any]) -> dict[str, Any]:
    known = sorted(float(value) for value in values if value is not None)
    return {
        "median": _number(median(known)) if known else None,
        "p90": _number(known[max(0, math.ceil(0.9 * len(known)) - 1)]) if known else None,
        "coverage": {"known": len(known), "total": len(values)},
    }


def _membership_hash(tasks: list[dict[str, Any]]) -> str:
    wire = json.dumps(sorted(task["slug"] for task in tasks), separators=(",", ":"))
    return hashlib.sha256(wire.encode()).hexdigest()


def _rows_by_task(
    conn: sqlite3.Connection, table: str, order: str
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cursor = conn.execute(f"SELECT * FROM {table} ORDER BY {order}")
    names = [item[0] for item in cursor.description]
    for row in cursor.fetchall():
        item = dict(zip(names, row, strict=True))
        if item.get("task_slug"):
            result[str(item["task_slug"])].append(item)
    return result


def _complete_sum(rows: list[dict[str, Any]], key: str) -> int | None:
    values = [row.get(key) for row in rows]
    if not values or any(value is None for value in values):
        return None
    total = 0
    for value in values:
        assert value is not None
        total += int(value)
    return total


def _task_tool_calls(conn: sqlite3.Connection, slug: str) -> int | None:
    row = conn.execute(
        """SELECT SUM(CASE WHEN source='posttool' THEN 1 ELSE 0 END),
                  SUM(CASE WHEN source<>'session_record' THEN tool_calls ELSE 0 END),
                  COUNT(*)
           FROM usage_events WHERE task_slug=?""",
        (slug,),
    ).fetchone()
    if not row or not int(row[2] or 0):
        return None
    if int(row[0] or 0):
        return int(row[0])
    return int(row[1]) if row[1] is not None and int(row[1]) > 0 else None


def _uncached(total: Any, cached: Any) -> int | None:
    if total is None or cached is None or int(cached) > int(total):
        return None
    return int(total) - int(cached)


def _json_list(raw: Any) -> list[str]:
    try:
        value = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        return []
    return sorted(str(item) for item in value) if isinstance(value, list) else []


def _impact_label(raw: Any) -> str:
    try:
        value = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return "unknown"
    if not isinstance(value, Mapping):
        return "unknown"
    return str(value.get("level") or value.get("blast_radius") or "unknown")


def _route_deep(raw: Any) -> bool:
    try:
        value = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return False
    return bool(value.get("deep")) if isinstance(value, Mapping) else False


def _mature(completed_at: str | None, generated_at: str, days: int) -> bool:
    try:
        return _date(generated_at) >= _date(str(completed_at)) + timedelta(days=days)
    except (TypeError, ValueError):
        return False


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _number(value: float) -> int | float:
    return int(value) if value.is_integer() else round(value, 6)
