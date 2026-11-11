"""Canonical host-context budget policy shared by CLI and MCP wrappers."""

from __future__ import annotations

import os
from typing import Any, Mapping, cast

from project_config import load_config
from tausik_utils import ServiceError

DEFAULT_BUDGET = {
    "advisory": {"responses": 24, "input_tokens": 2_500_000, "context_tokens": 140_000},
    "hard": {"responses": 32, "input_tokens": 4_000_000, "context_tokens": 180_000},
}
_METRICS = tuple(DEFAULT_BUDGET["advisory"])


def native_identity(env: Mapping[str, str] | None = None) -> tuple[str | None, str | None]:
    """Return a native host/thread pair only when the host exposes one."""
    values = env or os.environ
    thread = values.get("CODEX_THREAD_ID") or values.get("CODEX_SESSION_ID")
    if thread:
        return "codex", thread
    return None, None


def _budget(config: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    raw = config.get("host_context_budget", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        raise ServiceError("host_context_budget must be an object")
    result: dict[str, dict[str, int]] = {}
    for level in ("advisory", "hard"):
        supplied = raw.get(level, {})
        if not isinstance(supplied, Mapping):
            raise ServiceError(f"host_context_budget.{level} must be an object")
        result[level] = {}
        for metric in _METRICS:
            value = supplied.get(metric, DEFAULT_BUDGET[level][metric])
            if type(value) is not int or value <= 0:
                raise ServiceError(
                    f"host_context_budget.{level}.{metric} must be a positive integer"
                )
            result[level][metric] = value
    for metric in _METRICS:
        if result["advisory"][metric] >= result["hard"][metric]:
            raise ServiceError(
                f"host_context_budget.advisory.{metric} must be below the hard ceiling"
            )
    return result


def _usage(project_dir: str, host: str | None, thread_id: str | None) -> dict[str, Any]:
    if not host or not thread_id:
        return {"availability": "unavailable", "reason": "host thread identity is unavailable"}
    if host != "codex":
        return {
            "availability": "unavailable",
            "reason": f"{host} has no native host-context adapter",
        }
    try:
        from usage_codex_report import report

        observed = report(project_dir, thread_id=thread_id)
    except (OSError, ValueError) as exc:
        return {"availability": "unavailable", "reason": f"native usage read failed: {exc}"}
    if not observed.get("source_available"):
        return {"availability": "unavailable", "reason": "native Codex journal is unavailable"}
    if observed.get("responses", 0) == 0:
        return {
            "availability": "unavailable",
            "reason": "native Codex journal has no responses for this thread",
        }
    return {
        "availability": "native",
        "responses": observed["responses"],
        "input_tokens": observed.get("tokens", {}).get("input"),
        "context_tokens": observed.get("latest_context_tokens"),
    }


def _level(usage: Mapping[str, Any], budget: Mapping[str, Mapping[str, int]]) -> str:
    if usage.get("availability") != "native":
        return "unavailable"
    for level in ("hard", "advisory"):
        if any(
            usage.get(metric) is not None and usage[metric] >= budget[level][metric]
            for metric in _METRICS
        ):
            return level
    return "ok"


def _fresh_window_prompt(
    session_id: int | None, thread_id: str | None, task_slug: str | None = None
) -> str:
    identity = f"; previous host thread {thread_id}" if thread_id else ""
    checkpoint = f"session #{session_id}" if session_id is not None else "the latest handoff"
    guidance = (
        f"Continue TAUSIK from checkpoint {checkpoint}{identity}. "
        "Run /start, load the handoff and active task in package mode, and continue from the "
        "first incomplete plan step. Do not reread the full host history."
    )
    if not task_slug:
        return guidance
    return f"Resume: .tausik/tausik task start {task_slug} --package. {guidance}"


def _bound_task_lease(
    svc: Any, *, session_id: int, host: str | None, thread_id: str | None
) -> dict[str, Any] | None:
    if not host or not thread_id:
        return None
    from execution_lease_package import normalize_project_identity

    leases = svc.be._q(
        "SELECT * FROM execution_leases WHERE session_id=? AND project_identity=? "
        "AND host_instance=? AND thread_id=? AND revoked_at IS NULL AND task_slug IS NOT NULL "
        "ORDER BY id DESC",
        (
            session_id,
            normalize_project_identity(os.path.dirname(svc.tausik_dir())),
            host.casefold(),
            thread_id.strip(),
        ),
    )
    if len(leases) > 1:
        raise ServiceError("IDENTITY_AMBIGUOUS: multiple task-bound leases for host session")
    if not leases:
        return None
    return cast(dict[str, Any], leases[0])


def enforce_hard_ceiling(svc: Any, *, host: str, thread_id: str) -> dict[str, Any] | None:
    """Checkpoint/revoke an over-budget thread before any lease-protected mutation."""

    config = load_config(svc.tausik_dir())
    observed = _usage(os.path.dirname(svc.tausik_dir()), host, thread_id)
    if _level(observed, _budget(config)) != "hard":
        return None
    return open_session(svc, host=host, thread_id=thread_id, usage=observed)


def open_session(
    svc: Any,
    *,
    host: str | None = None,
    thread_id: str | None = None,
    usage: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Open/reuse a host-bound session and enforce the context budget."""
    if host is None and thread_id is None:
        host, thread_id = native_identity()
    if bool(host) != bool(thread_id):
        raise ServiceError("host and thread_id must be supplied together")
    config = load_config(svc.tausik_dir())
    budget = _budget(config)
    project_dir = os.path.dirname(svc.tausik_dir())
    observed = dict(usage) if usage is not None else _usage(project_dir, host, thread_id)
    level = _level(observed, budget)
    existing = svc.be.session_current(thread_id) if thread_id else svc.be.session_current()
    legacy = svc.be.session_current() if thread_id and existing is None else None
    prompt: str | None
    if legacy and legacy.get("host_session_id") is not None:
        legacy = None
    if level == "hard":
        checkpoint_session = existing or legacy
        if checkpoint_session is None and thread_id:
            recent = svc.be._q1(
                "SELECT * FROM sessions WHERE host_session_id=? ORDER BY id DESC LIMIT 1",
                (thread_id,),
            )
            prior_handoff = str((recent or {}).get("handoff") or "")
            if recent is not None and recent.get("ended_at") and '"level": "hard"' in prior_handoff:
                prompt = _fresh_window_prompt(recent["id"], thread_id)
                return {
                    "session": recent,
                    "host_context": {
                        "host": host,
                        "reopened": False,
                        "fresh_context": False,
                        "level": level,
                        "usage": observed,
                        "budget": budget,
                        "allow_continue": False,
                        "checkpoint_saved": False,
                        "fresh_window_prompt": prompt,
                    },
                }
        if checkpoint_session is None:
            svc.session_start(thread_id)
            checkpoint_session = svc.be.session_current(thread_id)
        assert checkpoint_session is not None
        bound_lease = _bound_task_lease(
            svc,
            session_id=int(checkpoint_session["id"]),
            host=host,
            thread_id=thread_id,
        )
        task_slug = str(bound_lease["task_slug"]) if bound_lease else None
        prompt = _fresh_window_prompt(checkpoint_session["id"], thread_id, task_slug)
        checkpoint_saved = False
        marker = {
            "level": level,
            "host": host,
            "thread_id": thread_id,
            "usage": observed,
            "fresh_window_prompt": prompt,
        }
        if '"level": "hard"' not in str(checkpoint_session.get("handoff") or ""):
            svc.session_handoff(
                {
                    "warnings": ["Host context budget reached; continue in a fresh host window."],
                    "next_steps": [prompt],
                    "host_context_budget": marker,
                },
                host_session_id=thread_id if checkpoint_session.get("host_session_id") else None,
            )
            checkpoint_saved = True
        if bound_lease and task_slug:
            resume_command = f".tausik/tausik task start {task_slug} --package"
            svc.be.meta_set(f"host_context_hard_lease:{bound_lease['id']}", resume_command)
        if checkpoint_session.get("host_session_id"):
            svc.be.session_end(
                checkpoint_session["id"], "Host context hard ceiling; checkpoint only"
            )
            checkpoint_session = svc.be.session_last_handoff(checkpoint_session["id"])
        return {
            "session": checkpoint_session,
            "host_context": {
                "host": host,
                "reopened": False,
                "fresh_context": False,
                "level": level,
                "usage": observed,
                "budget": budget,
                "allow_continue": False,
                "checkpoint_saved": checkpoint_saved,
                "fresh_window_prompt": prompt,
            },
        }
    svc.session_start(thread_id)
    current = svc.be.session_current(thread_id) if thread_id else svc.be.session_current()
    assert current is not None
    checkpoint_saved = False
    prompt = None
    if level in {"advisory", "hard"}:
        prompt = _fresh_window_prompt(current["id"], thread_id)
        marker = {
            "level": level,
            "host": host,
            "thread_id": thread_id,
            "usage": observed,
            "fresh_window_prompt": prompt,
        }
        previous = current.get("handoff") or ""
        if thread_id and thread_id not in str(previous):
            svc.session_handoff(
                {
                    "warnings": ["Host context budget reached; continue in a fresh host window."],
                    "next_steps": [prompt],
                    "host_context_budget": marker,
                },
                host_session_id=thread_id,
            )
            checkpoint_saved = True
            current = svc.be.session_current(thread_id) if thread_id else svc.be.session_current()
    return {
        "session": current,
        "host_context": {
            "host": host,
            "reopened": existing is not None,
            "fresh_context": existing is None and level == "ok",
            "level": level,
            "usage": observed,
            "budget": budget,
            "allow_continue": level != "hard",
            "checkpoint_saved": checkpoint_saved,
            "fresh_window_prompt": prompt,
        },
    }
