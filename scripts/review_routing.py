"""Executable review routing derived from the residual-assurance decision.

This module is the only place that translates an assurance-policy result into
reviewer work.  It deliberately knows nothing about stack names or file
extensions: those are declarations upstream, never routing shortcuts here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from review_separation import review_model_family


_DEPTH = {"L1": 1, "L2": 2, "L3": 3}
_MIN_REVIEWER_INVOCATIONS = {"L1": 0, "L2": 1, "L3": 1}


def _missing_inputs(assurance: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    if not assurance.get("profiles"):
        missing.append("assurance_profiles")
    impact = assurance.get("impact") or {}
    for field in ("level", "blast_radius", "reversibility"):
        if impact.get(field, "unknown") == "unknown":
            missing.append(f"assurance_impact.{field}")
    return missing


def build_review_route(
    assurance: Mapping[str, Any],
    *,
    explicit_deep: bool = False,
    configured_extreme_floor: bool = False,
    measured_high: bool = False,
) -> dict[str, Any]:
    """Return the host-independent execution contract for one review.

    ``measured_high`` is the closure-time selective escalation.  It can raise a
    route chosen earlier, but never lower the policy decision or its hard floor.
    Deep fan-out is separate from L3 separation of duties and is permitted only
    by an explicit audit request or a configured extreme floor.
    """
    depth = str(assurance.get("depth") or "L2")
    if depth not in _DEPTH:
        depth = "L2"
    reasons = [str(reason) for reason in assurance.get("reasons") or []]
    if measured_high and _DEPTH[depth] < _DEPTH["L3"]:
        depth = "L3"
        reasons.append("measured-high closure escalation requires L3 before close")

    deep = bool(explicit_deep or configured_extreme_floor)
    if deep:
        depth = "L3"
        reasons.append("forced deep audit" if explicit_deep else "configured extreme L3-deep floor")

    if depth == "L1":
        execution = {
            "mode": "checklist-and-gates",
            "reviewer_invocations": 0,
            "reviewer_context": "author",
            "different_model_required": False,
        }
    elif depth == "L2":
        execution = {
            "mode": "focused-review",
            "reviewer_invocations": 1,
            "reviewer_context": "fresh",
            "different_model_required": False,
        }
    elif deep:
        execution = {
            "mode": "multi-agent-deep-audit",
            "reviewer_invocations": 7,
            "reviewer_context": "fresh",
            "different_model_required": True,
        }
    else:
        execution = {
            "mode": "external-review",
            "reviewer_invocations": 1,
            "reviewer_context": "different-model",
            "different_model_required": True,
        }

    return {
        "depth": depth,
        "deep": deep,
        "profiles": list(assurance.get("profiles") or []),
        "reasons": reasons,
        "hard_floor": assurance.get("hard_floor"),
        "required_evidence": list(assurance.get("required_evidence") or []),
        "observed_evidence": list(assurance.get("observed_evidence") or []),
        "residual_gaps": list(assurance.get("residual_gaps") or []),
        "missing_inputs": _missing_inputs(assurance),
        "execution": execution,
    }


def force_deep_route(route: Mapping[str, Any]) -> dict[str, Any]:
    """Return the explicit deep-audit form without recomputing package policy."""
    forced = dict(route)
    forced["depth"] = "L3"
    forced["deep"] = True
    forced["reasons"] = [*list(route.get("reasons") or []), "forced deep audit"]
    forced["execution"] = {
        "mode": "multi-agent-deep-audit",
        "reviewer_invocations": 7,
        "reviewer_context": "fresh",
        "different_model_required": True,
    }
    return forced


def validate_review_record(
    route: Mapping[str, Any],
    *,
    run_type: str,
    author_model: str | None,
    reviewer_model: str | None,
    reviewer_context: str,
    reviewer_invocations: int,
    critical_findings: int = 0,
    high_findings: int = 0,
    verification_passed: bool = True,
    substantive_repair: bool = False,
    post_repair_verification_passed: bool = True,
    reviewer_available: bool = True,
    require_identities: bool = True,
) -> list[str]:
    """Return blockers that make a claimed route unsafe to record/close."""
    errors: list[str] = []
    required_depth = str(route.get("depth") or "L2")
    if run_type not in _DEPTH:
        errors.append("run_type must be L1, L2, or L3")
        return errors
    if _DEPTH[run_type] < _DEPTH.get(required_depth, 2):
        errors.append(f"route requires {required_depth}; {run_type} cannot satisfy it")

    route_expected = int((route.get("execution") or {}).get("reviewer_invocations", 1))
    expected = max(route_expected, _MIN_REVIEWER_INVOCATIONS[run_type])
    if reviewer_invocations != expected:
        errors.append(
            f"route requires {expected} reviewer invocation(s); recorded {reviewer_invocations}"
        )
    if run_type == "L1" and reviewer_invocations:
        errors.append("L1 must use zero reviewer invocations")
    if require_identities and review_model_family(author_model) is None:
        errors.append("review record requires a recognized author model identity")
    if run_type == "L2" and reviewer_context != "fresh":
        errors.append("L2 requires one focused reviewer in a fresh context")
    if require_identities and run_type == "L2" and review_model_family(reviewer_model) is None:
        errors.append("L2 requires a recognized reviewer model identity")
    if run_type == "L3":
        if not reviewer_available:
            errors.append("L3 reviewer is unavailable; the route cannot be downgraded")
        if reviewer_context != "different-model":
            errors.append("L3 requires a different-model reviewer, not separate context alone")
        if review_model_family(author_model) is None or review_model_family(reviewer_model) is None:
            errors.append("L3 requires recognized author and reviewer model identities")
        elif review_model_family(author_model) == review_model_family(reviewer_model):
            errors.append("same-family review cannot be recorded as L3")
    if critical_findings or high_findings:
        errors.append("reviewer HIGH/CRITICAL findings must be repaired before close")
    if not verification_passed:
        errors.append("deterministic verification failed")
    if substantive_repair and not post_repair_verification_passed:
        errors.append("substantive repair requires a fresh passing verification")
    return errors


def route_json(route: Mapping[str, Any]) -> str:
    """Stable JSON representation stored with the review record."""
    return json.dumps(dict(route), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


_REVIEWED_TASK_FIELDS = (
    "title",
    "goal",
    "acceptance_criteria",
    "rollback_plan",
    "scope",
    "scope_exclude",
    "scope_paths",
    "scope_tools",
    "relevant_files",
    "assurance_profiles",
    "assurance_impact",
    "risk_json",
    "complexity",
    "role",
    "stack",
)


def _project_root_for_connection(conn: Any) -> Path:
    db_file = str(conn.execute("PRAGMA database_list").fetchone()[2] or "")
    parent = Path(db_file).resolve().parent
    return parent.parent if parent.name == ".tausik" else parent


def review_state_fingerprint(conn: Any, slug: str, project_root: str | Path | None = None) -> str:
    """Hash the task contract and bytes of every declared review file."""
    row = conn.execute("SELECT * FROM tasks WHERE slug=?", (slug,)).fetchone()
    if row is None:
        raise ValueError(f"task not found: {slug}")
    task = dict(row)
    contract = {key: task.get(key) for key in _REVIEWED_TASK_FIELDS}
    root = Path(project_root).resolve() if project_root else _project_root_for_connection(conn)
    try:
        declared = json.loads(task.get("relevant_files") or "[]")
    except (TypeError, ValueError):
        declared = []
    files: list[dict[str, str]] = []
    for raw in declared if isinstance(declared, list) else []:
        label = str(raw)
        candidate = (root / label).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            files.append({"path": label, "state": "outside-project"})
            continue
        if not candidate.is_file():
            files.append({"path": label, "state": "missing"})
            continue
        files.append({"path": label, "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest()})
    payload = json.dumps(
        {"task": contract, "files": files},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def review_record_blockers(
    conn: Any,
    slug: str,
    route: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> list[str]:
    """Why the latest persisted review cannot satisfy the canonical route."""
    row = conn.execute(
        "SELECT * FROM reviews WHERE task_slug=? ORDER BY id DESC LIMIT 1", (slug,)
    ).fetchone()
    if row is None:
        return [f"{route.get('depth', 'L2')} review record is required"]
    record = dict(row)
    recorded_fingerprint = str(record.get("reviewed_state_fingerprint") or "")
    current_fingerprint = review_state_fingerprint(conn, slug, project_root)
    if not recorded_fingerprint:
        return ["review record predates reviewed-state binding; run a fresh review"]
    if recorded_fingerprint != current_fingerprint:
        return ["review record is stale: task contract or reviewed files changed"]
    stored_route = route
    try:
        decoded = json.loads(record.get("route_json") or "null")
        if isinstance(decoded, dict):
            stored_route = decoded
    except (TypeError, ValueError):
        pass
    blockers = validate_review_record(
        stored_route,
        run_type=str(record.get("run_type") or ""),
        author_model=record.get("author_model"),
        reviewer_model=record.get("reviewer_model"),
        reviewer_context=str(record.get("reviewer_context") or ""),
        reviewer_invocations=int(record.get("reviewer_invocations") or 0),
        critical_findings=int(record.get("critical_findings") or 0),
        high_findings=int(record.get("high_findings") or 0),
    )
    run_type = str(record.get("run_type") or "")
    required_depth = str(route.get("depth") or "L2")
    if run_type in _DEPTH and _DEPTH[run_type] < _DEPTH.get(required_depth, 2):
        blockers.append(f"current route requires {required_depth}; {run_type} cannot satisfy it")
    if route.get("deep") and not stored_route.get("deep"):
        blockers.append("current route requires an L3-deep review record")
    return blockers
