"""TAUSIK TaskMixin — task lifecycle with strict workflow enforcement."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

from tausik_utils import (
    ServiceError,
    utcnow_iso,
    validate_content,
    validate_length,
    validate_slug,
)
from project_types import COMPLEXITY_SP, VALID_TASK_STATUSES
from service_cascade import CascadeMixin
from service_gates import GatesMixin
from model_pinning import model_start_updates
from service_reasoning import ReasoningMixin
from service_replay import ReplayMixin
from service_recording import check_session_capacity
from service_task_done import TaskDoneReportMixin, _format_task_done_failures  # noqa: F401

if TYPE_CHECKING:
    from project_backend import SQLiteBackend
    from project_service import ProjectService

_LIFECYCLE_STATUSES = frozenset({"done", "active", "blocked", "review"})


_MISSING = object()


from service_validation import load_stacks as _load_stacks  # noqa: E402,F401
from service_validation import update_enums as _update_enums  # noqa: E402,F401
from service_recording import apply_force_capacity_audit as _apply_force_audit  # noqa: E402,F401


class TaskMixin(TaskDoneReportMixin, GatesMixin, CascadeMixin, ReasoningMixin, ReplayMixin):
    """Task lifecycle with strict workflow enforcement."""

    be: SQLiteBackend

    def _project_task(self, slug: str) -> None:
        """Re-serialize ONE task to `tausik/`. Fail-open — never raises.

        Called from every task mutator. Only `task_done` used to export, so a
        task created, re-specced, started, blocked or journalled on a branch did
        not travel with it; the tree only caught up on the next full
        `tausik state export`, which is why `status` reported no divergence.
        Claim/unclaim are deliberately absent: `claimed_by` is not one of the
        columns `state_export.export_one` serializes, so they cannot change the
        projection.
        """
        from state_triggers import auto_export_entity

        auto_export_entity(cast("ProjectService", self), "tasks", slug)

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
        *,
        cost_budget_usd: float | None = None,
        token_budget: int | None = None,
    ) -> str:
        from tausik_utils import safe_single_line

        if story_slug:
            self._require_story(story_slug)
        validate_slug(slug)
        validate_length("title", title)
        title = safe_single_line(title) or title
        from service_validation import validate_task_add_inputs

        validate_task_add_inputs(
            stack,
            complexity,
            call_budget,
            tier,
            cost_budget_usd=cost_budget_usd,
            token_budget=token_budget,
        )
        if defect_of:
            self._require_task(defect_of)
        validate_content("goal", goal)
        score = COMPLEXITY_SP.get(complexity, 1) if complexity else 1
        self.be.task_add(story_slug, slug, title, stack, complexity, score, goal, role, defect_of)
        notice = ""
        if call_budget is not None:
            self.be.task_set_call_budget(slug, call_budget)
            if tier is not None:
                notice = f"\nNote: --tier '{tier}' overridden by --call-budget."
        elif tier is not None:
            self.be.task_update(slug, tier=tier)
        if cost_budget_usd is not None:
            self.be.task_set_cost_budget(slug, float(cost_budget_usd))
        if token_budget is not None:
            self.be.task_set_token_budget(slug, int(token_budget))
        self._project_task(slug)
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
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        if status:
            for s in status.split(","):
                if s not in VALID_TASK_STATUSES:
                    raise ServiceError(
                        f"Invalid status '{s}'. Valid: {', '.join(sorted(VALID_TASK_STATUSES))}"
                    )
        return self.be.task_list(
            status, story, epic, role, stack, limit=limit, include_archived=include_archived
        )

    def task_show(self, slug: str) -> dict[str, Any]:
        task = self.be.task_get_full(slug)
        if not task:
            raise ServiceError(f"Task '{slug}' not found")
        task["decisions"] = self.be.decisions_for_task(slug)
        task["reasoning_steps"] = self.be.reasoning_step_list(slug)
        task["specs"] = self.be.specs_for_task(slug)
        task["adapts"] = self.be.adapts_for_target("task", slug)
        return task

    def task_start(self, slug: str, _internal_force: bool = False, force: bool = False) -> str:
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
            updates.update(model_start_updates(self.be))  # pin model at first activation
        self.be.begin_tx()
        try:
            self.be.task_update(slug, **updates)
            self._cascade_start(slug)
            self.be.commit_tx()
        except Exception:
            self.be.rollback_tx()
            raise
        self._project_task(slug)
        msgs = [f"Task '{slug}' started (attempt #{updates['attempts']})."]
        msgs.extend(qg0_warnings)
        if capacity_audit:
            msgs.append(f"⚠ {capacity_audit}")
        # v15-ow-hook-recognize: worker-mode notice for a delegated task (and the
        # orchestrator model banner is suppressed for it), else the normal banner.
        from service_delegate import start_recognition_message

        rec_msg = start_recognition_message(self.be, slug, task.get("complexity"))
        if rec_msg:
            msgs.append(rec_msg)
        try:
            from model_routing_session import record_active_task_recommendation
            from project_config import find_tausik_dir

            record_active_task_recommendation(find_tausik_dir(), slug, task.get("complexity"))
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            # Persistence is best-effort — never block task_start on it.
            pass
        return "\n".join(msgs) if len(msgs) > 1 else msgs[0]

    def task_done(
        self,
        slug: str,
        relevant_files: list[str] | None = None,
        ac_verified: bool = False,
        no_knowledge: bool = False,
        evidence: str | None = None,
        progress_fn: Any | None = None,
        evidence_json: str | None = None,
        no_file_changes: bool = False,
        no_changelog: bool = False,
        verify_handle: str | None = None,
    ) -> str:
        report = self._task_done_report(
            slug,
            relevant_files=relevant_files,
            ac_verified=ac_verified,
            no_knowledge=no_knowledge,
            evidence=evidence,
            evidence_json=evidence_json,
            progress_fn=progress_fn,
            no_file_changes=no_file_changes,
            no_changelog=no_changelog,
            verify_handle=verify_handle,
        )
        if not report.get("ok"):
            raise ServiceError(_format_task_done_failures(report))
        try:
            from model_routing_adherence import finalize_close
            from project_config import find_tausik_dir
            from state_triggers import auto_export_entity

            finalize_close(find_tausik_dir(), slug)  # routing telemetry (best-effort)
            # cast: mixin is a composed ProjectService at runtime (see service_knowledge)
            auto_export_entity(cast("ProjectService", self), "tasks", slug)
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            pass
        message = report.get("message")
        if isinstance(message, str) and message.strip():
            return message
        return f"Task '{slug}' completed."

    # _task_done_report -> moved to service_task_done.TaskDoneReportMixin
    # (filesize-debt-paydown-2). Mixed in via inheritance; same call signature.

    def task_block(self, slug: str, reason: str | None = None) -> str:
        task = self._require_task(slug)
        if task["status"] == "done":
            raise ServiceError(f"Cannot block a done task '{slug}'")

        updates: dict[str, Any] = {"status": "blocked", "blocked_at": utcnow_iso()}
        self.be.task_update(slug, **updates)
        if reason:
            self.be.task_append_notes(slug, f"BLOCKED: {reason}")
        self._project_task(slug)
        return f"Task '{slug}' blocked."

    def task_unblock(self, slug: str, *, force: bool = False) -> str:
        task = self._require_task(slug)
        if task["status"] != "blocked":
            raise ServiceError(f"Task '{slug}' is not blocked (status: {task['status']})")
        # v1.3.4 (med-batch-2-qg #4): unblock → active; capacity check stops
        # block/unblock cycling past the 180-min ACTIVE threshold (SENAR Rule 9.2).
        if not force:
            check_session_capacity(self.be, slug, task)
        self.be.task_update(slug, status="active", blocked_at=None)
        self._project_task(slug)
        return f"Task '{slug}' unblocked."

    def task_review(self, slug: str) -> str:
        task = self._require_task(slug)
        if task["status"] == "done":
            raise ServiceError(f"Cannot move '{slug}' to review — task is already done")
        self.be.task_update(slug, status="review")
        self._project_task(slug)
        return f"Task '{slug}' moved to review."

    def task_update(self, slug: str, **fields: Any) -> str:
        task = self._require_task(slug)
        # Refuse to clobber the append-only journal (qa-task-update-notes-guard);
        # pops notes_overwrite, raises if a non-empty journal would be replaced.
        from task_notes_guard import guard_notes_overwrite

        guard_notes_overwrite(slug, task.get("notes"), fields)
        if fields.get("status") in _LIFECYCLE_STATUSES:
            raise ServiceError(
                f"status='{fields['status']}' must use lifecycle method "
                f"(task_done/start/block/review) — would bypass QG-2."
            )
        # Emptiness first: the enum check below reads `if v and ...`, so an
        # empty string slipped PAST it rather than failing it, and every plain
        # text field had no check at all. Blanking is refused for the fields a
        # gate reads; the list and its exclusions live in service_validation.
        from service_validation import reject_blank_updates

        reject_blank_updates(fields)
        for name, valid in _update_enums():
            v = fields.get(name)
            if v and v not in valid:
                raise ServiceError(f"Invalid {name} '{v}'. Valid: {sorted(valid)}")
        # EVERY budget is validated before ANY of them is written. The three used
        # to be interleaved — validate call_budget, write it, then validate
        # cost_budget_usd and maybe raise — so a rejected call left the first
        # value in the DB and exited by exception, past the projection. The row
        # changed, the file did not, and nothing said so until the next
        # `state export --check`. `task_add` already validates up front
        # (validate_task_add_inputs); this is the same shape, applied late.
        cb = fields.pop("call_budget", _MISSING)
        cost_b = fields.pop("cost_budget_usd", _MISSING)
        tok_b = fields.pop("token_budget", _MISSING)
        notice = ""
        budget_writes: list[tuple[Any, Any]] = []
        if cb is not _MISSING and cb is not None:
            if cb < 0:
                raise ServiceError(f"Invalid call_budget '{cb}'; must be >=0")
            budget_writes.append((self.be.task_set_call_budget, cb))
            tier = fields.pop("tier", None)
            if tier is not None:
                notice = f"\nNote: tier '{tier}' overridden by call_budget."
        if cost_b is not _MISSING and cost_b is not None:
            try:
                cost_val = float(cost_b)
            except (TypeError, ValueError):
                raise ServiceError(
                    f"Invalid cost_budget_usd '{cost_b}'; must be a non-negative number"
                ) from None
            if cost_val < 0:
                raise ServiceError(f"Invalid cost_budget_usd '{cost_b}'; must be >=0")
            budget_writes.append((self.be.task_set_cost_budget, cost_val))
        if tok_b is not _MISSING and tok_b is not None:
            try:
                tok_val = int(tok_b)
            except (TypeError, ValueError):
                raise ServiceError(
                    f"Invalid token_budget '{tok_b}'; must be a non-negative integer"
                ) from None
            if tok_val < 0:
                raise ServiceError(f"Invalid token_budget '{tok_b}'; must be >=0")
            budget_writes.append((self.be.task_set_token_budget, tok_val))
        # ...and so is EVERYTHING ELSE that can refuse. Batching the three
        # budgets against each other narrowed the defect without closing it: the
        # very next block — ACL normalization — still raised AFTER the budget
        # writes had committed, so `--call-budget 40 --scope-paths '{not-json'`
        # left call_budget AND a derived tier in the row, reported failure, and
        # exited past the projection. The same shape, one validator further down.
        from scope_acl import ACL_FIELDS, normalize_acl_json

        for f in ACL_FIELDS:
            if fields.get(f) is not None:
                try:
                    fields[f] = normalize_acl_json(fields[f], f)
                except ValueError as e:
                    raise ServiceError(str(e)) from None
        from tausik_utils import safe_single_line

        for f in ("title", "goal"):
            if fields.get(f) is not None:
                fields[f] = safe_single_line(fields[f]) or fields[f]
        self._write_update_atomically(slug, budget_writes, fields)
        return self._task_updated(slug, notice)

    def _write_update_atomically(
        self, slug: str, budget_writes: list[tuple[Any, Any]], fields: dict[str, Any]
    ) -> None:
        """Apply the budget setters and the field write, or apply neither.

        Validating up front is the primary fix and would be enough for the
        failures anyone has hit. This transaction covers the ones nobody has:
        `_update` rejects an unknown column, SQLite rejects a bad `story_id`,
        the disk fills — all of them raise between the budget writes (which go
        through raw `_ex` and auto-commit) and the field write. Twice now this
        method has been fixed by removing the failure someone found rather than
        the shape that produced it, so the shape is closed here.

        `_pending_projection` is already rollback-aware, so a discarded write
        discards its queued projection with it. If a caller has a transaction
        open, ownership stays with the caller: it will roll back, and committing
        here would end its transaction early.
        """
        owns_tx = not self.be._in_tx
        if owns_tx:
            self.be.begin_tx()
        try:
            for setter, value in budget_writes:
                setter(slug, value)
            # Preserved exactly: a budget-only call does not touch the field
            # write (which would bump updated_at for no declared change).
            if not (budget_writes and not fields):
                self.be.task_update(slug, **fields)
            if owns_tx:
                self.be.commit_tx()
        except Exception:
            if owns_tx:
                self.be.rollback_tx()
            raise

    def task_delete(self, slug: str) -> str:
        self._require_task(slug)
        self.be.task_delete(slug)
        from service_delegate import clear_delegation_state

        clear_delegation_state(self.be, slug)  # drop stale OW meta on slug reuse
        self._project_task(slug)  # export_one -> None -> drops the file
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
        self._project_task(slug)
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
        self._project_task(slug)
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
        self._project_task(slug)  # the journal is part of the task doc
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
        self._project_task(slug)
        return f"Task '{slug}' moved to story '{new_story_slug}'."

    # _cascade_start, _cascade_done -> inherited from CascadeMixin (service_cascade.py)

    def _task_updated(self, slug: str, notice: str) -> str:
        """Single exit for `task_update`: project, then report.

        The method has four return points (call_budget-only, cost-budget-only,
        token-budget-only, and the general field write). Routing them through one
        helper is why a fifth cannot silently skip the projection.
        """
        self._project_task(slug)
        return f"Task '{slug}' updated.{notice}"
