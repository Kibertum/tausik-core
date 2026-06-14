"""Orchestrator-worker delegation state — `tausik task delegate` (v15-ow-delegate-cli).

The main session (Opus coordinator) marks a complexity<=medium task as delegable
to a worker sub-agent: TAUSIK records the intent (recommended model + parent
session) in the `meta` kv table — no schema migration, fully additive. The agent
performs the actual Agent-tool spawn; the worker/hook reads the record back.
Complex tasks are refused — they stay with the coordinator.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError, utcnow_iso

if TYPE_CHECKING:
    from project_backend import SQLiteBackend

_DELEGATION_PREFIX = "delegation:"
_DEFAULT_MODEL = ("claude-sonnet-4-6", "Sonnet 4.6")


def _delegation_key(slug: str) -> str:
    return f"{_DELEGATION_PREFIX}{slug}"


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

    def task_delegate(self, slug: str) -> str:
        """Mark a complexity<=medium task delegated to a worker sub-agent."""
        task = self.be.task_get(slug)
        if task is None:
            raise ServiceError(f"Task '{slug}' not found")
        if task.get("status") == "done":
            raise ServiceError(f"Task '{slug}' is done — nothing to delegate")
        if task.get("complexity") == "complex":
            raise ServiceError(
                f"Task '{slug}' is complex — keep it with the Opus coordinator. "
                f"Only complexity<=medium tasks delegate to a worker sub-agent."
            )
        existing = self.task_delegation(slug)
        if existing:
            return (
                f"Task '{slug}' already delegated (model={existing.get('display')}, "
                f"parent session #{existing.get('parent_session') or 'unknown'}). No-op."
            )
        model, display = self._recommended_model(task.get("complexity"))
        sess = self.be.session_current()
        parent = sess.get("id") if sess else None
        record = {
            "model": model,
            "display": display,
            "parent_session": parent,
            "delegated_at": utcnow_iso(),
        }
        self.be.meta_set(_delegation_key(slug), json.dumps(record))
        return (
            f"Task '{slug}' delegated to a worker sub-agent. Spawn it via the Agent "
            f"tool with model={display} ({model}); the worker runs "
            f"`tausik task start {slug}`, honours its scope, and reports back via "
            f"task_log. Parent session #{parent}."
        )

    def task_handoff(self, slug: str) -> dict[str, Any]:
        """Build the worker handoff contract for a task (goal/AC/scope/model/skills)."""
        task = self.be.task_get(slug)
        if task is None:
            raise ServiceError(f"Task '{slug}' not found")
        from ow_handoff import build_handoff_contract

        return build_handoff_contract(task, self.task_delegation(slug))

    def task_undelegate(self, slug: str) -> str:
        """Clear a task's delegation record (idempotent)."""
        if not self.task_delegation(slug):
            return f"Task '{slug}' is not delegated."
        self.be.meta_delete(_delegation_key(slug))
        return f"Task '{slug}' delegation cleared."

    @staticmethod
    def _recommended_model(complexity: str | None) -> tuple[str, str]:
        try:
            from model_routing_matrix import suggest_model

            spec = suggest_model(complexity)
            return (
                spec.get("model") or _DEFAULT_MODEL[0],
                spec.get("display") or _DEFAULT_MODEL[1],
            )
        except Exception:  # noqa: BLE001 — routing is advisory; fall back to a safe default
            return _DEFAULT_MODEL
