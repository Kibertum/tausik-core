"""TAUSIK TaskMixin — task lifecycle with strict workflow enforcement."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from tausik_utils import (
    ServiceError,
    utcnow_iso,
    validate_content,
    validate_length,
    validate_slug,
)
from project_types import (
    COMPLEXITY_SP,
    VALID_TASK_STATUSES,
)
from service_cascade import CascadeMixin
from service_gates import GatesMixin
from service_recording import check_session_capacity, record_call_actual

if TYPE_CHECKING:
    from project_backend import SQLiteBackend

_LIFECYCLE_STATUSES = frozenset({"done", "active", "blocked", "review"})


_MISSING = object()


from service_validation import load_stacks as _load_stacks  # noqa: E402,F401
from service_validation import update_enums as _update_enums  # noqa: E402,F401
from service_recording import apply_force_capacity_audit as _apply_force_audit  # noqa: E402,F401


class TaskMixin(GatesMixin, CascadeMixin):
    """Task lifecycle with strict workflow enforcement."""

    be: SQLiteBackend

    def task_add(
        self,
        story_slug: str | None,
        slug: str,
        title: str,
        stack: str | None = None,
        complexity: str | None = None,
        goal: str | None = None,
        role: str | None = None,
        defect_of: str | None = None,
        call_budget: int | None = None,
        tier: str | None = None,
    ) -> str:
        from tausik_utils import safe_single_line

        if story_slug:
            self._require_story(story_slug)
        validate_slug(slug)
        validate_length("title", title)
        title = safe_single_line(title) or title
        from service_validation import validate_task_add_inputs

        validate_task_add_inputs(stack, complexity, call_budget, tier)
        if defect_of:
            self._require_task(defect_of)
        validate_content("goal", goal)
        score = COMPLEXITY_SP.get(complexity, 1) if complexity else 1
        self.be.task_add(
            story_slug, slug, title, stack, complexity, score, goal, role, defect_of
        )
        notice = ""
        if call_budget is not None:
            self.be.task_set_call_budget(slug, call_budget)
            if tier is not None:
                notice = f"\nNote: --tier '{tier}' overridden by --call-budget."
        elif tier is not None:
            self.be.task_update(slug, tier=tier)
        msg = f"Task '{slug}' created."
        if not goal or not goal.strip():
            msg += "\n⚠ QG-0 warning: missing goal."
        return msg + notice

    def task_list(
        self,
        status: str | None = None,
        story: str | None = None,
        epic: str | None = None,
        role: str | None = None,
        stack: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        if status:
            for s in status.split(","):
                if s not in VALID_TASK_STATUSES:
                    raise ServiceError(
                        f"Invalid status '{s}'. Valid: {', '.join(sorted(VALID_TASK_STATUSES))}"
                    )
        return self.be.task_list(status, story, epic, role, stack, limit=limit)

    def task_show(self, slug: str) -> dict[str, Any]:
        task = self.be.task_get_full(slug)
        if not task:
            raise ServiceError(f"Task '{slug}' not found")
        task["decisions"] = self.be.decisions_for_task(slug)
        return task

    def task_start(
        self, slug: str, _internal_force: bool = False, force: bool = False
    ) -> str:
        task = self._require_task(slug)
        if task["status"] == "done":
            raise ServiceError(f"Task '{slug}' is already done")
        if task["status"] == "active":
            return f"Task '{slug}' is already active."
        qg0_warnings: list[str] = []
        capacity_audit = ""
        if not _internal_force:
            qg0_warnings = self._check_qg0_start(slug, task)
            if force:
                capacity_audit = _apply_force_audit(self.be, slug, task)
            else:
                check_session_capacity(self.be, slug, task)
        updates: dict[str, Any] = {
            "status": "active",
            "attempts": task.get("attempts", 0) + 1,
        }
        if not task.get("started_at"):
            updates["started_at"] = utcnow_iso()
        self.be.begin_tx()
        try:
            self.be.task_update(slug, **updates)
            self._cascade_start(slug)
            self.be.commit_tx()
        except Exception:
            self.be.rollback_tx()
            raise
        msgs = [f"Task '{slug}' started (attempt #{updates['attempts']})."]
        msgs.extend(qg0_warnings)
        if capacity_audit:
            msgs.append(f"⚠ {capacity_audit}")
        return "\n".join(msgs) if len(msgs) > 1 else msgs[0]

    def task_done(
        self,
        slug: str,
        relevant_files: list[str] | None = None,
        ac_verified: bool = False,
        no_knowledge: bool = False,
        evidence: str | None = None,
        progress_fn: Any | None = None,
    ) -> str:
        report = self._task_done_report(
            slug,
            relevant_files=relevant_files,
            ac_verified=ac_verified,
            no_knowledge=no_knowledge,
            evidence=evidence,
            progress_fn=progress_fn,
        )
        if not report.get("ok"):
            failures = report.get("blocking_failures") or []
            first = failures[0] if failures else {}
            msg = first.get("message") or "task_done failed"
            raise ServiceError(msg)
        message = report.get("message")
        if isinstance(message, str) and message.strip():
            return message
        return f"Task '{slug}' completed."

    def task_done_v2(
        self,
        slug: str,
        relevant_files: list[str] | None = None,
        ac_verified: bool = False,
        no_knowledge: bool = False,
        evidence: str | None = None,
        progress_fn: Any | None = None,
    ) -> dict[str, Any]:
        return self._task_done_report(
            slug,
            relevant_files=relevant_files,
            ac_verified=ac_verified,
            no_knowledge=no_knowledge,
            evidence=evidence,
            progress_fn=progress_fn,
        )

    def _task_done_report(
        self,
        slug: str,
        *,
        relevant_files: list[str] | None,
        ac_verified: bool,
        no_knowledge: bool,
        evidence: str | None,
        progress_fn: Any | None = None,
    ) -> dict[str, Any]:
        report: dict[str, Any] = {
            "ok": False,
            "slug": slug,
            "plan_complete": False,
            "ac_verified": False,
            "gates_passed": False,
            "gates": [],
            "blocking_failures": [],
            "warnings": [],
            "cache_status": None,
            "message": "",
        }
        task = self._require_task(slug)
        if task["status"] == "done":
            raise ServiceError(f"Task '{slug}' is already done")
        if evidence:
            self.task_log(slug, evidence)  # one call instead of log+done (v1.3 DX)
            task = self._require_task(slug)
        try:
            ac_warnings = self._verify_ac(slug, task, ac_verified)
            report["ac_verified"] = True
        except ServiceError as e:
            report["blocking_failures"].append({"stage": "ac", "message": str(e)})
            return report
        try:
            self._verify_plan_complete(slug, task)
            report["plan_complete"] = True
        except ServiceError as e:
            report["blocking_failures"].append({"stage": "plan", "message": str(e)})
            return report
        gate_report = self._run_quality_gates_report(
            slug, relevant_files, progress_fn=progress_fn
        )
        report["gates"] = gate_report.get("results", [])
        report["cache_status"] = gate_report.get("cache_status")
        report["gates_passed"] = bool(gate_report.get("passed"))
        if not gate_report.get("passed"):
            failures = gate_report.get("blocking_failures", [])
            report["blocking_failures"] = [
                {
                    "stage": "gates",
                    "gate": f.get("gate"),
                    "files": f.get("files") or [],
                    "output": f.get("output"),
                    "remediation": f.get("remediation"),
                    "message": (
                        f"QG-2 Implementation Gate failed: {f.get('gate')} — "
                        f"{(f.get('output') or '')[:180]}"
                    ),
                }
                for f in failures
            ]
            return report

        checklist_warning = self._check_verification_checklist(slug, task)
        # SENAR Core Rule 7: defect tasks must document root cause
        root_cause_warning = ""
        if task.get("defect_of"):
            notes_lower = (task.get("notes") or "").lower()
            _rc_kw = (
                "root cause",
                "причина",
                "cause:",
                "caused by",
                "из-за",
                "потому что",
                "because",
            )
            if not any(kw in notes_lower for kw in _rc_kw):
                root_cause_warning = (
                    f"WARNING: Defect task '{slug}' (defect_of={task['defect_of']}) "
                    f"has no root cause documented. Log it: .tausik/tausik task log {slug} "
                    f'"Root cause: ..."'
                )

        # Knowledge capture warning (SENAR Rule 8).
        # v1.3.4 (med-batch-2-qg #5): --no-knowledge refused for complex
        # /defect tasks (SENAR Rule 8 upgrades from warning to refusal —
        # those are the cases where knowledge capture matters most).
        _kw = ("dead end", "decided", "decision", "memory", "pattern", "gotcha")
        notes = task.get("notes") or ""
        is_complex = (task.get("complexity") or "").lower() == "complex"
        is_defect = bool(task.get("defect_of"))
        if no_knowledge and (is_complex or is_defect):
            reason = "complex" if is_complex else "defect"
            report["blocking_failures"].append(
                {
                    "stage": "knowledge",
                    "message": (
                        f"--no-knowledge refused for {reason} task '{slug}'. "
                        f"SENAR Rule 8 requires knowledge capture. Either capture "
                        f"first (memory_add / decide / dead-end) and re-run without "
                        f"the flag, or downgrade complexity if truly trivial."
                    ),
                }
            )
            return report
        knowledge_warning = ""
        if not any(kw in notes.lower() for kw in _kw) and not no_knowledge:
            if (
                self.be.memory_count_for_task(slug) == 0
                and self.be.decision_count_for_task(slug) == 0
            ):
                knowledge_warning = "NOTE: No knowledge captured for this task (no memories, decisions, or dead ends). Use --no-knowledge to confirm none needed."
        if no_knowledge:
            self.be.event_add(
                "task",
                slug,
                "knowledge_confirmed_none",
                "Explicitly confirmed: no knowledge to capture",
            )
        updates: dict[str, Any] = {"status": "done", "completed_at": utcnow_iso()}
        if relevant_files:
            updates["relevant_files"] = json.dumps(relevant_files)
        # Atomic: task update + cascade + audit in one transaction
        self.be.begin_tx()
        try:
            self.be.task_update(slug, **updates)
            msgs = [f"Task '{slug}' completed."]
            msgs.extend(ac_warnings)
            if knowledge_warning:
                msgs.append(knowledge_warning)
                report["warnings"].append(knowledge_warning)
            if checklist_warning:
                msgs.append(checklist_warning)
                report["warnings"].append(checklist_warning)
            if root_cause_warning:
                msgs.append(root_cause_warning)
                report["warnings"].append(root_cause_warning)
            budget_warning = record_call_actual(self.be, slug, task)
            if budget_warning:
                msgs.append(budget_warning)
                report["warnings"].append(budget_warning)
            msgs.extend(self._cascade_done(slug))
            self.be.commit_tx()
        except Exception:
            self.be.rollback_tx()
            raise
        report["ok"] = True
        report["message"] = " ".join(msgs)
        return report

    def task_block(self, slug: str, reason: str | None = None) -> str:
        task = self._require_task(slug)
        if task["status"] == "done":
            raise ServiceError(f"Cannot block a done task '{slug}'")

        updates: dict[str, Any] = {"status": "blocked", "blocked_at": utcnow_iso()}
        self.be.task_update(slug, **updates)
        if reason:
            self.be.task_append_notes(slug, f"BLOCKED: {reason}")
        return f"Task '{slug}' blocked."

    def task_unblock(self, slug: str, *, force: bool = False) -> str:
        task = self._require_task(slug)
        if task["status"] != "blocked":
            raise ServiceError(
                f"Task '{slug}' is not blocked (status: {task['status']})"
            )
        # v1.3.4 (med-batch-2-qg #4): unblocking returns the task to active
        # state — same risk as task_start. Without this check, the agent
        # could block-then-unblock to bypass session capacity limits and
        # keep coding past the 180-min ACTIVE-time threshold (SENAR Rule 9.2).
        if not force:
            check_session_capacity(self.be, slug, task)
        self.be.task_update(slug, status="active", blocked_at=None)
        return f"Task '{slug}' unblocked."

    def task_review(self, slug: str) -> str:
        task = self._require_task(slug)
        if task["status"] == "done":
            raise ServiceError(f"Cannot move '{slug}' to review — task is already done")
        self.be.task_update(slug, status="review")
        return f"Task '{slug}' moved to review."

    def task_update(self, slug: str, **fields: Any) -> str:
        self._require_task(slug)
        if fields.get("status") in _LIFECYCLE_STATUSES:
            raise ServiceError(
                f"status='{fields['status']}' must use lifecycle method "
                f"(task_done/start/block/review) — would bypass QG-2."
            )
        for name, valid in _update_enums():
            v = fields.get(name)
            if v and v not in valid:
                raise ServiceError(f"Invalid {name} '{v}'. Valid: {sorted(valid)}")
        cb = fields.pop("call_budget", _MISSING)
        notice = ""
        if cb is not _MISSING and cb is not None:
            if cb < 0:
                raise ServiceError(f"Invalid call_budget '{cb}'; must be >=0")
            self.be.task_set_call_budget(slug, cb)
            tier = fields.pop("tier", None)
            if tier is not None:
                notice = f"\nNote: tier '{tier}' overridden by call_budget."
            if not fields:
                return f"Task '{slug}' updated.{notice}"
        from tausik_utils import safe_single_line

        for f in ("title", "goal"):
            if fields.get(f) is not None:
                fields[f] = safe_single_line(fields[f]) or fields[f]
        self.be.task_update(slug, **fields)
        return f"Task '{slug}' updated.{notice}"

    def task_delete(self, slug: str) -> str:
        self._require_task(slug)
        self.be.task_delete(slug)
        return f"Task '{slug}' deleted."

    def task_plan(self, slug: str, steps: list[str]) -> str:
        if not steps:
            raise ServiceError("Plan must have at least one step")
        for i, s in enumerate(steps, 1):
            if not s or not s.strip():
                raise ServiceError(f"Plan step {i} is empty")
        self._require_task(slug)
        plan_data = [{"step": s, "done": False} for s in steps]
        self.be.task_update(slug, plan=json.dumps(plan_data))
        return f"Plan set for '{slug}' ({len(steps)} steps)."

    def task_step(self, slug: str, step_num: int) -> str:
        task = self._require_task(slug)
        if not task.get("plan"):
            raise ServiceError(f"Task '{slug}' has no plan")
        try:
            steps = json.loads(task["plan"])
        except (json.JSONDecodeError, TypeError) as e:
            raise ServiceError(f"Corrupted plan data for task '{slug}': {e}")
        if step_num < 1 or step_num > len(steps):
            raise ServiceError(f"Step {step_num} out of range (1-{len(steps)})")
        steps[step_num - 1]["done"] = True
        self.be.task_update(slug, plan=json.dumps(steps))
        done_count = sum(1 for s in steps if s.get("done"))
        return f"Step {step_num} done ({done_count}/{len(steps)})."

    # task_quick + task_next + task_claim + task_unclaim live in
    # service_task_team.TaskTeamMixin for filesize compliance — they're
    # picked up via the multi-mixin composition in project_service.

    def task_log(
        self,
        slug: str,
        message: str,
        phase: str | None = None,
        diff_stats: str | None = None,
    ) -> str:
        """Append a timestamped log entry to task notes + task_logs table."""
        task = self._require_task(slug)
        validate_content("log message", message)
        # Dual write: notes (backward compat) + task_logs table (structured)
        self.be.task_append_notes(slug, message)
        # Auto-detect phase from task status if not provided
        if phase is None:
            status_to_phase = {
                "planning": "planning",
                "active": "implementation",
                "review": "review",
                "done": "done",
            }
            phase = status_to_phase.get(task["status"])
        self.be.task_log_add(slug, message, phase=phase, diff_stats=diff_stats)
        return f"Logged to '{slug}'."

    def task_logs(self, slug: str, phase: str | None = None) -> list[dict]:
        """Return structured logs for a task."""
        return self.be.task_log_list(slug, phase=phase)

    def team_status(self) -> list[dict[str, Any]]:
        """Return non-done tasks grouped by agent (claimed_by)."""
        tasks = self.be.task_list(status="planning,active,blocked,review")
        agents: dict[str, list[dict[str, Any]]] = {}
        for t in tasks:
            agent = t.get("claimed_by") or "(unclaimed)"
            agents.setdefault(agent, []).append(t)
        return [{"agent": a, "tasks": ts} for a, ts in agents.items()]

    def task_move(self, slug: str, new_story_slug: str) -> str:
        self._require_task(slug)
        story = self._require_story(new_story_slug)
        self.be.task_update(slug, story_id=story["id"])
        return f"Task '{slug}' moved to story '{new_story_slug}'."

    # _cascade_start, _cascade_done -> inherited from CascadeMixin (service_cascade.py)
