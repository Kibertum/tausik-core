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
            return worker_mode_notice(slug, deleg)
    try:
        from project_config import is_task_start_model_banner_enabled

        if is_task_start_model_banner_enabled():
            from model_routing import format_task_start_banner

            return format_task_start_banner(complexity)
    except Exception:  # noqa: BLE001 — banner is informational, never block start
        pass
    return None


def clear_delegation_state(be: Any, slug: str) -> None:
    """Drop delegation + worker-summary meta for a slug (best-effort) so a reused
    slug can't inherit stale orchestrator-worker state."""
    for key in (_delegation_key(slug), f"worker_summary:{slug}"):
        try:
            be.meta_delete(key)
        except Exception:  # noqa: BLE001 — best-effort cleanup, never block the caller
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
