"""Deterministic, bounded context for one task.

Required task intent is never shortened to meet the byte target. Optional
relevant-memory lines are admitted whole until the target is reached; omitted
lines and required-field overflow are explicit.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

DEFAULT_MAX_BYTES = 8_192
MIN_MAX_BYTES = 512
MAX_MAX_BYTES = 65_536

_FINGERPRINT_FIELDS = (
    "slug",
    "status",
    "goal",
    "acceptance_criteria",
    "scope",
    "scope_exclude",
    "scope_paths",
    "relevant_files",
    "risk_json",
    "assurance_profiles",
    "assurance_impact",
    "plan",
    "updated_at",
)


def _json_bytes(value: Any) -> int:
    return len(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )


def _set_exact_size(package: dict[str, Any]) -> None:
    """Set the serialized byte count, including the count field itself."""
    size = 0
    while package.get("bytes") != size:
        package["bytes"] = size
        size = _json_bytes(package)


def _decoded(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value.strip():
        return fallback
    try:
        return json.loads(value)
    except ValueError:
        return value


def _active_decisions(svc: Any, slug: str) -> list[dict[str, Any]]:
    try:
        from decision_lifecycle import listing

        rows = listing(svc, n=100, status="active", task=slug)
    except Exception:  # noqa: BLE001 — task context must survive optional knowledge failure
        return []
    return [
        {
            "id": row.get("id"),
            "decision": row.get("decision"),
            "rationale": row.get("rationale"),
            "rejected": row.get("rejected") or "",
        }
        for row in rows
    ]


def _fingerprint(task: dict[str, Any], decisions: list[dict[str, Any]]) -> str:
    source = {field: task.get(field) for field in _FINGERPRINT_FIELDS}
    source["decisions"] = decisions
    encoded = json.dumps(source, ensure_ascii=False, sort_keys=True, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _assurance_projection(svc: Any, task: dict[str, Any]) -> dict[str, Any]:
    """Evaluate declarations against capabilities from the latest signed receipt."""
    from assurance_policy import (
        compose_declarations,
        evaluate_assurance,
        observed_capabilities,
    )
    from stack_registry import registry_for_project

    stack = task.get("stack")
    declaration = (
        registry_for_project(svc.tausik_dir()).assurance_for(stack)
        if stack
        else {
            "profiles": [],
            "impact": {},
            "gate_capabilities": {},
        }
    )
    profiles, impact, complete = compose_declarations(
        declaration["profiles"],
        _decoded(task.get("assurance_profiles"), []),
        declaration["impact"],
        _decoded(task.get("assurance_impact"), {}),
    )
    gate_results: list[dict[str, Any]] = []
    try:
        row = svc.be._q1(
            "SELECT receipt_json FROM verification_runs "
            "WHERE task_slug=? AND receipt_json IS NOT NULL ORDER BY id DESC LIMIT 1",
            (task["slug"],),
        )
        envelope = json.loads(row["receipt_json"]) if row else {}
        receipt = envelope.get("receipt", envelope)
        if receipt.get("passed"):
            gate_results = list(receipt.get("gates") or [])
    except (AttributeError, KeyError, TypeError, ValueError):
        gate_results = []
    observed = observed_capabilities(declaration["gate_capabilities"], gate_results)
    return evaluate_assurance(
        profiles=profiles,
        impact=impact,
        observed_evidence=observed,
        metadata_complete=complete,
    )


def _review_route(svc: Any, task: dict[str, Any], assurance: dict[str, Any]) -> dict[str, Any]:
    """Preview the same route consumed by CLI, MCP and host skills."""
    from review_routing import build_review_route

    measured_high = False
    try:
        from risk_l3_trigger import MIN_MEASURED_WEIGHT, measured_score, measured_weight
        from risk_model import LEVEL_HIGH

        risk = _decoded(task.get("risk_json"), None)
        measured_high = bool(
            risk
            and measured_weight(risk) >= MIN_MEASURED_WEIGHT
            and (measured_score(risk) or 0) >= LEVEL_HIGH
        )
    except (ImportError, TypeError, ValueError):
        measured_high = False

    configured_extreme_floor = False
    try:
        from project_config import load_config

        review_cfg = load_config(svc.tausik_dir()).get("review", {})
        configured_extreme_floor = bool(
            isinstance(review_cfg, dict)
            and review_cfg.get("extreme_hard_floor")
            and assurance.get("hard_floor") == "L3"
        )
    except (AttributeError, TypeError, ValueError):
        configured_extreme_floor = False
    return build_review_route(
        assurance,
        configured_extreme_floor=configured_extreme_floor,
        measured_high=measured_high,
    )


def build_task_context_package(
    svc: Any,
    slug: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    """Return the current task contract plus bounded optional retrieval context."""
    if type(max_bytes) is not int or not MIN_MAX_BYTES <= max_bytes <= MAX_MAX_BYTES:
        raise ValueError(f"max_bytes must be {MIN_MAX_BYTES}..{MAX_MAX_BYTES}")
    task = svc.task_show(slug)
    decisions = _active_decisions(svc, slug)
    assurance = _assurance_projection(svc, task)
    review_route = _review_route(svc, task, assurance)
    required = {
        "slug": task["slug"],
        "title": task.get("title"),
        "status": task.get("status"),
        "complexity": task.get("complexity"),
        "goal": task.get("goal"),
        "acceptance_criteria": task.get("acceptance_criteria"),
        "scope": task.get("scope"),
        "scope_exclude": task.get("scope_exclude"),
        "scope_paths": _decoded(task.get("scope_paths"), []),
        "relevant_files": _decoded(task.get("relevant_files"), []),
        "plan": _decoded(task.get("plan"), []),
        "decisions": decisions,
        "unresolved_risks": {
            "status": task.get("status"),
            "blocked_at": task.get("blocked_at"),
            "risk_score": task.get("risk_score"),
            "risk": _decoded(task.get("risk_json"), None),
        },
        "assurance": assurance,
        "review_route": review_route,
        "verification": {
            "verify": f".tausik/tausik verify --task {slug}",
            "close_with_verify": f".tausik/tausik task done {slug} --ac-verified --verify",
        },
    }
    package: dict[str, Any] = {
        "schema_version": 1,
        "fingerprint": _fingerprint(task, decisions),
        "source_updated_at": task.get("updated_at"),
        "max_bytes": max_bytes,
        "required": required,
        "relevant_memory": [],
        "overflow": False,
        "omitted": [],
    }
    required_bytes = _json_bytes(package)
    if required_bytes > max_bytes:
        package["overflow"] = True
        package["omitted"] = ["relevant_memory"]
        package["overflow_reason"] = "required_fields_exceed_budget"
        _set_exact_size(package)
        return package

    memory = list(task.get("relevant_memory") or [])
    for index, line in enumerate(memory):
        candidate = dict(package)
        candidate["relevant_memory"] = [*package["relevant_memory"], str(line)]
        _set_exact_size(candidate)
        if _json_bytes(candidate) > max_bytes:
            package["overflow"] = True
            package["omitted"] = [f"relevant_memory[{index}:]"]
            break
        package["relevant_memory"].append(str(line))
    _set_exact_size(package)
    return package


def serialize_task_context_package(svc: Any, slug: str, *, max_bytes: int) -> str:
    return json.dumps(
        build_task_context_package(svc, slug, max_bytes=max_bytes),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
