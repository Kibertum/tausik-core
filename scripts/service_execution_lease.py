"""Trusted Codex hook assertions and execution-lease lifecycle."""

from __future__ import annotations

import secrets
import sqlite3
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping, cast

from execution_lease_package import (
    authorization_hash,
    iso as _iso,
    normalize_project_identity,
    project_dir_from_tausik as project_dir_from_tausik,
    renewal_package_binding,
    require_current_task_package,
    require_task_argument_binding,
    route_allows_package_bypass,
    utc as _utc,
)
from execution_lease_capability import CAPABILITY_VERSION, schema_compatible as _schema_compatible
from tausik_utils import ServiceError
from tausik_version import __version__

DEFAULT_TTL_SECONDS = 15 * 60
ASSERTION_TTL_SECONDS = 30
AUTHORIZATION_TTL_SECONDS = 15
_MAINTENANCE_KEY = "execution_lease_maintenance"
_AUTHORIZATION_ARGUMENT = "_tausik_authorization"


class ExecutionLeaseError(ServiceError):
    """Typed refusal whose code is stable across hook and MCP transports."""

    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class TrustedHostAssertion:
    project_identity: str
    host_instance: str
    thread_id: str
    assertion_nonce: str
    issued_at: datetime
    expires_at: datetime


def _assertion_from_trusted_hook(
    payload: Mapping[str, object],
    project_dir: str,
    *,
    trusted_host: str,
    expected_event: str,
    now: datetime | None = None,
) -> TrustedHostAssertion:
    """Create authority only in an attested host hook with exact thread identity."""

    event = payload.get("hook_event_name") or payload.get("hookEventName")
    if event != expected_event:
        raise ExecutionLeaseError("IDENTITY_UNTRUSTED", f"event is not {expected_event}")
    raw_thread = payload.get("session_id")
    if not isinstance(raw_thread, str) or not raw_thread.strip():
        raise ExecutionLeaseError("IDENTITY_MISSING", f"{expected_event} has no session_id")
    host = trusted_host.casefold()
    if host not in {"codex", "cursor"}:
        raise ExecutionLeaseError("IDENTITY_UNTRUSTED", "issuer is not a trusted host adapter")
    issued = _utc(now)
    return TrustedHostAssertion(
        normalize_project_identity(project_dir),
        host,
        raw_thread.strip(),
        secrets.token_hex(16),
        issued,
        issued + timedelta(seconds=ASSERTION_TTL_SECONDS),
    )


def assertion_from_session_start(
    payload: Mapping[str, object],
    project_dir: str,
    *,
    trusted_host: str,
    now: datetime | None = None,
) -> TrustedHostAssertion:
    """Create authority in a host-specific trusted SessionStart adapter."""

    return _assertion_from_trusted_hook(
        payload,
        project_dir,
        trusted_host=trusted_host,
        expected_event="SessionStart",
        now=now,
    )


def assertion_from_pre_tool_use(
    payload: Mapping[str, object],
    project_dir: str,
    *,
    trusted_host: str,
    now: datetime | None = None,
) -> TrustedHostAssertion:
    """Create renewal authority at the last trusted boundary before execution."""

    return _assertion_from_trusted_hook(
        payload,
        project_dir,
        trusted_host=trusted_host,
        expected_event="PreToolUse",
        now=now,
    )


def _maintenance_marker(svc: Any) -> str | None:
    row = svc.be._q1("SELECT value FROM meta WHERE key=?", (_MAINTENANCE_KEY,))
    return str(row["value"]) if row is not None else None


def _enter_maintenance(svc: Any, reason: str, instant: datetime) -> None:
    at = _iso(instant)
    with svc.be.transaction():
        svc.be._ex(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (_MAINTENANCE_KEY, reason),
        )
        try:
            svc.be._execution_lease_revoke_all(at)
        except sqlite3.Error:
            pass
        try:
            svc.be._ex(
                "UPDATE memory_preflight_tokens SET status='failed',completed_at=?,failure_code=? "
                "WHERE status IN ('issued','reserved')",
                (at, "CAPABILITY_MAINTENANCE"),
            )
        except sqlite3.Error:
            pass
        try:
            svc.be._execution_lease_set_state(
                mode="maintenance",
                reason=reason,
                projection_build=__version__,
                capability_version=CAPABILITY_VERSION,
                updated_at=at,
            )
        except sqlite3.Error:
            pass


def enter_execution_lease_maintenance(svc: Any, reason: str) -> None:
    """Persist a fail-closed state discovered by a trusted runtime boundary."""

    _enter_maintenance(svc, reason, _utc())


def _recover_state(svc: Any, instant: datetime, *, failure_code: str) -> None:
    svc.be._execution_lease_revoke_all(_iso(instant))
    svc.be._ex(
        "UPDATE memory_preflight_tokens SET status='failed',completed_at=?,failure_code=? "
        "WHERE status IN ('issued','reserved')",
        (_iso(instant), failure_code),
    )
    svc.be._execution_lease_set_state(
        mode="ready",
        reason=None,
        projection_build=__version__,
        capability_version=CAPABILITY_VERSION,
        updated_at=_iso(instant),
    )
    svc.be._ex("DELETE FROM meta WHERE key=?", (_MAINTENANCE_KEY,))


def reconcile_execution_lease_state(svc: Any, assertion: TrustedHostAssertion) -> None:
    """Validate ready state at SessionStart; never clear maintenance implicitly."""

    if not isinstance(assertion, TrustedHostAssertion):
        raise ExecutionLeaseError("IDENTITY_UNTRUSTED", "reconciliation requires hook authority")
    instant = _utc()
    if not _schema_compatible(svc):
        _enter_maintenance(svc, "persistent lease schema is incompatible", instant)
        raise ExecutionLeaseError("CAPABILITY_MISMATCH", "persistent lease schema is incompatible")
    problem: str | None = None
    with svc.be.transaction():
        state = svc.be._execution_lease_state()
        marker = _maintenance_marker(svc)
        if marker is not None:
            raise ExecutionLeaseError("LEASE_MAINTENANCE", marker)
        if state is None:
            if svc.be._q1("SELECT id FROM execution_leases LIMIT 1") is not None:
                problem = "lease state is missing for existing leases"
            else:
                svc.be._execution_lease_set_state(
                    mode="ready",
                    reason=None,
                    projection_build=__version__,
                    capability_version=CAPABILITY_VERSION,
                    updated_at=_iso(instant),
                )
                return
        elif state["mode"] != "ready":
            raise ExecutionLeaseError(
                "LEASE_MAINTENANCE", str(state.get("reason") or "owner reconciliation is required")
            )
        elif state["capability_version"] != CAPABILITY_VERSION:
            problem = "persisted execution-lease capability differs from this build"
        elif state["projection_build"] != __version__:
            # Build is provenance; CAPABILITY_VERSION is the compatibility boundary.
            svc.be._execution_lease_set_state(
                mode="ready",
                reason=None,
                projection_build=__version__,
                capability_version=CAPABILITY_VERSION,
                updated_at=_iso(instant),
            )
            incompatible = svc.be._q1(
                "SELECT id FROM execution_leases WHERE revoked_at IS NULL "
                "AND (capability_min>? OR capability_max<?) LIMIT 1",
                (CAPABILITY_VERSION, CAPABILITY_VERSION),
            )
            if incompatible is not None:
                problem = "mixed execution-lease capability"
        elif problem is None:
            incompatible = svc.be._q1(
                "SELECT id FROM execution_leases WHERE revoked_at IS NULL "
                "AND (capability_min>? OR capability_max<?) LIMIT 1",
                (CAPABILITY_VERSION, CAPABILITY_VERSION),
            )
            if incompatible is not None:
                problem = "mixed execution-lease capability"
    if problem is not None:
        _enter_maintenance(svc, problem, instant)
        raise ExecutionLeaseError("CAPABILITY_MISMATCH", problem)


def recover_execution_lease_state(svc: Any, confirmation: str) -> None:
    """Owner recovery: validate schema, revoke bindings, and acknowledge this build."""

    if confirmation != "revoke-and-reconcile":
        raise ExecutionLeaseError("RECOVERY_CONFIRMATION_REQUIRED", "pass revoke-and-reconcile")
    instant = _utc()
    if not _schema_compatible(svc):
        _enter_maintenance(svc, "persistent lease schema is incompatible", instant)
        raise ExecutionLeaseError("CAPABILITY_MISMATCH", "repair or migrate schema first")
    with svc.be.transaction():
        _recover_state(svc, instant, failure_code="OWNER_RECONCILIATION")
    marker = os.path.join(os.path.dirname(svc.be.db_path), "execution-lease-maintenance")
    try:
        os.remove(marker)
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise ExecutionLeaseError(
            "RECOVERY_MARKER_REMOVE_FAILED",
            f"database recovered but emergency marker remains: {exc}",
        ) from exc


def issue_execution_lease(
    svc: Any,
    assertion: TrustedHostAssertion,
    *,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> dict[str, Any]:
    """Atomically open/reuse the host session and issue its durable lease."""

    if not isinstance(assertion, TrustedHostAssertion):
        raise ExecutionLeaseError("IDENTITY_UNTRUSTED", "lease issuance requires hook authority")
    if ttl_seconds <= 0:
        raise ExecutionLeaseError("LEASE_INVALID", "ttl_seconds must be positive")
    issued = _utc(now)
    if assertion.expires_at <= issued:
        raise ExecutionLeaseError("ASSERTION_STALE", "trusted SessionStart assertion expired")
    if assertion.issued_at > issued + timedelta(seconds=5):
        raise ExecutionLeaseError("IDENTITY_MISMATCH", "assertion was issued in the future")
    with svc.be.transaction():
        marker = _maintenance_marker(svc)
        if marker is not None:
            raise ExecutionLeaseError("LEASE_MAINTENANCE", marker)
        state = svc.be._execution_lease_state()
        if (
            state is None
            or state["mode"] != "ready"
            or state["projection_build"] != __version__
            or state["capability_version"] != CAPABILITY_VERSION
        ):
            raise ExecutionLeaseError("LEASE_MAINTENANCE", "owner reconciliation is required")
        previous_assertion = svc.be._execution_lease_by_assertion(assertion.assertion_nonce)
        if previous_assertion is not None and (
            previous_assertion["revoked_at"] is not None
            or previous_assertion["expires_at"] <= _iso(issued)
        ):
            raise ExecutionLeaseError(
                "ASSERTION_REPLAY", "assertion already produced a terminal lease"
            )
        existing = svc.be._execution_lease_current(
            assertion.project_identity, assertion.host_instance, assertion.thread_id
        )
        renewal_source = existing or svc.be._q1(
            "SELECT * FROM execution_leases WHERE project_identity=? AND host_instance=? "
            "AND thread_id=? ORDER BY id DESC LIMIT 1",
            (assertion.project_identity, assertion.host_instance, assertion.thread_id),
        )
        task_slug, task_fingerprint = renewal_package_binding(svc, renewal_source)
        svc.session_start(assertion.thread_id)
        session = svc.be.session_current(assertion.thread_id)
        if session is None:
            raise ExecutionLeaseError("IDENTITY_MISSING", "host session was not created")
        try:
            lease = svc.be._execution_lease_issue(
                session_id=session["id"],
                project_identity=assertion.project_identity,
                host_instance=assertion.host_instance,
                thread_id=assertion.thread_id,
                assertion_nonce=assertion.assertion_nonce,
                assertion_issued_at=_iso(assertion.issued_at),
                assertion_expires_at=_iso(assertion.expires_at),
                nonce=secrets.token_hex(16),
                issued_at=_iso(issued),
                expires_at=_iso(issued + timedelta(seconds=ttl_seconds)),
                projection_build=__version__,
                capability_min=CAPABILITY_VERSION,
                capability_max=CAPABILITY_VERSION,
                task_slug=task_slug,
                task_package_fingerprint=task_fingerprint,
            )
        except ValueError as exc:
            raise ExecutionLeaseError("IDENTITY_AMBIGUOUS", str(exc)) from exc
        return cast(dict[str, Any], lease)


def require_execution_lease(
    svc: Any,
    *,
    project_dir: str,
    host_instance: str | None,
    thread_id: str | None,
    nonce: str | None,
    now: datetime | None = None,
    allow_package_rebind: bool = False,
) -> dict[str, Any]:
    """Validate a complete binding; trusted hooks supply the thread identity."""

    if not host_instance or not thread_id or not nonce:
        raise ExecutionLeaseError("IDENTITY_MISSING", "host, thread and nonce are required")
    instant = _utc(now)
    marker = _maintenance_marker(svc)
    if marker is not None:
        raise ExecutionLeaseError("LEASE_MAINTENANCE", marker)
    if not _schema_compatible(svc):
        _enter_maintenance(svc, "persistent lease schema is incompatible", instant)
        raise ExecutionLeaseError("CAPABILITY_MISMATCH", "persistent lease schema is incompatible")
    state = svc.be._execution_lease_state()
    if state is None or state["mode"] != "ready":
        raise ExecutionLeaseError("LEASE_MAINTENANCE", "lease state requires reconciliation")
    if state["capability_version"] != CAPABILITY_VERSION:
        _enter_maintenance(
            svc, "persisted execution-lease capability differs from this build", instant
        )
        raise ExecutionLeaseError(
            "CAPABILITY_MISMATCH", "persisted capability differs from this build"
        )
    lease = svc.be._execution_lease_by_nonce(nonce)
    if lease is None:
        raise ExecutionLeaseError("LEASE_MISSING", "nonce is unknown")
    open_session = svc.be._q1(
        "SELECT id FROM sessions WHERE id=? AND ended_at IS NULL",
        (lease["session_id"],),
    )
    if open_session is None:
        raise ExecutionLeaseError("LEASE_REVOKED", "bound TAUSIK session is not open")
    expected = (
        normalize_project_identity(project_dir),
        host_instance.casefold(),
        thread_id.strip(),
    )
    actual = (lease["project_identity"], lease["host_instance"], lease["thread_id"])
    if actual != expected:
        raise ExecutionLeaseError("IDENTITY_MISMATCH", "lease binding does not match trusted hook")
    if lease["revoked_at"] is not None:
        raise ExecutionLeaseError("LEASE_REVOKED", "lease has been revoked")
    if lease["expires_at"] <= _iso(instant):
        raise ExecutionLeaseError("LEASE_STALE", "lease has expired")
    if not (lease["capability_min"] <= CAPABILITY_VERSION <= lease["capability_max"]):
        _enter_maintenance(svc, "mixed execution-lease capability", instant)
        raise ExecutionLeaseError("CAPABILITY_MISMATCH", "lease capability is incompatible")
    if not allow_package_rebind:
        require_current_task_package(svc, lease)
    return cast(dict[str, Any], lease)


def authorize_mcp_mutation(
    svc: Any,
    *,
    lease: Mapping[str, Any],
    route: str,
    arguments: Mapping[str, object],
    correlated: bool = False,
    now: datetime | None = None,
) -> str | None:
    if _AUTHORIZATION_ARGUMENT in arguments:
        raise ExecutionLeaseError(
            "AUTHORIZATION_FORGED", "model-supplied MCP authorization is forbidden"
        )
    require_task_argument_binding(lease, route, arguments)
    from work_continuity import enforce_continuity_boundary

    enforce_continuity_boundary(svc, lease, route, arguments)
    instant = _utc(now)
    correlation = secrets.token_urlsafe(32) if correlated else None
    arguments_identity: Mapping[str, object] = arguments
    if correlation is not None:
        arguments_identity = {
            "arguments": dict(arguments),
            "hook_correlation": correlation,
        }
    svc.be._execution_authorization_issue(
        lease_id=int(lease["id"]),
        route=route,
        arguments_hash=authorization_hash(arguments_identity),
        issued_at=_iso(instant),
        expires_at=_iso(instant + timedelta(seconds=AUTHORIZATION_TTL_SECONDS)),
    )
    return correlation


def consume_mcp_authorization(
    svc: Any,
    *,
    route: str,
    arguments: Mapping[str, object],
    authorization: str | None = None,
    require_correlation: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    if require_correlation and (not isinstance(authorization, str) or not authorization):
        raise ExecutionLeaseError("IDENTITY_MISSING", "MCP call has no hook-issued correlation")
    arguments_identity: Mapping[str, object] = arguments
    if isinstance(authorization, str) and authorization:
        arguments_identity = {
            "arguments": dict(arguments),
            "hook_correlation": authorization,
        }
    instant = _utc(now)
    try:
        row = svc.be._execution_authorization_consume(
            route=route,
            arguments_hash=authorization_hash(arguments_identity),
            consumed_at=_iso(instant),
        )
    except ValueError as exc:
        raise ExecutionLeaseError("AUTHORIZATION_AMBIGUOUS", str(exc)) from exc
    if row is None:
        raise ExecutionLeaseError(
            "IDENTITY_MISSING", "no authorization from this thread's PreToolUse event"
        )
    lease = svc.be._q1("SELECT * FROM execution_leases WHERE id=?", (row["lease_id"],))
    if lease is None:
        raise ExecutionLeaseError("LEASE_MISSING", "authorization lease disappeared")
    validated = require_execution_lease(
        svc,
        project_dir=project_dir_from_tausik(svc),
        host_instance=lease.get("host_instance"),
        thread_id=lease.get("thread_id"),
        nonce=lease.get("nonce"),
        now=instant,
        allow_package_rebind=route_allows_package_bypass(route),
    )
    require_task_argument_binding(validated, route, arguments)
    return cast(dict[str, Any], validated)
