"""Atomic validation and persistence for one issued L3 cohort packet."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from review_routing import route_json, validate_review_record


_REQUIRED_RESULT_FIELDS = {
    "task",
    "critical",
    "high",
    "warnings",
    "dependency_map_complete",
}
_OPTIONAL_RESULT_FIELDS = {"notes", "critical_reason", "finding_refs"}


def _count(item: dict[str, Any], key: str) -> int:
    value = item[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 1_000_000:
        raise ValueError(f"{key} must be a non-negative integer")
    return int(value)


def _validated_results(results: Any, expected: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(results, list):
        raise ValueError("results must be a list of task result objects")
    by_slug: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            raise ValueError(f"results[{index}] must be an object")
        slug = item.get("task")
        if not isinstance(slug, str) or not slug:
            raise ValueError(f"results[{index}].task must be a non-empty string")
        missing = sorted(_REQUIRED_RESULT_FIELDS - set(item))
        if missing:
            raise ValueError(f"{slug}: missing result field(s): {', '.join(missing)}")
        unknown = sorted(set(item) - _REQUIRED_RESULT_FIELDS - _OPTIONAL_RESULT_FIELDS)
        if unknown:
            raise ValueError(f"{slug}: unknown result field(s): {', '.join(unknown)}")
        if slug in by_slug:
            raise ValueError(f"duplicate result for task {slug}")
        for key in ("critical", "high", "warnings"):
            _count(item, key)
        if item.get("notes") is not None and not isinstance(item.get("notes"), str):
            raise ValueError(f"{slug}: notes must be a string or null")
        if not isinstance(item["dependency_map_complete"], bool):
            raise ValueError(f"{slug}: dependency_map_complete must be boolean")
        refs = item.get("finding_refs", [])
        if not isinstance(refs, list) or not all(isinstance(ref, str) and ref for ref in refs):
            raise ValueError(f"{slug}: finding_refs must be a list of non-empty strings")
        if _count(item, "critical") and (
            not isinstance(item.get("critical_reason"), str)
            or not item["critical_reason"].strip()
            or not refs
        ):
            raise ValueError(f"{slug}: CRITICAL requires critical_reason and finding_refs")
        by_slug[slug] = item
    if set(by_slug) != set(expected):
        raise ValueError(f"results must cover exactly: {', '.join(expected)}")
    return by_slug


def record_review_round(
    svc: Any,
    cohort_id: int,
    round_number: int,
    results: list[dict[str, Any]],
    *,
    packet_digest: str,
    author_model: str,
    reviewer_model: str,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist one reviewer invocation only for the exact issued packet."""
    from review_cohort import (
        _canonical,
        _cohort,
        _current_contract,
        _latest_results,
        _now,
        _packet,
        _root,
        _round2_members,
        cohort_status,
    )

    if round_number not in (1, 2):
        raise ValueError("automatic review round must be 1 or 2")
    if not isinstance(packet_digest, str) or not packet_digest:
        raise ValueError("packet_digest from the issued review packet is required")
    conn = svc.be._conn
    try:
        with svc.be.transaction():
            cohort = _cohort(svc.be, cohort_id)
            expected_round = int(cohort["current_round"]) + 1
            if round_number != expected_round or round_number > 2:
                raise ValueError(f"expected round {expected_round}; automatic round 3 is forbidden")
            members, routes = _current_contract(svc, cohort)
            if round_number == 1:
                if cohort["state"] != "open":
                    raise ValueError(f"round 1 cannot be recorded from state {cohort['state']}")
                expected = members
                carried: list[str] = []
            else:
                if cohort["state"] != "round1_red":
                    raise ValueError(f"round 2 cannot be recorded from state {cohort['state']}")
                expected, carried = _round2_members(svc, cohort)
            issued_row = conn.execute(
                "SELECT * FROM review_cohort_packets WHERE cohort_pk=? AND round_number=?",
                (cohort_id, round_number),
            ).fetchone()
            if issued_row is None or issued_row["packet_digest"] != packet_digest:
                raise ValueError("review packet is missing, superseded, or has the wrong digest")
            issued = json.loads(issued_row["packet_json"])
            current = _packet(conn, expected, _root(svc), round_number, routes)
            if current["packet_digest"] != packet_digest:
                raise ValueError(
                    "review packet is stale: task, files, dependencies, or lineage changed"
                )
            by_slug = _validated_results(results, expected)
            authors = {item["slug"]: item["author_model"] for item in issued["tasks"]}
            author_label = (
                next(iter(set(authors.values())))
                if len(set(authors.values())) == 1
                else ("mixed:" + ",".join(sorted(set(authors.values()))))
            )
            if author_model != author_label:
                raise ValueError("author_model does not match trusted per-task provenance")
            for slug in expected:
                errors = validate_review_record(
                    routes[slug],
                    run_type="L3",
                    author_model=authors[slug],
                    reviewer_model=reviewer_model,
                    reviewer_context="different-model",
                    reviewer_invocations=1,
                )
                if errors:
                    raise ValueError(f"{slug}: invalid L3 reviewer evidence: " + "; ".join(errors))
            stamp = _now()
            conn.execute(
                "INSERT INTO review_cohort_rounds(cohort_pk,round_number,packet_json,author_model,"
                "reviewer_model,reviewer_context,reviewer_invocations,usage_json,recorded_at) "
                "VALUES(?,?,?,?,?,'different-model',1,?,?)",
                (
                    cohort_id,
                    round_number,
                    _canonical(issued),
                    author_label,
                    reviewer_model,
                    _canonical(usage) if usage else None,
                    stamp,
                ),
            )
            prior = _latest_results(svc.be, cohort_id)
            for slug in expected:
                item = by_slug[slug]
                critical, high, warnings = (
                    _count(item, key) for key in ("critical", "high", "warnings")
                )
                verdict = "red" if critical or high else ("advisory" if warnings else "green")
                conn.execute(
                    "INSERT INTO review_cohort_results(cohort_pk,round_number,task_slug,verdict,"
                    "critical_findings,high_findings,warnings,reviewed_state_fingerprint,route_json,"
                    "carried_forward,supersedes_result_id,notes,author_model,dependency_map_complete,"
                    "critical_reason,finding_refs_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,0,?,?,?,?,?,?,?)",
                    (
                        cohort_id,
                        round_number,
                        slug,
                        verdict,
                        critical,
                        high,
                        warnings,
                        issued["fingerprints"][slug],
                        route_json(routes[slug]),
                        prior.get(slug, {}).get("id"),
                        item.get("notes"),
                        authors[slug],
                        int(item.get("dependency_map_complete", False)),
                        item.get("critical_reason"),
                        _canonical(item.get("finding_refs", [])),
                        stamp,
                    ),
                )
            for slug in carried:
                old = prior[slug]
                conn.execute(
                    "INSERT INTO review_cohort_results(cohort_pk,round_number,task_slug,verdict,"
                    "critical_findings,high_findings,warnings,reviewed_state_fingerprint,route_json,"
                    "carried_forward,supersedes_result_id,notes,author_model,dependency_map_complete,"
                    "critical_reason,finding_refs_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,1,?,?,?,?,?,?,?)",
                    (
                        cohort_id,
                        2,
                        slug,
                        old["verdict"],
                        old["critical_findings"],
                        old["high_findings"],
                        old["warnings"],
                        old["reviewed_state_fingerprint"],
                        old["route_json"],
                        old["id"],
                        "carried forward: unchanged green task",
                        old["author_model"],
                        old["dependency_map_complete"],
                        old["critical_reason"],
                        old["finding_refs_json"],
                        stamp,
                    ),
                )
            has_red = any(
                _count(item, "critical") or _count(item, "high") for item in by_slug.values()
            )
            state = (
                ("round1_red" if has_red else "green")
                if round_number == 1
                else ("owner_decision" if has_red else "green")
            )
            final_packet = _packet(conn, expected, _root(svc), round_number, routes)
            if final_packet["packet_digest"] != packet_digest:
                raise ValueError("review packet changed while results were being recorded")
            changed = conn.execute(
                "UPDATE review_cohorts SET state=?,current_round=?,updated_at=? "
                "WHERE id=? AND current_round=?",
                (state, round_number, stamp, cohort_id, round_number - 1),
            ).rowcount
            if changed != 1:
                raise ValueError("review round was recorded concurrently; reload cohort status")
    except (sqlite3.IntegrityError, sqlite3.OperationalError) as exc:
        raise ValueError(f"review round could not be recorded atomically: {exc}") from exc
    # A red first round is followed by repair, then an explicit status request
    # issues the immutable round-two packet. Returning status with issuance here
    # would snapshot the pre-repair state and make the intended repair stale.
    return cohort_status(svc, cohort_id, issue_packet=state != "round1_red")
