"""TAUSIK SessionMixin — session lifecycle with handoff persistence.

Extracted from project_service.py to keep that module under the 400-line
filesize gate (filesize-debt-paydown-2). Pure re-org — no semantic changes.
ProjectService composes this mixin via multiple inheritance just like
HierarchyMixin/TaskMixin/KnowledgeMixin/SkillsMixin.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


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

    def session_active_seconds(
        self, session_id: int | None = None, idle_threshold: int | None = None
    ) -> int:
        from service_session_metrics import session_active_seconds as _f

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
        import os
        import subprocess
        import sys

        current = self.be.session_current()
        if not current:
            raise ServiceError("No active session. Start one: .tausik/tausik session start")
        self.be.session_end(current["id"], summary)
        # Best-effort FTS maintenance: optimize only past a churn threshold, fast
        # (sub-second on these indexes) and swallowed on failure so it never
        # blocks or breaks session end. (v15p-fts-optimize-cron)
        try:
            self.be.fts_maybe_optimize()
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            pass
        if os.environ.get("TAUSIK_DISABLE_SESSION_METRICS") == "1":
            return f"Session #{current['id']} ended."
        hooks_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "hooks",
            "session_metrics.py",
        )
        if not os.path.isfile(hooks_script):
            return f"Session #{current['id']} ended."
        try:
            # Best-effort: do not fail session end when transcript isn't available.
            # stdin=DEVNULL: when this runs inside the MCP server's worker thread
            # the child would otherwise inherit the JSON-RPC stdin pipe and could
            # block on it. See defect v14b-defect-mcp-task-done-stdin-hang.
            subprocess.run(
                [sys.executable, hooks_script, "--auto", "--record"],
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                stdin=subprocess.DEVNULL,
            )
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            pass
        return f"Session #{current['id']} ended."

    def session_current(self) -> dict[str, Any] | None:
        return self.be.session_current()

    def session_list(self, n: int = 10) -> list[dict[str, Any]]:
        return self.be.session_list(n)

    def session_handoff(self, handoff: dict[str, Any]) -> str:
        current = self.be.session_current()
        if not current:
            raise ServiceError("No active session. Start one: .tausik/tausik session start")
        self.be.session_update_handoff(current["id"], handoff)
        return f"Handoff saved for session #{current['id']}."

    def session_last_handoff(self) -> dict[str, Any] | None:
        row = self.be.session_last_handoff()
        if row and row.get("handoff"):
            return dict(json.loads(row["handoff"]))
        return None
