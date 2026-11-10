"""Task-package binding and freshness checks for execution leases."""

from __future__ import annotations

import json
import hashlib
import ntpath
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, cast

_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_TASK_ARGUMENT_BY_ROUTE = {
    "tausik_decide": "task_slug",
    "tausik_dead_end": "task_slug",
    "tausik_memory_add": "task_slug",
    "tausik_reason_step": "slug",
    "tausik_review_record": "task",
    "tausik_spec_link": "task_slug",
    "tausik_spec_unlink": "task_slug",
    "tausik_usage_event_log": "task_slug",
    "tausik_verify": "task_slug",
    "cli_task_mutation": "slug",
}
_REBIND_ROUTES = frozenset({"tausik_task_start", "cli_task_start"})
_SESSION_BOOTSTRAP_ROUTES = frozenset({"tausik_session_open", "tausik_session_start"})
_UNBOUND_TASK_ROUTES = frozenset({"tausik_task_add", "tausik_task_quick"})
_OPTIONAL_TASK_ARGUMENT_ROUTES = frozenset(
    {
        "tausik_decide",
        "tausik_dead_end",
        "tausik_memory_add",
        "tausik_usage_event_log",
        "tausik_verify",
    }
)
_CONDITIONAL_TASK_TARGET_ROUTES = frozenset(
    {"tausik_adapt_link", "tausik_actz_link", "tausik_actz_unlink"}
)
_PROJECT_LEVEL_ROUTES = frozenset(
    {
        "tausik_verify_cohort",
        "tausik_verify_hierarchy",
        "cli_verify_cohort",
        "cli_verify_hierarchy",
    }
)


def utc(instant: datetime | None = None) -> datetime:
    value = instant or datetime.now(timezone.utc)
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def iso(instant: datetime) -> str:
    return utc(instant).isoformat().replace("+00:00", "Z")


def normalized_project_hash(project_dir: str) -> str | None:
    raw = str(project_dir).strip()
    if not raw:
        return None
    if _WINDOWS_ABSOLUTE.match(raw):
        normalized = ntpath.normcase(ntpath.normpath(raw)).replace("\\", "/")
    else:
        normalized = os.path.normcase(os.path.realpath(os.path.abspath(raw))).replace("\\", "/")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_project_identity(project_dir: str) -> str:
    normalized = normalized_project_hash(project_dir)
    if normalized is None:
        from service_execution_lease import ExecutionLeaseError

        raise ExecutionLeaseError("IDENTITY_MISSING", "project path is empty")
    return normalized


def authorization_hash(arguments: Mapping[str, object]) -> str:
    encoded = json.dumps(arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def project_dir_from_tausik(svc: Any) -> str:
    return str(Path(svc.tausik_dir()).resolve().parent)


def active_task_package(svc: Any, *, include_payload: bool = False) -> dict[str, Any] | None:
    columns = ",p.payload_json" if include_payload else ""
    return cast(
        dict[str, Any] | None,
        svc.be._q1(
            f"SELECT t.slug AS task_slug,p.fingerprint{columns} FROM tasks t "
            "LEFT JOIN task_context_packages p ON p.task_slug=t.slug WHERE t.status='active' "
            "ORDER BY t.started_at DESC,t.id DESC LIMIT 1"
        ),
    )


def _bound_task_package(svc: Any, slug: str) -> dict[str, Any] | None:
    return cast(
        dict[str, Any] | None,
        svc.be._q1(
            "SELECT t.slug AS task_slug,t.status,p.fingerprint,p.payload_json "
            "FROM tasks t LEFT JOIN task_context_packages p ON p.task_slug=t.slug "
            "WHERE t.slug=?",
            (slug,),
        ),
    )


def require_task_argument_binding(
    lease: Mapping[str, Any], route: str, arguments: Mapping[str, object]
) -> None:
    """Keep task-scoped mutations on the task selected by this thread."""
    if route in _REBIND_ROUTES or route in _UNBOUND_TASK_ROUTES:
        return
    if route == "tausik_task_review" and "cohort" in arguments:
        route = "tausik_review_cohort"
    if route == "tausik_review_cohort":
        if lease.get("task_slug"):
            from service_execution_lease import ExecutionLeaseError

            raise ExecutionLeaseError(
                "TASK_BINDING_SCOPE",
                "task-bound lease cannot authorize project-level review cohort mutation",
            )
        return
    if route in _PROJECT_LEVEL_ROUTES:
        if lease.get("task_slug"):
            from service_execution_lease import ExecutionLeaseError

            raise ExecutionLeaseError(
                "TASK_BINDING_SCOPE",
                f"task-bound lease cannot authorize project-level route {route}",
            )
        return
    argument: str | None
    if route in _CONDITIONAL_TASK_TARGET_ROUTES:
        if arguments.get("target_type") != "task":
            return
        argument = "target_slug"
    else:
        argument = (
            "slug" if route.startswith("tausik_task_") else _TASK_ARGUMENT_BY_ROUTE.get(route)
        )
    if argument is None:
        return
    slug = arguments.get(argument)
    bound = lease.get("task_slug")
    if not isinstance(slug, str) or not slug:
        if route in _OPTIONAL_TASK_ARGUMENT_ROUTES:
            return
        from service_execution_lease import ExecutionLeaseError

        raise ExecutionLeaseError(
            "TASK_BINDING_MISSING", f"{route} requires explicit {argument} for a bound lease"
        )
    if slug != bound:
        from service_execution_lease import ExecutionLeaseError

        raise ExecutionLeaseError(
            "TASK_BINDING_MISMATCH",
            f"lease is bound to {bound!r}, not task {slug!r}",
        )


def route_allows_package_bypass(route: str | None) -> bool:
    """Allow only lifecycle routes that establish session/task package context."""
    return route in _REBIND_ROUTES or route in _SESSION_BOOTSTRAP_ROUTES


def require_current_task_package(svc: Any, lease: Mapping[str, Any]) -> None:
    """Reject a lease whose persisted task snapshot is absent or out of date."""
    from service_execution_lease import ExecutionLeaseError

    slug = lease.get("task_slug")
    if not isinstance(slug, str) or not slug:
        active_count = svc.be._q1("SELECT COUNT(*) AS n FROM tasks WHERE status='active'")
        if active_count and active_count["n"]:
            raise ExecutionLeaseError("PACKAGE_STALE", "lease is not bound to an active task")
        return
    bound = _bound_task_package(svc, slug)
    if bound is None or bound.get("status") != "active":
        raise ExecutionLeaseError("PACKAGE_STALE", "bound task is no longer active")
    if not bound.get("fingerprint") or not bound.get("payload_json"):
        raise ExecutionLeaseError(
            "PACKAGE_STALE", "bound active task has no persisted context package"
        )
    if lease.get("task_package_fingerprint") != bound["fingerprint"]:
        raise ExecutionLeaseError(
            "PACKAGE_STALE", "lease fingerprint differs from its bound task package"
        )
    try:
        from task_context_package import load_task_context_package, package_is_current

        package = load_task_context_package(svc, slug)
    except Exception as exc:
        raise ExecutionLeaseError("PACKAGE_STALE", f"stored package is corrupt: {exc}") from exc
    if package is None or not package_is_current(svc, package):
        raise ExecutionLeaseError(
            "PACKAGE_STALE", "task contract or selected memory changed after lease binding"
        )


def renewal_package_binding(
    svc: Any, existing: Mapping[str, Any] | None
) -> tuple[str | None, str | None]:
    """Validate and preserve a prior thread binding during lease renewal."""
    if existing is None:
        return None, None
    slug = existing.get("task_slug")
    if isinstance(slug, str) and slug:
        require_current_task_package(svc, existing)
        fingerprint = existing.get("task_package_fingerprint")
        return slug, fingerprint if isinstance(fingerprint, str) else None
    active = svc.be._q1("SELECT COUNT(*) AS n FROM tasks WHERE status='active'")
    if active and active["n"]:
        from service_execution_lease import ExecutionLeaseError

        raise ExecutionLeaseError(
            "PACKAGE_STALE", "unbound lease cannot renew while a task is active"
        )
    return None, None
