"""Owner dispositions and closure consumption for bounded L3 cohorts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from review_routing import validate_review_record


def decide_review_cohort(
    svc: Any,
    cohort_id: int,
    action: str,
    *,
    owner: str,
    reason: str,
    finding_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Apply the single owner transition after terminal automatic round two."""
    from review_cohort import _canonical, _cohort, _latest_results, _now, cohort_status

    if action not in ("accept-risk", "manual-review", "repair-open"):
        raise ValueError("action must be accept-risk, manual-review, or repair-open")
    if not owner.strip() or not reason.strip():
        raise ValueError("owner identity and reason are required")
    state = {
        "accept-risk": "accepted_risk",
        "manual-review": "awaiting_manual_review",
        "repair-open": "repair_open",
    }[action]
    try:
        with svc.be.transaction():
            cohort = _cohort(svc.be, cohort_id)
            if cohort["state"] != "owner_decision":
                raise ValueError("owner action is available only after a red round 2")
            latest = _latest_results(svc.be, cohort_id)
            routes = json.loads(cohort["routes_json"])
            red = [row for row in latest.values() if row["verdict"] == "red"]
            policy_result = "closure remains blocked"
            if action == "accept-risk":
                if not finding_refs:
                    raise ValueError("risk acceptance requires at least one finding reference")
                nonwaivable = [
                    row["task_slug"]
                    for row in red
                    if int(row["critical_findings"]) > 0
                    or routes[row["task_slug"]].get("hard_floor")
                ]
                if nonwaivable:
                    raise ValueError(
                        "risk acceptance refused for CRITICAL/hard-floor tasks: "
                        + ", ".join(nonwaivable)
                    )
                policy_result = "HIGH risk accepted by owner; closure allowed"
            stamp = _now()
            transition = svc.be._conn.execute(
                "UPDATE review_cohorts SET state=?, owner_identity=?, owner_reason=?, "
                "finding_refs_json=?, policy_result=?, updated_at=? "
                "WHERE id=? AND state='owner_decision'",
                (
                    state,
                    owner,
                    reason,
                    _canonical(finding_refs or []),
                    policy_result,
                    stamp,
                    cohort_id,
                ),
            )
            if transition.rowcount != 1:
                raise ValueError("owner disposition was decided concurrently")
            if action == "accept-risk":
                svc.be._conn.execute(
                    "UPDATE review_cohort_results SET verdict='accepted_risk' "
                    "WHERE cohort_pk=? AND round_number=2 AND verdict='red'",
                    (cohort_id,),
                )
    except sqlite3.OperationalError as exc:
        if not any(marker in str(exc).lower() for marker in ("locked", "busy")):
            raise
        raise ValueError("owner disposition is busy; retry after the concurrent decision") from exc
    return cohort_status(svc, cohort_id)


def cohort_review_blockers(
    conn: Any,
    slug: str,
    project_root: str | Path | None = None,
    current_route: Mapping[str, Any] | None = None,
) -> list[str] | None:
    """Return None when no cohort evidence exists, otherwise its close blockers."""
    from review_cohort import _digest, _round_fingerprint

    row = conn.execute(
        "SELECT r.*, c.state AS cohort_state FROM review_cohort_results r "
        "JOIN review_cohorts c ON c.id=r.cohort_pk WHERE r.task_slug=? "
        "ORDER BY r.id DESC LIMIT 1",
        (slug,),
    ).fetchone()
    if row is None:
        return None
    result = dict(row)
    if result["cohort_state"] not in ("green", "accepted_risk"):
        return [f"L3 cohort is {result['cohort_state']}; closure needs green or accepted risk"]
    stored_route = json.loads(result["route_json"])
    if current_route is not None and _digest(stored_route) != _digest(dict(current_route)):
        return ["L3 cohort receipt is stale: review route or policy changed"]
    current = _round_fingerprint(conn, slug, Path(project_root) if project_root else Path.cwd())
    if result["reviewed_state_fingerprint"] != current:
        return [
            "L3 cohort receipt is stale: task contract, reviewed files, or dependencies changed"
        ]
    if result["verdict"] not in ("green", "advisory", "accepted_risk"):
        return ["L3 cohort has unresolved HIGH/CRITICAL findings"]
    evidence = result
    if result["carried_forward"]:
        source = conn.execute(
            "SELECT * FROM review_cohort_results WHERE id=?",
            (result["supersedes_result_id"],),
        ).fetchone()
        if source is None:
            return ["carried L3 result has no superseded source evidence"]
        evidence = dict(source)
    round_row = conn.execute(
        "SELECT * FROM review_cohort_rounds WHERE cohort_pk=? AND round_number=?",
        (evidence["cohort_pk"], evidence["round_number"]),
    ).fetchone()
    if round_row is None:
        return ["L3 cohort result has no reviewer round evidence"]
    return validate_review_record(
        json.loads(evidence["route_json"]),
        run_type="L3",
        author_model=evidence.get("author_model") or round_row["author_model"],
        reviewer_model=round_row["reviewer_model"],
        reviewer_context=round_row["reviewer_context"],
        reviewer_invocations=int(round_row["reviewer_invocations"]),
    )
