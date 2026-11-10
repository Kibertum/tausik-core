"""Canonical, self-contained task package used by start/resume and leases."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from tausik_utils import ServiceError, utcnow_iso

DEFAULT_MAX_BYTES = 16_384
MIN_MAX_BYTES = 512
MAX_MAX_BYTES = 65_536
MEMORY_CONTENT_MAX_BYTES = 256

_CONTRACT_FIELDS = (
    "slug",
    "title",
    "stack",
    "complexity",
    "goal",
    "acceptance_criteria",
    "scope",
    "scope_exclude",
    "scope_paths",
    "scope_tools",
    "relevant_files",
    "risk_json",
    "assurance_profiles",
    "assurance_impact",
    "plan",
    "rollback_plan",
    "call_budget",
)


class TaskPackageError(ServiceError):
    """Stable refusal raised before activation when a package cannot be trusted."""

    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


def _json_bytes(value: Any) -> int:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return len(raw.encode("utf-8"))


def _set_exact_size(package: dict[str, Any]) -> None:
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


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _active_decisions(svc: Any, slug: str) -> list[dict[str, Any]]:
    try:
        from decision_lifecycle import listing

        rows = listing(svc, n=svc.be.decision_count_for_task(slug), status="active", task=slug)
    except Exception as exc:
        raise TaskPackageError("DECISION_UNAVAILABLE", str(exc)) from exc
    return [
        {
            "id": row.get("id"),
            "decision": row.get("decision"),
            "rationale": row.get("rationale"),
            "rejected": row.get("rejected") or "",
        }
        for row in rows
    ]


def task_contract_revision(task: dict[str, Any], decisions: list[dict[str, Any]]) -> str:
    source = {field: task.get(field) for field in _CONTRACT_FIELDS}
    source["decisions"] = decisions
    return _hash(source)


def _truncate_utf8(text: str, limit: int) -> tuple[str, bool]:
    raw = text.encode("utf-8")
    if len(raw) <= limit:
        return text, False
    return raw[:limit].decode("utf-8", errors="ignore"), True


def _memory_source(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "slug": row.get("slug"),
        "type": row.get("type"),
        "title": row.get("title"),
        "content": row.get("content") or "",
        "tags": _decoded(row.get("tags"), []),
        "provenance": row.get("provenance"),
        "updated_at": row.get("updated_at"),
        "archived_at": row.get("archived_at"),
    }


def _memory_payload(row: dict[str, Any]) -> dict[str, Any]:
    source = _memory_source(row)
    content = str(source["content"])
    inline, truncated = _truncate_utf8(content, MEMORY_CONTENT_MAX_BYTES)
    return {
        "id": source["id"],
        "slug": source["slug"],
        "type": source["type"],
        "title": source["title"],
        "content": inline,
        "content_truncated": truncated,
        "content_bytes": len(content.encode("utf-8")),
        "tags": source["tags"],
        "provenance": source["provenance"],
        "revision": source["updated_at"],
        "source_hash": _hash(source),
    }


def _selected_memory(
    svc: Any, task: dict[str, Any], decisions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    from memory_relevance import relevant_memory

    relevance = relevant_memory(svc.be, task, decisions)
    if relevance.error:
        raise TaskPackageError("MEMORY_UNAVAILABLE", relevance.error)
    return [_memory_payload(row) for row in relevance.entries]


def _assurance_projection(svc: Any, task: dict[str, Any]) -> dict[str, Any]:
    from assurance_policy import compose_declarations, evaluate_assurance, observed_capabilities
    from stack_registry import registry_for_project

    stack = task.get("stack")
    declaration = (
        registry_for_project(svc.tausik_dir()).assurance_for(stack)
        if stack
        else {"profiles": [], "impact": {}, "gate_capabilities": {}}
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
            "SELECT receipt_json FROM verification_runs WHERE task_slug=? "
            "AND receipt_json IS NOT NULL ORDER BY id DESC LIMIT 1",
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
        profiles=profiles, impact=impact, observed_evidence=observed, metadata_complete=complete
    )


def _review_route(svc: Any, task: dict[str, Any], assurance: dict[str, Any]) -> dict[str, Any]:
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

        cfg = load_config(svc.tausik_dir()).get("review", {})
        configured_extreme_floor = bool(
            isinstance(cfg, dict)
            and cfg.get("extreme_hard_floor")
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
    task_override: dict[str, Any] | None = None,
    status_override: str | None = None,
) -> dict[str, Any]:
    """Build one ordered package without mutating lifecycle state."""
    if type(max_bytes) is not int or not MIN_MAX_BYTES <= max_bytes <= MAX_MAX_BYTES:
        raise ValueError(f"max_bytes must be {MIN_MAX_BYTES}..{MAX_MAX_BYTES}")
    task = dict(task_override or svc.be.task_get_full(slug) or {})
    if not task:
        raise TaskPackageError("TASK_NOT_FOUND", slug)
    if status_override is not None:
        task["status"] = status_override
    decisions = _active_decisions(svc, slug)
    assurance = _assurance_projection(svc, task)
    review_route = _review_route(svc, task, assurance)
    plan = _decoded(task.get("plan"), [])
    required = {
        "slug": task["slug"],
        "title": task.get("title"),
        "stack": task.get("stack"),
        "status": task.get("status"),
        "complexity": task.get("complexity"),
        "goal": task.get("goal"),
        "acceptance_criteria": task.get("acceptance_criteria"),
        "scope": task.get("scope"),
        "scope_exclude": task.get("scope_exclude"),
        "scope_paths": _decoded(task.get("scope_paths"), []),
        "scope_tools": _decoded(task.get("scope_tools"), []),
        "relevant_files": _decoded(task.get("relevant_files"), []),
        "plan": [
            {"id": i + 1, "step": item.get("step"), "done": bool(item.get("done"))}
            if isinstance(item, dict)
            else {"id": i + 1, "step": str(item), "done": False}
            for i, item in enumerate(plan)
        ],
        "incomplete_step_ids": [
            i + 1
            for i, item in enumerate(plan)
            if not (isinstance(item, dict) and item.get("done"))
        ],
        "rollback_plan": task.get("rollback_plan"),
        "call_budget": task.get("call_budget"),
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
    memory = _selected_memory(svc, task, decisions)
    task_revision = task_contract_revision(task, decisions)
    memory_revisions = [
        {"id": row["id"], "revision": row["revision"], "source_hash": row["source_hash"]}
        for row in memory
    ]
    package: dict[str, Any] = {
        "schema_version": 2,
        "fingerprint": "",
        "task_revision": task_revision,
        "selected_memory_revisions": memory_revisions,
        "max_bytes": max_bytes,
        "required": required,
        "relevant_memory": memory,
        "overflow": False,
        "decomposition": {
            "required_bytes": _json_bytes(required),
            "memory_bytes": _json_bytes(memory),
            "selected_memory_count": len(memory),
        },
    }
    package["fingerprint"] = _hash(
        {"required": required, "task_revision": task_revision, "relevant_memory": memory}
    )
    _set_exact_size(package)
    if package["bytes"] > max_bytes:
        package["overflow"] = True
        package["overflow_reason"] = "canonical_package_exceeds_budget"
        package["guidance"] = (
            "Narrow scope or selected memory, split acceptance criteria into a child task, "
            "or explicitly raise the configured task-package budget. Memory content is never "
            "replaced by identifiers alone."
        )
        _set_exact_size(package)
    return package


def require_package_fits(package: dict[str, Any]) -> None:
    if package.get("overflow"):
        d = package.get("decomposition") or {}
        raise TaskPackageError(
            "PACKAGE_TOO_LARGE",
            f"measured={package.get('bytes')} limit={package.get('max_bytes')} "
            f"required={d.get('required_bytes')} memory={d.get('memory_bytes')}; "
            f"{package.get('guidance')}",
        )


def validate_package_contract(package: dict[str, Any]) -> None:
    """Refuse an incomplete canonical contract on both start and resume."""
    required = package.get("required") or {}
    missing: list[str] = []
    for field in ("goal", "acceptance_criteria"):
        if not str(required.get(field) or "").strip():
            missing.append(field)
    complexity = required.get("complexity")
    if (
        complexity in {"medium", "complex"}
        and not str(required.get("scope") or "").strip()
        and not required.get("scope_paths")
    ):
        missing.append("scope_or_scope_paths")
    if complexity in {"medium", "complex"} and not str(required.get("rollback_plan") or "").strip():
        missing.append("rollback_plan")
    if complexity == "complex":
        assurance = required.get("assurance") or {}
        if not isinstance(required.get("call_budget"), int) or required["call_budget"] <= 0:
            missing.append("call_budget")
        if not assurance.get("profiles"):
            missing.append("assurance_profiles")
        impact = assurance.get("impact") or {}
        if any(
            impact.get(field) in (None, "unknown")
            for field in ("level", "blast_radius", "reversibility")
        ):
            missing.append("assurance_impact")
    if missing:
        raise TaskPackageError(
            "PACKAGE_INVALID", "missing or incomplete fields: " + ", ".join(missing)
        )


def persist_task_context_package(svc: Any, package: dict[str, Any]) -> None:
    slug = package["required"]["slug"]
    svc.be._ex(
        "INSERT INTO task_context_packages(task_slug,fingerprint,payload_json,bytes,max_bytes,"
        "task_revision,selected_memory_revisions,created_at) VALUES(?,?,?,?,?,?,?,?) "
        "ON CONFLICT(task_slug) DO UPDATE SET fingerprint=excluded.fingerprint, "
        "payload_json=excluded.payload_json,bytes=excluded.bytes,max_bytes=excluded.max_bytes,"
        "task_revision=excluded.task_revision,selected_memory_revisions=excluded.selected_memory_revisions,"
        "created_at=excluded.created_at",
        (
            slug,
            package["fingerprint"],
            json.dumps(package, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            package["bytes"],
            package["max_bytes"],
            package["task_revision"],
            json.dumps(package["selected_memory_revisions"], sort_keys=True, separators=(",", ":")),
            utcnow_iso(),
        ),
    )


def validate_package_payload(package: dict[str, Any]) -> None:
    """Verify canonical payload metadata instead of trusting stored columns."""
    expected_fingerprint = _hash(
        {
            "required": package.get("required"),
            "task_revision": package.get("task_revision"),
            "relevant_memory": package.get("relevant_memory"),
        }
    )
    if package.get("fingerprint") != expected_fingerprint:
        raise TaskPackageError("PACKAGE_CORRUPT", "payload fingerprint does not match content")
    if package.get("bytes") != _json_bytes(package):
        raise TaskPackageError("PACKAGE_CORRUPT", "payload byte count does not match content")


def load_task_context_package(svc: Any, slug: str) -> dict[str, Any] | None:
    row = svc.be._q1("SELECT * FROM task_context_packages WHERE task_slug=?", (slug,))
    if row is None:
        return None
    try:
        payload = json.loads(row["payload_json"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TaskPackageError("PACKAGE_CORRUPT", str(exc)) from exc
    if not isinstance(payload, dict):
        raise TaskPackageError("PACKAGE_CORRUPT", "payload must be an object")
    validate_package_payload(payload)
    required = payload.get("required")
    if not isinstance(required, dict) or required.get("slug") != slug:
        raise TaskPackageError("PACKAGE_CORRUPT", "payload task slug does not match stored row")
    expected_memory = json.dumps(
        payload.get("selected_memory_revisions"), sort_keys=True, separators=(",", ":")
    )
    if (
        row["fingerprint"] != payload.get("fingerprint")
        or row["bytes"] != payload.get("bytes")
        or row["max_bytes"] != payload.get("max_bytes")
        or row["task_revision"] != payload.get("task_revision")
        or row["selected_memory_revisions"] != expected_memory
    ):
        raise TaskPackageError("PACKAGE_CORRUPT", "stored metadata does not match payload")
    return payload


def assert_package_snapshot_current(svc: Any, package: dict[str, Any]) -> None:
    validate_package_payload(package)
    slug = package["required"]["slug"]
    task = svc.be.task_get_full(slug)
    if task is None:
        raise TaskPackageError("REVISION_CONFLICT", "task disappeared while packaging")
    if task_contract_revision(task, _active_decisions(svc, slug)) != package["task_revision"]:
        raise TaskPackageError("REVISION_CONFLICT", "task contract changed while packaging")
    for selected in package["selected_memory_revisions"]:
        row = svc.be.memory_get(int(selected["id"]))
        if row is None or _hash(_memory_source(row)) != selected["source_hash"]:
            raise TaskPackageError(
                "REVISION_CONFLICT", f"selected memory #{selected['id']} changed while packaging"
            )


def package_is_current(svc: Any, package: dict[str, Any]) -> bool:
    try:
        assert_package_snapshot_current(svc, package)
    except Exception:  # noqa: BLE001 - freshness is a fail-closed boolean boundary
        return False
    return True


def serialize_task_context_package(svc: Any, slug: str, *, max_bytes: int) -> str:
    stored = load_task_context_package(svc, slug)
    package = (
        stored
        if stored is not None
        and stored.get("max_bytes") == max_bytes
        and package_is_current(svc, stored)
        else build_task_context_package(svc, slug, max_bytes=max_bytes)
    )
    return json.dumps(
        package,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
