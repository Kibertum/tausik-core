from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from benchmark_cohort_render import render_inventory  # noqa: F401 -- public re-export
from benchmark_compare_support import measured_reviewer_invocations
from tausik_utils import utcnow_iso

_IDENTITY = ("host", "host_version", "provider", "model", "reasoning", "speed")
_IDENTITY_COLUMNS = (
    "host",
    "host_version",
    "provider",
    "model",
    "reasoning_effort",
    "speed_mode",
)
_COUNTERS = ("input", "cached_input", "cache_write", "output", "reasoning_output")


def _source_key(row: Mapping[str, Any]) -> str | None:
    """Return an opaque stable response key, or None when it cannot be deduplicated."""
    identity = row.get("identity") or {}
    source = row.get("source") or {}
    parts = [
        (identity.get("host") or {}).get("value"),
        source.get("project"),
        source.get("thread"),
        source.get("response"),
    ]
    if not parts[0] or not parts[2] or not parts[3]:
        return None
    wire = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(wire.encode()).hexdigest()


def _task_version(conn: sqlite3.Connection, slug: str | None) -> str | None:
    if not slug:
        return None
    row = conn.execute(
        "SELECT started_tausik_version,done_tausik_version FROM tasks WHERE slug=?", (slug,)
    ).fetchone()
    if not row or not row[0] or not row[1] or row[0] != row[1]:
        return None
    return str(row[0])


def _task_exists(conn: sqlite3.Connection, slug: str | None) -> bool:
    return bool(slug and conn.execute("SELECT 1 FROM tasks WHERE slug=?", (slug,)).fetchone())


def capture_observations(conn: sqlite3.Connection, rows: Iterable[Mapping[str, Any]]) -> dict:
    """Persist allowlisted response evidence; never persist transcript bodies.

    Matching start/done boundaries prove one version covered the accepted work
    window. Missing or different boundaries remain unclassified. Native sources
    may finalize a response after its first import, so the stable source key is
    updated explicitly while byte-equivalent repeats remain idempotent.
    """
    inserted = updated = repeated = unkeyed = 0
    for row in rows:
        key = _source_key(row)
        if key is None:
            unkeyed += 1
            continue
        identity = row.get("identity") or {}
        source = row.get("source") or {}
        tokens = row.get("tokens") or {}
        attribution = row.get("attribution") or "unknown"
        task_slug = source.get("task") if attribution == "exact" else None
        if task_slug and not _task_exists(conn, task_slug):
            task_slug = None
            attribution = "project"
        values = [
            key,
            task_slug,
            _task_version(conn, task_slug),
            source.get("timestamp"),
            *[(identity.get(name) or {}).get("value") for name in _IDENTITY],
            *[(identity.get(name) or {}).get("basis") for name in _IDENTITY],
            attribution,
            1,
            *[tokens.get(name) for name in _COUNTERS],
            row.get("tool_calls"),
            row.get("active_duration_ms"),
            row.get("format") or "unknown",
            utcnow_iso(),
        ]
        comparable_columns = (
            "task_slug,tausik_version,observed_at,host,host_version,provider,model,"
            "reasoning_effort,speed_mode,host_basis,host_version_basis,provider_basis,"
            "model_basis,reasoning_effort_basis,speed_mode_basis,attribution_confidence,"
            "response_rounds,tokens_input,tokens_cached_input,tokens_cache_write,"
            "tokens_output,tokens_reasoning_output,tool_calls,active_duration_ms,source_format"
        )
        previous = conn.execute(
            f"SELECT {comparable_columns} FROM benchmark_observations WHERE source_key=?",
            (key,),
        ).fetchone()
        if previous is not None and tuple(previous) == tuple(values[1:-1]):
            repeated += 1
            continue
        conn.execute(
            """INSERT INTO benchmark_observations(
                source_key, task_slug, tausik_version, observed_at,
                host, host_version, provider, model, reasoning_effort, speed_mode,
                host_basis, host_version_basis, provider_basis, model_basis,
                reasoning_effort_basis, speed_mode_basis,
                attribution_confidence, response_rounds,
                tokens_input, tokens_cached_input, tokens_cache_write,
                tokens_output, tokens_reasoning_output, tool_calls,
                active_duration_ms, source_format, recorded_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source_key) DO UPDATE SET
                task_slug=excluded.task_slug,
                tausik_version=excluded.tausik_version,
                observed_at=excluded.observed_at,
                host=excluded.host,
                host_version=excluded.host_version,
                provider=excluded.provider,
                model=excluded.model,
                reasoning_effort=excluded.reasoning_effort,
                speed_mode=excluded.speed_mode,
                host_basis=excluded.host_basis,
                host_version_basis=excluded.host_version_basis,
                provider_basis=excluded.provider_basis,
                model_basis=excluded.model_basis,
                reasoning_effort_basis=excluded.reasoning_effort_basis,
                speed_mode_basis=excluded.speed_mode_basis,
                attribution_confidence=excluded.attribution_confidence,
                response_rounds=excluded.response_rounds,
                tokens_input=excluded.tokens_input,
                tokens_cached_input=excluded.tokens_cached_input,
                tokens_cache_write=excluded.tokens_cache_write,
                tokens_output=excluded.tokens_output,
                tokens_reasoning_output=excluded.tokens_reasoning_output,
                tool_calls=excluded.tool_calls,
                active_duration_ms=excluded.active_duration_ms,
                source_format=excluded.source_format,
                recorded_at=excluded.recorded_at""",
            values,
        )
        if previous is None:
            inserted += 1
        else:
            updated += 1
    return {"inserted": inserted, "updated": updated, "repeated": repeated, "unkeyed": unkeyed}


def capture_for_project(project: Path, rows: Iterable[Mapping[str, Any]]) -> dict:
    """Best-effort local capture used by native host readers."""
    db = project / ".tausik" / "tausik.db"
    if not db.is_file():
        return {"inserted": 0, "updated": 0, "repeated": 0, "unkeyed": 0, "available": False}
    try:
        with sqlite3.connect(db, timeout=5) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='benchmark_observations'"
            ).fetchone()
            if not exists:
                return {
                    "inserted": 0,
                    "updated": 0,
                    "repeated": 0,
                    "unkeyed": 0,
                    "available": False,
                }
            result = capture_observations(conn, rows)
        result["available"] = True
        return result
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return {"inserted": 0, "updated": 0, "repeated": 0, "unkeyed": 0, "available": False}


def _latest_by_task(conn: sqlite3.Connection, table: str, order: str) -> dict[str, dict]:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if not columns:
        return {}
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()
    names = [item[0] for item in conn.execute(f"SELECT * FROM {table} LIMIT 0").description]
    result = {}
    for row in rows:
        item = dict(zip(names, row, strict=True))
        slug = item.get("task_slug")
        if slug:
            result[str(slug)] = item
    return result


def _all_by_task(conn: sqlite3.Connection, table: str, order: str) -> dict[str, list[dict]]:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if not columns:
        return {}
    cursor = conn.execute(f"SELECT * FROM {table} ORDER BY {order}")
    names = [item[0] for item in cursor.description]
    result: dict[str, list[dict]] = defaultdict(list)
    for row in cursor.fetchall():
        item = dict(zip(names, row, strict=True))
        if item.get("task_slug"):
            result[str(item["task_slug"])].append(item)
    return result


def _complete_sum(rows: list[dict], key: str) -> int | None:
    return _complete_values([row.get(key) for row in rows])


def _complete_values(values: list[Any]) -> int | None:
    if not values or any(value is None for value in values):
        return None
    total = 0
    for value in values:
        total += int(value)
    return total


def _task_tool_calls(conn: sqlite3.Connection, slug: str) -> int | None:
    row = conn.execute(
        """SELECT
            SUM(CASE WHEN source='posttool' THEN 1 ELSE 0 END),
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


def cohort_inventory(conn: sqlite3.Connection) -> dict:
    """Project accepted work by observed version and model configuration."""
    conn.row_factory = sqlite3.Row
    observations = [
        dict(row)
        for row in conn.execute(
            """SELECT b.*, t.status, t.resolution, t.attempts, t.started_at, t.completed_at
               FROM benchmark_observations b
               LEFT JOIN tasks t ON t.slug=b.task_slug
               ORDER BY b.observed_at, b.id"""
        )
    ]
    accepted = [
        row
        for row in observations
        if row["attribution_confidence"] == "exact"
        and row["task_slug"]
        and row["status"] == "done"
        and row["resolution"] is None
    ]
    verification = _latest_by_task(conn, "verification_runs", "id")
    all_verifications = _all_by_task(conn, "verification_runs", "id")
    all_reviews = _all_by_task(conn, "reviews", "id")
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    identity_keys = (
        "tausik_version",
        "host",
        "host_version",
        "provider",
        "model",
        "reasoning_effort",
        "speed_mode",
    )
    basis_keys = tuple(f"{column}_basis" for column in _IDENTITY_COLUMNS)
    keys = identity_keys + basis_keys
    for row in accepted:
        grouped[tuple(row[key] for key in keys)].append(row)
    task_identities: dict[str, set[tuple]] = defaultdict(set)
    for row in accepted:
        task_identities[str(row["task_slug"])].add(tuple(row[key] for key in keys))
    mixed_tasks = {slug for slug, identities in task_identities.items() if len(identities) > 1}
    cohorts = []
    counter_columns = {
        "input": "tokens_input",
        "cached_input": "tokens_cached_input",
        "cache_write": "tokens_cache_write",
        "output": "tokens_output",
        "reasoning_output": "tokens_reasoning_output",
        "tool_calls": "tool_calls",
        "active_duration_ms": "active_duration_ms",
    }
    for identity, rows in sorted(
        grouped.items(), key=lambda item: tuple(str(v or "") for v in item[0])
    ):
        tasks = sorted({str(row["task_slug"]) for row in rows})
        attributable_tasks = [slug for slug in tasks if slug not in mixed_tasks]
        review_rows = [row for slug in attributable_tasks for row in all_reviews.get(slug, [])]
        review_tasks = {slug for slug in attributable_tasks if all_reviews.get(slug)}
        latest_verifications = [
            verification[slug] for slug in attributable_tasks if slug in verification
        ]
        verification_rows = [
            row for slug in attributable_tasks for row in all_verifications.get(slug, [])
        ]
        coverage: dict[str, dict[str, Any]] = {
            name: {"known": sum(row[column] is not None for row in rows), "total": len(rows)}
            for name, column in counter_columns.items()
        }
        totals = {name: _complete_sum(rows, column) for name, column in counter_columns.items()}
        attempts: dict[str, int | None] = {}
        for slug in attributable_tasks:
            raw = next(row["attempts"] for row in rows if row["task_slug"] == slug)
            attempts[slug] = int(raw) if raw is not None and int(raw) >= 1 else None
        single_identity = len(attributable_tasks) == len(tasks)
        if totals["tool_calls"] is None and single_identity:
            calls = [_task_tool_calls(conn, slug) for slug in tasks]
            totals["tool_calls"] = _complete_values(calls)
            coverage["tool_calls"] = {
                "known": sum(value is not None for value in calls),
                "total": len(calls),
                "basis": "task usage_events",
            }
        verification_outcomes = [row.get("exit_code") for row in latest_verifications]
        attempt_values = list(attempts.values())
        attempts_total = _complete_values(attempt_values)
        retries_total = attempts_total - len(attempt_values) if attempts_total is not None else None
        identity_values = dict(zip(identity_keys, identity[: len(identity_keys)], strict=True))
        identity_basis = dict(zip(_IDENTITY_COLUMNS, identity[len(identity_keys) :], strict=True))
        review_invocation_known_tasks = {
            slug
            for slug in review_tasks
            if all(
                row.get("route_json") and row.get("reviewer_invocations") is not None
                for row in all_reviews[slug]
            )
        }
        reviewer_invocations = (
            measured_reviewer_invocations(review_rows)
            if len(review_tasks) == len(attributable_tasks)
            else None
        )
        cohorts.append(
            {
                "identity": identity_values,
                "identity_basis": identity_basis,
                "classification": (
                    "classified" if all(identity_values.values()) else "legacy/unclassified"
                ),
                "first_observed_at": min(
                    (row["observed_at"] for row in rows if row["observed_at"]), default=None
                ),
                "last_observed_at": max(
                    (row["observed_at"] for row in rows if row["observed_at"]), default=None
                ),
                "sample_size": len(tasks),
                "tasks": tasks,
                "response_rounds": sum(int(row["response_rounds"] or 0) for row in rows),
                "attempts": attempts_total,
                "retries": retries_total,
                "attempt_coverage": {
                    "known": sum(value is not None for value in attempt_values),
                    "total": len(tasks),
                },
                "task_evidence_attribution": {
                    "cohort": len(attributable_tasks),
                    "unsplit": len(tasks) - len(attributable_tasks),
                },
                "totals": totals,
                "coverage": coverage,
                "quality": {
                    "verified_tasks": len(
                        {
                            str(row["task_slug"])
                            for row in latest_verifications
                            if row.get("exit_code") is not None and int(row["exit_code"]) == 0
                        }
                    ),
                    "reviewed_tasks": len(review_tasks),
                    "review_levels": sorted(
                        {str(row.get("run_type")) for row in review_rows if row.get("run_type")}
                    ),
                    "reviewer_invocations": reviewer_invocations,
                    "review_invocation_coverage": {
                        "known": len(review_invocation_known_tasks),
                        "total": len(attributable_tasks),
                    },
                    "verification": {
                        "passed": sum(value == 0 for value in verification_outcomes),
                        "failed": sum(
                            value is not None and value != 0 for value in verification_outcomes
                        ),
                        "unknown": len(attributable_tasks) - len(verification_outcomes),
                        "runs": len(verification_rows),
                        "failed_runs": sum(
                            row.get("exit_code") is not None and int(row["exit_code"]) != 0
                            for row in verification_rows
                        ),
                        "duration_ms": _complete_sum(verification_rows, "duration_ms"),
                    },
                },
            }
        )
    unattributed = [
        row
        for row in observations
        if row["attribution_confidence"] != "exact" or not row["task_slug"]
    ]
    unaccepted = [
        row
        for row in observations
        if row["attribution_confidence"] == "exact" and row["task_slug"] and row not in accepted
    ]
    exact_count = sum(row["attribution_confidence"] == "exact" for row in observations)
    accepted_total = int(
        conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='done' AND resolution IS NULL"
        ).fetchone()[0]
    )
    mixed_attempts = {}
    for slug in sorted(mixed_tasks):
        raw = next(row["attempts"] for row in accepted if row["task_slug"] == slug)
        mixed_attempts[slug] = int(raw) if raw is not None and int(raw) >= 1 else None
    mixed_attempt_values = list(mixed_attempts.values())
    mixed_review_rows = [row for slug in mixed_tasks for row in all_reviews.get(slug, [])]
    mixed_review_values = [
        row.get("reviewer_invocations") if row.get("route_json") else None
        for row in mixed_review_rows
    ]
    mixed_review_tasks = {str(row["task_slug"]) for row in mixed_review_rows}
    mixed_review_known_tasks = {
        slug
        for slug in mixed_review_tasks
        if all(row.get("route_json") for row in all_reviews.get(slug, []))
    }
    mixed_verification_rows = [
        row for slug in mixed_tasks for row in all_verifications.get(slug, [])
    ]
    mixed_attempts_total = _complete_values(mixed_attempt_values)
    return {
        "schema_version": 1,
        "cohorts": cohorts,
        "coverage": {
            "observations": len(observations),
            "exact_attribution": exact_count,
            "accepted_observations": len(accepted),
            "accepted_tasks": len({row["task_slug"] for row in accepted}),
            "accepted_tasks_total": accepted_total,
            "unobserved_accepted_tasks": accepted_total
            - len({row["task_slug"] for row in accepted}),
        },
        "unattributed": {
            "observations": len(unattributed),
            "tokens": {
                name: _complete_sum(unattributed, column)
                for name, column in counter_columns.items()
                if name not in {"tool_calls", "active_duration_ms"}
            },
        },
        "unaccepted": {"observations": len(unaccepted)},
        "unsplit_task_evidence": {
            "tasks": sorted(mixed_tasks),
            "attempts": mixed_attempts_total,
            "retries": (
                mixed_attempts_total - len(mixed_attempt_values)
                if mixed_attempts_total is not None
                else None
            ),
            "reviewer_invocations": (
                measured_reviewer_invocations(mixed_review_rows)
                if mixed_review_values and mixed_review_tasks == mixed_tasks
                else None
            ),
            "review_invocation_coverage": {
                "known": len(mixed_review_known_tasks),
                "total": len(mixed_tasks),
            },
            "review_levels": sorted(
                {str(row["run_type"]) for row in mixed_review_rows if row.get("run_type")}
            ),
            "verification_runs": len(mixed_verification_rows),
            "verification_failed_runs": sum(
                row.get("exit_code") is not None and int(row["exit_code"]) != 0
                for row in mixed_verification_rows
            ),
            "verification_duration_ms": _complete_sum(mixed_verification_rows, "duration_ms"),
        },
        "privacy": "allowlisted counters and opaque source hashes only; no prompt or response bodies",
    }
