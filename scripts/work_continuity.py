"""Evidence-bound plan progress and bounded work-continuity recovery."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from tausik_utils import ServiceError, utcnow_iso

REFUSAL_LIMIT = 3


def continuity_schema_compatible(be: Any) -> bool:
    required = {
        "task_step_evidence": {
            "id",
            "task_slug",
            "step_num",
            "evidence_ref",
            "evidence_hash",
            "package_fingerprint",
            "created_at",
        },
        "task_continuity_state": {
            "task_slug",
            "package_fingerprint",
            "first_incomplete_step",
            "last_evidence_ref",
            "pending_requirement",
            "recovery_lease_id",
            "recovery_issued_at",
            "recovery_consumed_at",
            "refusal_hash",
            "refusal_count",
            "blocker_json",
            "updated_at",
        },
    }
    for table, columns in required.items():
        if not columns <= {row[1] for row in be._conn.execute(f"PRAGMA table_info({table})")}:
            return False
    indexes = {
        row[0] for row in be._conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    }
    return {"idx_task_step_evidence_task", "idx_task_continuity_pending"} <= indexes


class ContinuityError(ServiceError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


def _strict(task: Mapping[str, Any]) -> bool:
    return task.get("complexity") == "complex" and not task.get("task_package_legacy")


def _fingerprint(svc: Any, slug: str) -> str:
    row = svc.be._q1("SELECT fingerprint FROM task_context_packages WHERE task_slug=?", (slug,))
    if row is None or not row.get("fingerprint"):
        raise ContinuityError("PACKAGE_STALE", "continuity requires a persisted task package")
    return str(row["fingerprint"])


def _evidence_hash(ref: str) -> str:
    return hashlib.sha256(ref.encode("utf-8")).hexdigest()


def validate_evidence_ref(svc: Any, slug: str, evidence_ref: str) -> str:
    """Validate an immutable, task-bound evidence identity; return canonical ref."""
    ref = evidence_ref.strip()
    if ref.startswith("artifact:sha256:") and len(ref) == 80:
        digest = ref.removeprefix("artifact:sha256:")
        if all(char in "0123456789abcdef" for char in digest):
            return ref
    kind, sep, raw_id = ref.partition(":")
    if not sep or not raw_id.isdigit():
        raise ContinuityError(
            "STEP_EVIDENCE_INVALID",
            "use reason:<seq>, verify:<id>, decision:<id>, or artifact:sha256:<digest>",
        )
    number = int(raw_id)
    if kind == "reason":
        row = svc.be._q1(
            "SELECT kind FROM reasoning_steps WHERE task_slug=? AND seq=?", (slug, number)
        )
        if row is not None and row["kind"] in {"action", "verification"}:
            return f"reason:{number}"
    elif kind == "verify":
        row = svc.be._q1(
            "SELECT exit_code FROM verification_runs WHERE task_slug=? AND id=?", (slug, number)
        )
        if row is not None and int(row["exit_code"]) == 0:
            return f"verify:{number}"
    elif kind == "decision":
        row = svc.be._q1("SELECT id FROM decisions WHERE task_slug=? AND id=?", (slug, number))
        if row is not None:
            return f"decision:{number}"
    raise ContinuityError(
        "STEP_EVIDENCE_INVALID", f"{ref!r} is not immutable, green, and bound to {slug!r}"
    )


def complete_plan_step(svc: Any, slug: str, step_num: int, evidence_ref: str | None) -> str:
    """Atomically persist strict-task step state and its immutable evidence link."""
    task = svc._require_task(slug)
    if not task.get("plan"):
        raise ServiceError(f"Task '{slug}' has no plan")
    try:
        steps = json.loads(task.get("plan") or "")
    except (TypeError, ValueError) as exc:
        raise ServiceError(f"Corrupted plan data for task '{slug}': {exc}") from exc
    if not isinstance(steps, list) or not steps:
        raise ServiceError(f"Task '{slug}' has no plan")
    if step_num < 1 or step_num > len(steps):
        raise ServiceError(f"Step {step_num} out of range (1-{len(steps)})")
    if not _strict(task):
        steps[step_num - 1]["done"] = True
        svc.be.task_update(slug, plan=json.dumps(steps))
        svc._project_task(slug)
        return f"Step {step_num} done ({sum(bool(s.get('done')) for s in steps)}/{len(steps)})."
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise ContinuityError(
            "STEP_EVIDENCE_REQUIRED", "a strict complex task step needs immutable evidence"
        )
    now = utcnow_iso()
    with svc.be.transaction():
        canonical = validate_evidence_ref(svc, slug, evidence_ref)
        fingerprint = _fingerprint(svc, slug)
        authorized = getattr(svc, "_authorized_execution_lease", None)
        if isinstance(authorized, Mapping) and (
            authorized.get("task_slug") != slug
            or authorized.get("task_package_fingerprint") != fingerprint
        ):
            raise ContinuityError(
                "PACKAGE_STALE", "step authorization is not bound to the current package"
            )
        digest = _evidence_hash(canonical)
        fresh = svc.be.task_get(slug)
        current = json.loads(fresh.get("plan") or "[]")
        existing = svc.be._q1(
            "SELECT id FROM task_step_evidence WHERE task_slug=? AND step_num=? AND evidence_hash=?",
            (slug, step_num, digest),
        )
        if current[step_num - 1].get("done"):
            if existing is None:
                raise ContinuityError(
                    "STEP_ALREADY_DONE", "the completed step has a different evidence identity"
                )
        else:
            svc.be._ex(
                "INSERT INTO task_step_evidence(task_slug,step_num,evidence_ref,evidence_hash,package_fingerprint,created_at) VALUES(?,?,?,?,?,?)",
                (slug, step_num, canonical, digest, fingerprint, now),
            )
            current[step_num - 1]["done"] = True
            svc.be.task_update(slug, plan=json.dumps(current))
        first = next((i for i, item in enumerate(current, 1) if not item.get("done")), None)
        svc.be._ex(
            "INSERT INTO task_continuity_state(task_slug,package_fingerprint,first_incomplete_step,last_evidence_ref,updated_at) VALUES(?,?,?,?,?) "
            "ON CONFLICT(task_slug) DO UPDATE SET package_fingerprint=excluded.package_fingerprint,first_incomplete_step=excluded.first_incomplete_step,last_evidence_ref=excluded.last_evidence_ref,updated_at=excluded.updated_at",
            (slug, fingerprint, first, canonical, now),
        )
    svc._project_task(slug)
    return f"Step {step_num} done with {canonical} ({sum(bool(s.get('done')) for s in current)}/{len(current)})."


def _requirement(_svc: Any, _task: Mapping[str, Any]) -> str | None:
    """Call counts are advisory; native host-context telemetry owns hard stops."""
    return None


def _route_action(route: str, arguments: Mapping[str, object]) -> str:
    if route == "cli_task_mutation":
        action = arguments.get("action")
        return f"cli.task.{action}" if isinstance(action, str) else route
    return route


def _recovery_class(route: str, arguments: Mapping[str, object]) -> str | None:
    action = _route_action(route, arguments)
    if action in {"tausik_session_handoff", "cli_session_handoff", "cli.session.handoff"}:
        return "checkpoint"
    if action in {"tausik_task_block", "cli.task.block"}:
        return "blocker"
    if action in {"tausik_task_plan", "cli.task.plan"}:
        return "decompose"
    if action in {"tausik_reason_step", "cli.task.reason-step"}:
        return "reason"
    return None


def _action_hash(route: str, arguments: Mapping[str, object]) -> str:
    raw = json.dumps([route, arguments], sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _has_action_override(svc: Any, slug: str, route: str, arguments: Mapping[str, object]) -> bool:
    expected = {"route": route, "arguments_hash": _action_hash(route, arguments)}
    rows = svc.be._q(
        "SELECT content FROM reasoning_steps WHERE task_slug=? AND kind='action' ORDER BY seq DESC,id DESC LIMIT 10",
        (slug,),
    )
    for row in rows:
        try:
            value = json.loads(row["content"])
        except (TypeError, ValueError):
            continue
        if value == {"continuity_override": expected}:
            return True
    return False


def enforce_continuity_boundary(
    svc: Any, lease: Mapping[str, Any], route: str, arguments: Mapping[str, object]
) -> dict[str, Any] | None:
    """Retire call-count recovery state; host context owns live-task stops."""
    slug = lease.get("task_slug")
    if not isinstance(slug, str) or not slug:
        return None
    # These requirements came from estimated tool-call counts. They are advisory
    # in every host mode, including unattended runs. The autonomous 2x refusal
    # lives in call_budget_guard and is evaluated only between tasks.
    svc.be._ex(
        "UPDATE task_continuity_state SET pending_requirement=NULL,"
        "recovery_lease_id=NULL,recovery_issued_at=NULL,recovery_consumed_at=NULL,"
        "recovery_action=NULL,refusal_hash=NULL,refusal_count=0,blocker_json=NULL,updated_at=? "
        "WHERE task_slug=? AND pending_requirement IN "
        "('call_budget_exhausted','checkpoint_required')",
        (utcnow_iso(), slug),
    )
    return None


def complete_recovery(
    svc: Any,
    lease: Mapping[str, Any],
    route: str,
    arguments: Mapping[str, object],
    expected_generation: Mapping[str, Any] | None = None,
) -> None:
    """Consume a successful terminal recovery and revoke its normal authority."""
    slug = lease.get("task_slug")
    if not isinstance(slug, str) or not slug:
        return
    state = svc.be._q1("SELECT * FROM task_continuity_state WHERE task_slug=?", (slug,))
    if state is None or not state.get("pending_requirement"):
        return
    recovery = _recovery_class(route, arguments)
    overridden = _has_action_override(svc, slug, route, arguments)
    if recovery == "reason" or (recovery is None and not overridden):
        return
    requirement = state["pending_requirement"]
    if requirement == "call_budget_exhausted" and recovery == "checkpoint":
        return
    now = utcnow_iso()
    with svc.be.transaction():
        if expected_generation is not None:
            require_recovery_generation(svc, lease, expected_generation)
        changed = svc.be._ex(
            "UPDATE task_continuity_state SET pending_requirement=NULL,recovery_consumed_at=?,recovery_action=?,updated_at=? WHERE task_slug=? AND recovery_lease_id=? AND recovery_consumed_at IS NULL",
            (now, recovery, now, slug, int(lease["id"])),
        )
        if changed != 1:
            raise ContinuityError("RECOVERY_REPLAY", "recovery lease was already consumed")
        if recovery == "decompose":
            _materialize_decomposition(svc, slug)
        svc.be._ex("UPDATE execution_leases SET revoked_at=? WHERE id=?", (now, int(lease["id"])))
        svc.be._ex("DELETE FROM task_context_packages WHERE task_slug=?", (slug,))


def _materialize_decomposition(svc: Any, slug: str) -> list[str]:
    """Turn the replacement plan into runnable child tasks and park the parent."""
    parent = svc._require_task(slug)
    try:
        steps = json.loads(parent.get("plan") or "[]")
    except (TypeError, ValueError) as exc:
        raise ContinuityError("DECOMPOSITION_INVALID", "replacement plan is invalid") from exc
    if not isinstance(steps, list) or not steps:
        raise ContinuityError("DECOMPOSITION_INVALID", "decomposition needs at least one part")
    from service_task_order import task_depends

    children: list[str] = []
    for index, item in enumerate(steps, 1):
        title = str(item.get("step") or "").strip() if isinstance(item, dict) else ""
        if not title:
            raise ContinuityError("DECOMPOSITION_INVALID", "every part needs a title")
        parent_key = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:8]
        child = f"{slug[:38]}-{parent_key}-part-{index}"
        if svc.be.task_get(child) is not None:
            raise ContinuityError(
                "DECOMPOSITION_COLLISION", f"refusing to reuse existing child {child!r}"
            )
        svc.task_add(
            parent.get("story_slug"),
            child,
            title,
            stack=parent.get("stack"),
            complexity="medium",
            goal=f"Complete decomposed part {index} of {slug}: {title}",
            role=parent.get("role"),
            call_budget=parent.get("call_budget"),
        )
        svc.task_update(
            child,
            acceptance_criteria=(
                f"The part is implemented and verified against parent task {slug}. "
                "Negative: changes outside the inherited parent scope are refused."
            ),
            scope=parent.get("scope"),
            scope_exclude=parent.get("scope_exclude"),
            scope_paths=parent.get("scope_paths") or [],
            scope_tools=parent.get("scope_tools") or [],
            relevant_files=parent.get("relevant_files") or "[]",
            rollback_plan=parent.get("rollback_plan") or "Revert this decomposed part.",
            assurance_profiles=parent.get("assurance_profiles") or [],
            assurance_impact=parent.get("assurance_impact") or {},
        )
        task_depends(svc, slug, child)
        children.append(child)
    svc.task_block(
        slug,
        "Call budget exhausted; remaining work moved to child tasks.",
        "Should the parent be closed after every decomposed child passes QG-2?",
        "Every child is done and the owner confirms the parent resolution.",
    )
    return children


def require_recovery_generation(
    svc: Any, lease: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    """Revalidate single-use recovery under the dispatch write transaction."""
    slug = lease.get("task_slug")
    current = svc.be._q1("SELECT * FROM task_continuity_state WHERE task_slug=?", (slug,))
    live = svc.be._q1("SELECT revoked_at FROM execution_leases WHERE id=?", (lease["id"],))
    keys = ("task_slug", "pending_requirement", "recovery_lease_id", "recovery_issued_at")
    if (
        current is None
        or live is None
        or live.get("revoked_at") is not None
        or any(current.get(key) != expected.get(key) for key in keys)
        or int(current.get("recovery_lease_id") or 0) != int(lease["id"])
        or _fingerprint(svc, str(slug)) != lease.get("task_package_fingerprint")
    ):
        raise ContinuityError("RECOVERY_REPLAY", "recovery generation is no longer current")


def complete_cli_recovery(
    svc: Any,
    lease: Mapping[str, Any],
    action: str,
    expected_generation: Mapping[str, Any] | None = None,
) -> None:
    """Finish a CLI recovery after its service mutation returned successfully."""
    slug = lease.get("task_slug")
    if not isinstance(slug, str) or not slug:
        return
    route = "cli_session_handoff" if action == "session-handoff" else "cli_task_mutation"
    arguments = {} if route == "cli_session_handoff" else {"slug": slug, "action": action}
    complete_recovery(svc, lease, route, arguments, expected_generation)


def continuity_projection(be: Any, slug: str) -> dict[str, Any]:
    row = be._q1("SELECT * FROM task_continuity_state WHERE task_slug=?", (slug,)) or {}
    first = row.get("first_incomplete_step")
    if first is None:
        task = be.task_get(slug) or {}
        try:
            plan = json.loads(task.get("plan") or "[]")
            first = next((i for i, item in enumerate(plan, 1) if not item.get("done")), None)
        except (TypeError, ValueError, AttributeError):
            first = None
    package = be._q1("SELECT fingerprint FROM task_context_packages WHERE task_slug=?", (slug,))
    return {
        "package_fingerprint": row.get("package_fingerprint")
        or (package.get("fingerprint") if package else None),
        "first_incomplete_step": first,
        "last_verified_evidence": row.get("last_evidence_ref"),
        "pending_continuity_requirement": row.get("pending_requirement"),
        "resume_action": f".tausik/tausik task start {slug} --package",
        "blocker": json.loads(row["blocker_json"]) if row.get("blocker_json") else None,
    }
