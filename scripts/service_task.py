"""TAUSIK TaskMixin — task lifecycle with strict workflow enforcement."""

from __future__ import annotations

import json
import os
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
    VALID_COMPLEXITIES,
    VALID_TASK_STATUSES,
    VALID_TIERS,
    get_valid_stacks,
)
from service_cascade import CascadeMixin
from service_gates import GatesMixin
from service_recording import check_session_capacity, record_call_actual

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


_MISSING = object()


from service_validation import load_stacks as _load_stacks  # noqa: E402,F401
from service_validation import update_enums as _update_enums  # noqa: E402,F401


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
        if story_slug:
            self._require_story(story_slug)
        validate_slug(slug)
        validate_length("title", title)
        if complexity and complexity not in VALID_COMPLEXITIES:
            raise ServiceError(
                f"Invalid complexity '{complexity}', must be one of {sorted(VALID_COMPLEXITIES)}"
            )
        valid_stacks = _load_stacks()
        if stack and stack not in valid_stacks:
            raise ServiceError(
                f"Invalid stack '{stack}'. Valid: {', '.join(sorted(valid_stacks))}"
            )
        if defect_of:
            self._require_task(defect_of)  # parent must exist
        validate_content("goal", goal)
        if call_budget is not None and call_budget < 0:
            raise ServiceError(
                f"Invalid call_budget '{call_budget}'; must be >=0 or omitted"
            )
        if tier is not None and tier not in VALID_TIERS:
            raise ServiceError(
                f"Invalid tier '{tier}'. Valid: {', '.join(sorted(VALID_TIERS))}"
            )
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
            msg += "\n⚠ QG-0 warning: missing goal. Task won't start without goal + acceptance_criteria."
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

    def task_start(self, slug: str, _internal_force: bool = False) -> str:
        task = self._require_task(slug)
        if task["status"] == "done":
            raise ServiceError(f"Task '{slug}' is already done")
        if task["status"] == "active":
            return f"Task '{slug}' is already active."
        # QG-0: Context Gate — delegated to GatesMixin
        qg0_warnings: list[str] = []
        if not _internal_force:
            qg0_warnings = self._check_qg0_start(slug, task)
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
        return "\n".join(msgs) if len(msgs) > 1 else msgs[0]

    def task_done(
        self,
        slug: str,
        relevant_files: list[str] | None = None,
        ac_verified: bool = False,
        no_knowledge: bool = False,
    ) -> str:
        task = self._require_task(slug)
        if task["status"] == "done":
            raise ServiceError(f"Task '{slug}' is already done")
        ac_warnings: list[str] = []
        ac_warnings = self._verify_ac(slug, task, ac_verified)
        self._verify_plan_complete(slug, task)
        self._run_quality_gates(slug, relevant_files)
        checklist_warning = self._check_verification_checklist(slug, task)
        # SENAR Core Rule 7: defect tasks must document root cause
        root_cause_warning = ""
        if task.get("defect_of"):
            notes_lower = (task.get("notes") or "").lower()
            root_cause_keywords = (
                "root cause",
                "причина",
                "cause:",
                "caused by",
                "из-за",
                "потому что",
                "because",
            )
            if not any(kw in notes_lower for kw in root_cause_keywords):
                root_cause_warning = (
                    f"WARNING: Defect task '{slug}' (defect_of={task['defect_of']}) has no root cause "
                    f'documented. Log it: .tausik/tausik task log {slug} "Root cause: ..."'
                )

        # Knowledge capture warning (SENAR Rule 8)
        notes = task.get("notes") or ""
        has_knowledge = any(
            kw in notes.lower()
            for kw in ("dead end", "decided", "decision", "memory", "pattern", "gotcha")
        )
        knowledge_warning = ""
        if not has_knowledge and not no_knowledge:
            mem_cnt = self.be.memory_count_for_task(slug)
            dec_cnt = self.be.decision_count_for_task(slug)
            if mem_cnt == 0 and dec_cnt == 0:
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
            if checklist_warning:
                msgs.append(checklist_warning)
            if root_cause_warning:
                msgs.append(root_cause_warning)
            budget_warning = record_call_actual(self.be, slug, task)
            if budget_warning:
                msgs.append(budget_warning)
            msgs.extend(self._cascade_done(slug))
            self.be.commit_tx()
        except Exception:
            self.be.rollback_tx()
            raise
        return " ".join(msgs)

    def task_block(self, slug: str, reason: str | None = None) -> str:
        task = self._require_task(slug)
        if task["status"] == "done":
            raise ServiceError(f"Cannot block a done task '{slug}'")

        updates: dict[str, Any] = {"status": "blocked", "blocked_at": utcnow_iso()}
        self.be.task_update(slug, **updates)
        if reason:
            self.be.task_append_notes(slug, f"BLOCKED: {reason}")
        return f"Task '{slug}' blocked."

    def task_unblock(self, slug: str) -> str:
        task = self._require_task(slug)
        if task["status"] != "blocked":
            raise ServiceError(
                f"Task '{slug}' is not blocked (status: {task['status']})"
            )
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
        for name, valid in _update_enums():
            v = fields.get(name)
            if v and v not in valid:
                raise ServiceError(
                    f"Invalid {name} '{v}'. Valid: {', '.join(sorted(valid))}"
                )
        cb = fields.pop("call_budget", _MISSING)
        if cb is not _MISSING:
            if cb is not None and cb < 0:
                raise ServiceError(
                    f"Invalid call_budget '{cb}'; must be >=0 or omitted"
                )
            if cb is not None:
                self.be.task_set_call_budget(slug, cb)
                # explicit tier (if any) wins over auto-derived
                if "tier" not in fields:
                    return f"Task '{slug}' updated."
        self.be.task_update(slug, **fields)
        return f"Task '{slug}' updated."

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

    def task_quick(
        self,
        title: str,
        goal: str | None = None,
        role: str | None = None,
        stack: str | None = None,
    ) -> str:
        """Quick-create a task from minimal input (auto-slug, no story required)."""
        from tausik_utils import slugify

        slug = slugify(title)
        if self.be.task_get(slug):
            suffix = os.urandom(3).hex()
            slug = f"{slug[:44]}-{suffix}"
        return self.task_add(None, slug, title, stack=stack, goal=goal, role=role)

    def task_next(self, agent_id: str | None = None) -> dict[str, Any] | None:
        """Pick the next available task: highest-score unclaimed planning task.

        QG-0 is enforced — only tasks with goal + AC can be started.
        Tasks without goal/AC are returned but NOT auto-started.
        """
        task = self.be.task_next_candidate()
        if not task:
            return None
        if agent_id:
            self.task_claim(task["slug"], agent_id)
            # QG-0 enforced: try without force, handle gracefully if gate fails
            try:
                self.task_start(task["slug"])
            except ServiceError:
                task["_qg0_failed"] = (
                    True  # Task claimed but not started — agent must set goal/AC first
                )
            task = self.be.task_get(task["slug"]) or task
        return task

    def task_claim(self, slug: str, agent_id: str) -> str:
        """Claim a task for an agent. Atomic UPDATE prevents race conditions."""
        self._require_task(slug)

        self.be.task_claim(slug, agent_id, utcnow_iso())
        return f"Task '{slug}' claimed by '{agent_id}'."

    def task_unclaim(self, slug: str) -> str:
        self._require_task(slug)
        self.be.task_update(slug, claimed_by=None)
        return f"Task '{slug}' unclaimed."

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
