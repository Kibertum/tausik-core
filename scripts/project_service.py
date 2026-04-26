"""TAUSIK ProjectService -- business logic orchestration.

Composes domain mixins: Hierarchy, Task, Session, Knowledge.
Validates input, enforces business rules, delegates to SQLiteBackend.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError, validate_length, validate_slug
from service_knowledge import KnowledgeMixin
from service_skills import SkillsMixin
from service_task import TaskMixin

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


class HierarchyMixin:
    """Epic/story CRUD with validation."""

    be: SQLiteBackend

    def epic_add(self, slug: str, title: str, description: str | None = None) -> str:
        from tausik_utils import safe_single_line

        validate_slug(slug)
        validate_length("title", title)
        title = safe_single_line(title) or title
        self.be.epic_add(slug, title, safe_single_line(description))
        return f"Epic '{slug}' created."

    def epic_list(self) -> list[dict[str, Any]]:
        return self.be.epic_list()

    def epic_done(self, slug: str) -> str:
        self._require_epic(slug)
        self.be.epic_update(slug, status="done")
        return f"Epic '{slug}' marked done."

    def epic_delete(self, slug: str) -> str:
        self._require_epic(slug)
        self.be.epic_delete(slug)
        return f"Epic '{slug}' deleted."

    def story_add(
        self, epic_slug: str, slug: str, title: str, description: str | None = None
    ) -> str:
        from tausik_utils import safe_single_line

        self._require_epic(epic_slug)
        validate_slug(slug)
        validate_length("title", title)
        title = safe_single_line(title) or title
        self.be.story_add(epic_slug, slug, title, safe_single_line(description))
        return f"Story '{slug}' created in epic '{epic_slug}'."

    def story_list(self, epic_slug: str | None = None) -> list[dict[str, Any]]:
        return self.be.story_list(epic_slug)

    def story_done(self, slug: str) -> str:
        self._require_story(slug)
        self.be.story_update(slug, status="done")
        return f"Story '{slug}' marked done."

    def story_delete(self, slug: str) -> str:
        self._require_story(slug)
        self.be.story_delete(slug)
        return f"Story '{slug}' deleted."


class SessionMixin:
    """Session lifecycle with handoff persistence."""

    be: SQLiteBackend

    def session_start(self) -> str:
        current = self.be.session_current()
        if current:
            return f"Session #{current['id']} already active (started {current['started_at']})."
        sid = self.be.session_start()
        return f"Session #{sid} started."

    def session_active_minutes(
        self, session_id: int | None = None, idle_threshold: int | None = None
    ) -> int:
        from service_session_metrics import session_active_minutes as _f

        return _f(self.be, session_id, idle_threshold)

    def session_wall_minutes(self, session_id: int | None = None) -> int:
        from service_session_metrics import session_wall_minutes as _f

        return _f(self.be, session_id)

    def session_check_duration(self, max_minutes: int | None = None) -> str | None:
        from service_session_metrics import session_overrun_warning

        return session_overrun_warning(self.be, max_minutes)

    def session_extend(self, minutes: int = 60) -> str:
        """Extend session active-time limit by N minutes (SENAR Rule 9.2)."""
        from project_config import DEFAULT_SESSION_MAX_MINUTES, load_config
        from service_session_metrics import (
            effective_session_limit,
            session_active_minutes,
        )

        current = self.be.session_current()
        if not current:
            raise ServiceError("No active session to extend.")
        cfg = load_config()
        base = cfg.get("session_max_minutes", DEFAULT_SESSION_MAX_MINUTES)
        effective_limit = effective_session_limit(self.be, current["id"], base)
        new_limit = effective_limit + minutes
        active = session_active_minutes(self.be, current["id"])
        self.be.event_add(
            "session",
            str(current["id"]),
            "session_extend",
            f'{{"old_limit":{effective_limit},"new_limit":{new_limit},"active":{active}}}',
        )
        return (
            f"Session #{current['id']} extended by {minutes} min. "
            f"New limit: {new_limit} min (active: {active} min)."
        )

    def session_end(self, summary: str | None = None) -> str:
        current = self.be.session_current()
        if not current:
            raise ServiceError(
                "No active session. Start one: .tausik/tausik session start"
            )
        self.be.session_end(current["id"], summary)
        return f"Session #{current['id']} ended."

    def session_current(self) -> dict[str, Any] | None:
        return self.be.session_current()

    def session_list(self, n: int = 10) -> list[dict[str, Any]]:
        return self.be.session_list(n)

    def session_handoff(self, handoff: dict[str, Any]) -> str:
        current = self.be.session_current()
        if not current:
            raise ServiceError(
                "No active session. Start one: .tausik/tausik session start"
            )
        self.be.session_update_handoff(current["id"], handoff)
        return f"Handoff saved for session #{current['id']}."

    def session_last_handoff(self) -> dict[str, Any] | None:
        row = self.be.session_last_handoff()
        if row and row.get("handoff"):
            return dict(json.loads(row["handoff"]))
        return None


class ProjectService(
    HierarchyMixin, TaskMixin, SessionMixin, KnowledgeMixin, SkillsMixin
):
    """TAUSIK project service -- composes all domain mixins."""

    def __init__(self, be: SQLiteBackend) -> None:
        self.be = be

    def _require_epic(self, slug: str) -> dict[str, Any]:
        row = self.be.epic_get(slug)
        if not row:
            raise ServiceError(
                f"Epic '{slug}' not found. List epics: .tausik/tausik epic list"
            )
        return row

    def _require_story(self, slug: str) -> dict[str, Any]:
        row = self.be.story_get(slug)
        if not row:
            raise ServiceError(
                f"Story '{slug}' not found. List stories: .tausik/tausik story list"
            )
        return row

    def _require_task(self, slug: str) -> dict[str, Any]:
        row = self.be.task_get(slug)
        if not row:
            raise ServiceError(
                f"Task '{slug}' not found. List tasks: .tausik/tausik task list"
            )
        return row

    # --- Top-level operations ---

    def get_status(self) -> dict[str, Any]:
        return self.be.get_status_data()

    def get_metrics(self) -> dict[str, Any]:
        return self.be.get_metrics()

    def get_roadmap(self, include_done: bool = False) -> list[dict[str, Any]]:
        return self.be.get_roadmap_data(include_done)

    def search(
        self, query: str, scope: str = "all", n: int = 20
    ) -> dict[str, list[dict[str, Any]]]:
        return self.be.search_all(query, scope, n)

    def fts_optimize(self) -> dict[str, str]:
        return self.be.fts_optimize()

    def audit_check(self) -> str | None:
        """Check if periodic audit is overdue (SENAR Rule 9.5). Returns warning or None."""
        value = self.be.meta_get("last_audit_session")
        if not value:
            return "SENAR Rule 9.5: No audit has been performed yet. Run: .tausik/tausik audit mark"
        last_audit = int(value)
        current = self.be.session_current()
        current_id = current["id"] if current else 0
        if current_id - last_audit >= 3:
            return (
                f"SENAR Rule 9.5: {current_id - last_audit} sessions since last audit. "
                f"Run a quality sweep, then: .tausik/tausik audit mark"
            )
        return None

    def audit_mark(self) -> str:
        """Mark periodic audit as completed for current session."""
        current = self.be.session_current()
        if not current:
            raise ServiceError(
                "No active session. Start one: .tausik/tausik session start"
            )
        self.be.meta_set("last_audit_session", str(current["id"]))
        return f"Audit marked at session #{current['id']}."

    # --- Stacks ---

    def stack_info(self, stack: str) -> dict[str, Any]:
        """Return per-stack gate inventory + honest gap notice."""
        from difflib import get_close_matches

        from project_config import DEFAULT_GATES, load_gates
        from project_config import load_config
        from project_types import get_valid_stacks

        valid = get_valid_stacks(load_config())
        if stack not in valid:
            from tausik_utils import ServiceError

            suggest = get_close_matches(stack, sorted(valid), n=2, cutoff=0.5)
            hint = f" Did you mean: {', '.join(suggest)}?" if suggest else ""
            raise ServiceError(
                f"Unknown stack '{stack}'. Valid: {', '.join(sorted(valid))}.{hint}"
            )
        gates = load_gates()
        applicable: list[dict[str, Any]] = []
        for name, gate_def in DEFAULT_GATES.items():
            stacks = gate_def.get("stacks") or []
            if not stacks or stack in stacks:
                merged = dict(gate_def)
                if name in gates:
                    merged.update(gates[name])
                merged["name"] = name
                applicable.append(merged)
        gap_notice = ""
        if not applicable:
            gap_notice = (
                f"No gates configured for stack '{stack}'. Add a custom gate via "
                '`.tausik/config.json` under "gates" (see references/project-cli.md).'
            )
        return {"stack": stack, "gates": applicable, "gap_notice": gap_notice}

    def stack_list(self) -> list[dict[str, Any]]:
        """List all known stacks with applicable gate count."""
        from project_config import DEFAULT_GATES
        from project_config import load_config
        from project_types import DEFAULT_STACKS, get_valid_stacks

        valid = get_valid_stacks(load_config())
        out = []
        for stack in sorted(valid):
            count = sum(
                1
                for g in DEFAULT_GATES.values()
                if not g.get("stacks") or stack in g.get("stacks", [])
            )
            out.append(
                {
                    "stack": stack,
                    "applicable_gates": count,
                    "is_custom": stack not in DEFAULT_STACKS,
                }
            )
        return out

    # --- Gates ---

    def gates_status(self) -> dict[str, Any]:
        """Get gates grouped by stack with active stacks info."""
        from project_config import DEFAULT_GATES, load_config, load_gates

        gates = load_gates()
        cfg = load_config()
        active_stacks = cfg.get("bootstrap", {}).get("stacks", [])

        # Group gates by stack
        stack_groups: dict[str, list[str]] = {"general": []}
        for name, gate_def in DEFAULT_GATES.items():
            stacks = gate_def.get("stacks", [])
            if stacks:
                for stack in stacks:
                    stack_groups.setdefault(stack, [])
                    if name not in stack_groups[stack]:
                        stack_groups[stack].append(name)
            else:
                stack_groups["general"].append(name)
        for name in gates:
            if name not in DEFAULT_GATES:
                stack_groups["general"].append(name)

        # QG-0 readiness
        qg0_report: dict[str, Any] = {}
        try:
            tasks = self.task_list("planning")
            no_goal = [
                t for t in tasks if not t.get("goal") or not str(t["goal"]).strip()
            ]
            no_ac = [
                t
                for t in tasks
                if not t.get("acceptance_criteria")
                or not str(t["acceptance_criteria"]).strip()
            ]
            qg0_report = {
                "planning_count": len(tasks),
                "no_goal": [t["slug"] for t in no_goal[:5]],
                "no_ac": [t["slug"] for t in no_ac[:5]],
            }
        except Exception:
            pass

        return {
            "gates": gates,
            "stack_groups": stack_groups,
            "active_stacks": active_stacks,
            "qg0": qg0_report,
        }

    @staticmethod
    def gate_enable(name: str) -> str:
        from project_config import load_config, save_config

        cfg = load_config()
        cfg.setdefault("gates", {}).setdefault(name, {})["enabled"] = True
        save_config(cfg)
        return f"Gate '{name}' enabled."

    @staticmethod
    def gate_disable(name: str) -> str:
        from project_config import load_config, save_config

        cfg = load_config()
        cfg.setdefault("gates", {}).setdefault(name, {})["enabled"] = False
        save_config(cfg)
        return f"Gate '{name}' disabled."

    # Skill lifecycle -> inherited from SkillsMixin (service_skills.py)
