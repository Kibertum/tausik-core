"""Orchestrator-worker delegation state — `tausik task delegate` (v15-ow-delegate-cli).

The main coordinator session marks a complexity<=medium task as delegable
to a worker sub-agent: TAUSIK records the intent (recommended model + parent
session) in the `meta` kv table — no schema migration, fully additive. The agent
performs the actual Agent-tool spawn; the worker/hook reads the record back.
Complex tasks are refused — they stay with the coordinator.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError, utcnow_iso

if TYPE_CHECKING:
    from project_backend import SQLiteBackend

_DELEGATION_PREFIX = "delegation:"
_DEFAULT_MODEL = ("claude-sonnet-4-6", "Sonnet 4.6")


def _delegation_key(slug: str) -> str:
    return f"{_DELEGATION_PREFIX}{slug}"


def _backend_tausik_dir(be: Any) -> str | None:
    """Resolve telemetry beside the backend, never beside the process cwd."""
    db_path = getattr(be, "db_path", None)
    if not isinstance(db_path, str) or not db_path:
        return None
    return os.path.dirname(os.path.abspath(db_path))


def start_recognition_message(be: Any, slug: str, complexity: str | None) -> str | None:
    """task_start recognition line: worker-mode notice for a delegated task, else
    the model-recommendation banner (or None). All best-effort — never raises."""
    try:
        raw = be.meta_get(_delegation_key(slug))
    except Exception:  # noqa: BLE001 — recognition is best-effort; fall back to banner
        raw = None
    if raw:
        try:
            deleg = json.loads(raw)
        except (TypeError, ValueError):
            deleg = None
        if isinstance(deleg, dict):
            if not deleg.get("applied"):
                deleg["applied"] = True
                try:
                    be.meta_set(_delegation_key(slug), json.dumps(deleg))
                    from model_routing_adherence import record_route_outcome

                    tausik_dir = _backend_tausik_dir(be)
                    if tausik_dir:
                        record_route_outcome(tausik_dir, slug, deleg, "applied")
                except Exception:  # noqa: BLE001,S110 — telemetry cannot block task start
                    pass
            return worker_mode_notice(slug, deleg)
    try:
        from project_config import is_task_start_model_banner_enabled

        if is_task_start_model_banner_enabled():
            from agent_model_source import resolve
            from model_routing import format_task_start_banner
            from skill_profile_detect import detect_ide

            host = detect_ide()
            active = resolve(ide=host)["model_id"] if host else None
            return format_task_start_banner(complexity, active_model=active)
    except Exception:  # noqa: BLE001,S110 — banner is informational, never block start
        pass
    return None


def resume_recognition_message(be: Any, slug: str, complexity: str | None) -> str | None:
    """Recognize a worker that resumes the task activated by its coordinator."""
    try:
        if not be.meta_get(_delegation_key(slug)):
            return None
    except Exception:  # noqa: BLE001 — recognition is best-effort
        return None
    return start_recognition_message(be, slug, complexity)


def record_task_recommendation(be: Any, slug: str, complexity: str | None) -> None:
    """Persist the active task route without making task start depend on telemetry."""
    try:
        from model_routing_session import record_active_task_recommendation
        from agent_model_source import resolve
        from skill_profile_detect import detect_ide

        tausik_dir = _backend_tausik_dir(be)
        if not tausik_dir:
            return
        host = detect_ide()
        active = resolve(ide=host)["model_id"] if host else None
        recommendation = record_active_task_recommendation(
            tausik_dir,
            slug,
            complexity,
            host=host,
            active_model=active,
        )
        if recommendation:
            from model_routing_adherence import record_route_outcome

            record_route_outcome(tausik_dir, slug, recommendation, "recommended")
    except Exception:  # noqa: BLE001,S110 — route telemetry never blocks task start
        pass


def clear_delegation_state(be: Any, slug: str) -> None:
    """Drop delegation + worker-summary meta for a slug (best-effort) so a reused
    slug can't inherit stale orchestrator-worker state."""
    for key in (_delegation_key(slug), f"worker_summary:{slug}"):
        try:
            be.meta_delete(key)
        except Exception:  # noqa: BLE001,S110 — best-effort cleanup, never block the caller
            pass


def worker_mode_notice(slug: str, delegation: dict[str, Any]) -> str:
    """In-session worker recognition banner for a delegated task_start.

    Surfaces the worker operating contract (trimmed skills + hard-gated scope +
    report-back). Runtime skill-trimming is not a mid-session operation, so this
    announces the contract the worker honours rather than re-bootstrapping.
    """
    from ow_handoff import WORKER_SKILLS

    model = delegation.get("display") or delegation.get("model") or "recommended"
    return (
        f"⚙ Worker mode — delegated task '{slug}' (model {model}). "
        f"Operating contract: skills [{', '.join(WORKER_SKILLS)}]; scope is "
        f"hard-gated (edits outside the task's scope are blocked); report back via "
        f'`tausik task summary-back {slug} "<summary>"` when done.'
    )


class DelegateMixin:
    """task delegate / undelegate + delegation read. Composed into ProjectService."""

    be: SQLiteBackend

    def task_delegation(self, slug: str) -> dict[str, Any] | None:
        """Return the delegation record for a task, or None if not delegated."""
        raw = self.be.meta_get(_delegation_key(slug))
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except (TypeError, ValueError):
            return None

    def task_delegate(
        self,
        slug: str,
        *,
        startup_work: int | None = None,
        remaining_work: int | None = None,
    ) -> str:
        """Mark a bounded task delegated to a worker sub-agent.

        ``startup_work`` and ``remaining_work`` are optional estimates in the
        same caller-defined unit. They deliberately do not borrow ``call_budget``:
        a usage ceiling is not evidence of work remaining.
        """
        task = self.be.task_get(slug)
        if task is None:
            raise ServiceError(f"Task '{slug}' not found")
        if task.get("status") == "done":
            raise ServiceError(f"Task '{slug}' is done — nothing to delegate")
        for active in self.be.task_list(status="active"):
            active_delegation = self.task_delegation(active["slug"])
            if active_delegation and active_delegation.get("applied"):
                raise ServiceError(
                    f"Worker task '{active['slug']}' is already active — nested or "
                    "parallel delegation is disabled (max depth 1)."
                )
        route = self._recommended_route(task.get("complexity"))
        if task.get("complexity") == "complex":
            self._record_route(slug, route, "rejected")
            raise ServiceError(
                f"Task '{slug}' is complex — keep it with the coordinator. "
                f"Only complexity<=medium tasks delegate to a worker sub-agent."
            )
        existing = self.task_delegation(slug)
        if existing:
            return (
                f"Task '{slug}' already delegated (model={existing.get('display')}, "
                f"parent session #{existing.get('parent_session') or 'unknown'}). No-op."
            )
        if route["capability"] != "spawn_subagent":
            self._record_route(slug, route, "unavailable")
            raise ServiceError(
                f"Task '{slug}' route is advisory on host {route['host'] or 'unknown'}; "
                "TAUSIK did not claim or apply a worker model switch."
            )
        estimate = self._worker_estimate(startup_work, remaining_work)
        if estimate and estimate["startup_work"] > estimate["remaining_work"]:
            self._record_route(slug, route, "rejected")
            raise ServiceError(
                "Worker startup refused: startup work "
                f"{estimate['startup_work']} exceeds bounded remaining work "
                f"{estimate['remaining_work']}. Continue in the coordinator."
            )
        model, display = route["model"], route["display"]
        sess = self.be.session_current()
        parent = sess.get("id") if sess else None
        record = {
            "model": model,
            "display": display,
            "parent_session": parent,
            "delegated_at": utcnow_iso(),
            "family": route["family"],
            "host": route["host"],
            "reasoning_effort": route["reasoning_effort"],
            "speed_mode": route["speed_mode"],
            "capability": route["capability"],
            "applied": False,
            "max_delegation_depth": 1,
            "route_reason": route.get("route_reason"),
            "escalation_reason": route.get("escalation_reason"),
            "work_estimate": estimate,
        }
        self.be.meta_set(_delegation_key(slug), json.dumps(record))
        self._record_route(slug, route, "selected")
        return (
            f"Task '{slug}' delegated to a worker sub-agent. Spawn it via the Agent "
            f"tool with model={display} ({model}), reasoning={route['reasoning_effort']}, "
            f"speed={route['speed_mode']}; the worker runs "
            f"`tausik task start {slug}`, honours its scope, and reports back via "
            f"task_log. Parent session #{parent}."
        )

    def task_handoff(self, slug: str) -> dict[str, Any]:
        """Build the worker handoff contract for a DELEGATED task."""
        task = self.be.task_get(slug)
        if task is None:
            raise ServiceError(f"Task '{slug}' not found")
        delegation = self.task_delegation(slug)
        if delegation is None:
            raise ServiceError(
                f"Task '{slug}' is not delegated — run `tausik task delegate {slug}` "
                f"first (a handoff contract has no model without a delegation)."
            )
        from ow_handoff import build_handoff_contract

        return build_handoff_contract(task, delegation)

    def task_summary_back(
        self,
        slug: str,
        summary: str,
        *,
        changed: str | None = None,
        gates: str | None = None,
        ac_evidence: str | None = None,
        follow_ups: str | None = None,
    ) -> str:
        """Worker → orchestrator: persist a structured completion summary.

        Stored in meta (worker_summary:<slug>) for transcript-free retrieval AND
        appended to the task log so the orchestrator picks it up via `task show`.
        """
        if self.be.task_get(slug) is None:
            raise ServiceError(f"Task '{slug}' not found")
        record = {
            "summary": summary,
            "changed": changed or "",
            "gates": gates or "",
            "ac_evidence": ac_evidence or "",
            "follow_ups": follow_ups or "",
            "at": utcnow_iso(),
        }
        self.be.meta_set(f"worker_summary:{slug}", json.dumps(record))
        line = f"[worker-summary] {summary}"
        if gates:
            line += f" | gates: {gates}"
        if changed:
            line += f" | changed: {changed}"
        self.task_log(slug, line, phase="review")  # type: ignore[attr-defined]
        return (
            f"Worker summary recorded for '{slug}'. The orchestrator can read it "
            f"via `tausik task show {slug}` without the worker transcript."
        )

    def task_worker_summary(self, slug: str) -> dict[str, Any] | None:
        """Read the worker's structured summary for a task, or None."""
        raw = self.be.meta_get(f"worker_summary:{slug}")
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except (TypeError, ValueError):
            return None

    def task_undelegate(self, slug: str) -> str:
        """Clear a task's delegation record (idempotent)."""
        if not self.task_delegation(slug):
            return f"Task '{slug}' is not delegated."
        self.be.meta_delete(_delegation_key(slug))
        return f"Task '{slug}' delegation cleared."

    @staticmethod
    def _worker_estimate(
        startup_work: int | None, remaining_work: int | None
    ) -> dict[str, int] | None:
        """Validate paired work estimates without treating a budget as work."""
        if startup_work is None and remaining_work is None:
            return None
        if startup_work is None or remaining_work is None:
            raise ServiceError(
                "Worker work estimates require both startup_work and remaining_work."
            )
        if (
            isinstance(startup_work, bool)
            or isinstance(remaining_work, bool)
            or not isinstance(startup_work, int)
            or not isinstance(remaining_work, int)
            or startup_work < 0
            or remaining_work < 0
        ):
            raise ServiceError(
                "Worker work estimates must be non-negative integers in the same unit."
            )
        return {"startup_work": startup_work, "remaining_work": remaining_work}

    @staticmethod
    def _recommended_route(complexity: str | None) -> dict[str, Any]:
        try:
            from agent_model_source import AUTO
            from model_route import route_work

            return route_work(complexity, host=AUTO)
        except Exception:  # noqa: BLE001 — routing is advisory; fall back to a safe default
            return {
                "model": _DEFAULT_MODEL[0],
                "display": _DEFAULT_MODEL[1],
                "family": None,
                "host": None,
                "reasoning_effort": "medium",
                "speed_mode": "standard",
                "capability": "advisory",
            }

    def _record_route(self, slug: str, route: dict[str, Any], outcome: str) -> None:
        try:
            from model_routing_adherence import record_route_outcome

            tausik_dir = _backend_tausik_dir(self.be)
            if tausik_dir:
                record_route_outcome(tausik_dir, slug, route, outcome)
        except Exception:  # noqa: BLE001,S110 — telemetry never controls delegation
            pass
