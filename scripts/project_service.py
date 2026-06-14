"""TAUSIK ProjectService -- business logic orchestration.

Composes domain mixins: Hierarchy, Task, Session, Knowledge.
Validates input, enforces business rules, delegates to SQLiteBackend.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError
from service_adapts import AdaptsMixin
from service_delegate import DelegateMixin
from service_hierarchy import HierarchyMixin
from service_knowledge import KnowledgeMixin
from service_session import SessionMixin
from service_skills import SkillsMixin
from service_specs import SpecsMixin
from service_task import TaskMixin
from service_task_team import TaskTeamMixin

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


# HierarchyMixin moved to service_hierarchy.py (filesize-debt-paydown).
# SessionMixin moved to service_session.py (filesize-debt-paydown-2).
class ProjectService(
    HierarchyMixin,
    TaskMixin,
    TaskTeamMixin,
    SessionMixin,
    KnowledgeMixin,
    SkillsMixin,
    SpecsMixin,
    AdaptsMixin,
    DelegateMixin,
):
    """TAUSIK project service -- composes all domain mixins."""

    def __init__(self, be: SQLiteBackend) -> None:
        self.be = be

    def _require_epic(self, slug: str) -> dict[str, Any]:
        row = self.be.epic_get(slug)
        if not row:
            raise ServiceError(f"Epic '{slug}' not found. List epics: .tausik/tausik epic list")
        return row

    def _require_story(self, slug: str) -> dict[str, Any]:
        row = self.be.story_get(slug)
        if not row:
            raise ServiceError(f"Story '{slug}' not found. List stories: .tausik/tausik story list")
        return row

    def _require_task(self, slug: str) -> dict[str, Any]:
        row = self.be.task_get(slug)
        if not row:
            raise ServiceError(f"Task '{slug}' not found. List tasks: .tausik/tausik task list")
        return row

    @staticmethod
    def _validate_usage_counters(
        tokens_input: int,
        tokens_output: int,
        tokens_total: int,
        tool_calls: int,
        cost_usd: float,
    ) -> None:
        for label, val in (
            ("tokens_input", tokens_input),
            ("tokens_output", tokens_output),
            ("tokens_total", tokens_total),
            ("tool_calls", tool_calls),
        ):
            if int(val) < 0:
                raise ServiceError(f"{label} cannot be negative")
        if float(cost_usd) < 0:
            raise ServiceError("cost_usd cannot be negative")

    @staticmethod
    def _normalize_usage_time_bound(label: str, raw: str | None) -> str | None:
        if raw is None:
            return None
        spec = str(raw).strip()
        if not spec:
            return None
        from datetime import datetime, timezone

        s = spec.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError as e:
            raise ServiceError(f"Invalid {label} timestamp (ISO-8601): {spec!r}") from e
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- Top-level operations ---

    def get_status(self) -> dict[str, Any]:
        return self.be.get_status_data()

    def get_metrics(self) -> dict[str, Any]:
        return self.be.get_metrics()

    def metrics_record_session(
        self,
        tokens_input: int,
        tokens_output: int,
        tokens_total: int,
        cost_usd: float,
        tool_calls: int = 0,
        model: str = "",
        session_id: int | None = None,
    ) -> str:
        self._validate_usage_counters(
            tokens_input, tokens_output, tokens_total, tool_calls, cost_usd
        )
        sid = session_id
        if sid is None:
            current = self.be.session_current()
            if not current:
                raise ServiceError("No active session. Pass --session-id or start session first.")
            sid = int(current["id"])
        self.be.session_usage_record(
            sid,
            int(tokens_input),
            int(tokens_output),
            int(tokens_total),
            float(cost_usd),
            int(tool_calls),
            model,
        )
        return (
            f"Session usage recorded for session #{sid}: "
            f"{int(tokens_total):,} tokens, ${float(cost_usd):.4f}."
        )

    def metrics_log_usage_event(
        self,
        tokens_input: int,
        tokens_output: int,
        tokens_total: int,
        cost_usd: float,
        tool_calls: int = 0,
        model: str = "",
        task_slug: str | None = None,
        session_id: int | None = None,
    ) -> str:
        """Append a manual usage_events row (does not touch session_usage_metrics)."""
        self._validate_usage_counters(
            tokens_input, tokens_output, tokens_total, tool_calls, cost_usd
        )
        sid = session_id
        if sid is None:
            current = self.be.session_current()
            if not current:
                raise ServiceError("No active session. Pass --session-id or start session first.")
            sid = int(current["id"])
        ts: str | None = None
        if task_slug is not None and str(task_slug).strip():
            ts = str(task_slug).strip()
            self._require_task(ts)
        rid = self.be.usage_event_append(
            sid,
            ts,
            int(tokens_input),
            int(tokens_output),
            int(tokens_total),
            float(cost_usd),
            int(tool_calls),
            (model or "").strip() or None,
            "manual",
        )
        task_part = f", task={ts}" if ts else ""
        return (
            f"usage_events #{rid}: manual log for session #{sid}{task_part} "
            f"({int(tokens_total):,} tokens, ${float(cost_usd):.4f})."
        )

    def usage_cost_rollup_by_task(
        self,
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict[str, Any]]:
        s_bound = self._normalize_usage_time_bound("since", since)
        u_bound = self._normalize_usage_time_bound("until", until)
        if s_bound and u_bound and s_bound > u_bound:
            raise ServiceError("`since` must be <= `until` (ISO timestamps).")
        return self.be.usage_events_cost_rollup_by_task(since=s_bound, until=u_bound)

    def get_roadmap(self, include_done: bool = False) -> list[dict[str, Any]]:
        return self.be.get_roadmap_data(include_done)

    def search(
        self, query: str, scope: str = "all", n: int = 20
    ) -> dict[str, list[dict[str, Any]]]:
        return self.be.search_all(query, scope, n)

    def fts_optimize(self) -> dict[str, str]:
        return self.be.fts_optimize()

    def fts_maybe_optimize(self, threshold: int = 200) -> dict[str, Any]:
        return self.be.fts_maybe_optimize(threshold)

    def audit_check(self) -> str | None:
        """SENAR Rule 9.5 warning string, None when not overdue."""
        if not self.be.meta_get("last_audit_session"):
            return "SENAR Rule 9.5: No audit has been performed yet. Run: .tausik/tausik audit mark"
        n = self.audit_overdue_sessions()
        if n < 3:
            return None
        return f"SENAR Rule 9.5: {n} sessions since last audit. Run a quality sweep, then: .tausik/tausik audit mark"

    def audit_overdue_sessions(self) -> int:
        from service_session_metrics import audit_overdue_sessions as _f

        return _f(self.be)

    def audit_mark(self) -> str:
        """Mark periodic audit as completed for current session."""
        current = self.be.session_current()
        if not current:
            raise ServiceError("No active session. Start one: .tausik/tausik session start")
        self.be.meta_set("last_audit_session", str(current["id"]))
        return f"Audit marked at session #{current['id']}."

    # --- Stacks ---

    def stack_info(self, stack: str) -> dict[str, Any]:
        """Return per-stack gate inventory + honest gap notice."""
        from difflib import get_close_matches

        from project_config import DEFAULT_GATES, load_config, load_gates
        from project_types import get_valid_stacks

        valid = get_valid_stacks(load_config())
        if stack not in valid:
            from tausik_utils import ServiceError

            suggest = get_close_matches(stack, sorted(valid), n=2, cutoff=0.5)
            hint = f" Did you mean: {', '.join(suggest)}?" if suggest else ""
            raise ServiceError(f"Unknown stack '{stack}'. Valid: {', '.join(sorted(valid))}.{hint}")
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
        from project_config import DEFAULT_GATES, load_config
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
            no_goal = [t for t in tasks if not t.get("goal") or not str(t["goal"]).strip()]
            no_ac = [
                t
                for t in tasks
                if not t.get("acceptance_criteria") or not str(t["acceptance_criteria"]).strip()
            ]
            qg0_report = {
                "planning_count": len(tasks),
                "no_goal": [t["slug"] for t in no_goal[:5]],
                "no_ac": [t["slug"] for t in no_ac[:5]],
            }
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
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
