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

    def session_start(self, host_session_id: str | None = None) -> str:
        """Open a session; with a host id, the session IS that host session.

        Without a host id (CLI, MCP `/start`): the old contract — one open
        session, reused if present. With one (the SessionStart hook, decision
        #376): idempotent per host session, and a DIFFERENT open host session
        does not stop this one from opening — two concurrent agents are two
        sessions, not one shared counter.
        """
        if host_session_id:
            mine = self.be.session_current(host_session_id)
            if mine:
                return f"Session #{mine['id']} already active for host session {host_session_id}."
            sid = self.be.session_start(host_session_id)
            return f"Session #{sid} started for host session {host_session_id}."
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

    def session_check_duration(
        self, max_minutes: int | None = None, *, effective_limit: int | None = None
    ) -> str | None:
        from service_session_metrics import session_overrun_warning

        return session_overrun_warning(self.be, max_minutes, effective_limit=effective_limit)

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

    def session_end(self, summary: str | None = None, host_session_id: str | None = None) -> str:
        import os
        import subprocess
        import sys

        if host_session_id:
            # The host is ending ITS session: close exactly that one, never the
            # newest open session of some other agent (decision #376).
            current = self.be.session_current(host_session_id)
            if not current:
                return f"No open session for host session {host_session_id}; nothing to end."
        else:
            current = self.be.session_current()
        if not current:
            raise ServiceError("No active session. Start one: .tausik/tausik session start")
        # Every session ends with a handoff (SENAR 1.5 §7.3): if none was written
        # in it, the generated one is. Best-effort — a failing generator must
        # not keep a session open — but never silent: the failure is an event.
        if not current.get("handoff"):
            try:
                self.session_handoff(None, host_session_id=current.get("host_session_id"))
            except Exception as e:  # noqa: BLE001 — best-effort: recorded, never blocks the end
                self.be.event_add(
                    "session", str(current["id"]), "handoff_generate_failed", str(e)[:300]
                )
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
                [
                    sys.executable,
                    hooks_script,
                    "--auto",
                    "--record",
                    "--session-id",
                    str(current["id"]),
                ],
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
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

    def session_handoff(
        self, handoff: dict[str, Any] | None = None, host_session_id: str | None = None
    ) -> str:
        """Record work continuity. Does NOT require the hygiene window open.

        v2-session-split-and-drop: this used to refuse unless a session was
        active, which coupled the two things `sessions` glues together. The
        coupling had it exactly backwards — an agent that has just hit the
        180-minute limit is the one that most needs to write down where it
        stopped, and refusing there loses the document the limit exists to
        force. Continuity is about the WORK; the active window is about the
        agent's context budget.

        With no open session the handoff attaches to the most recent session
        instead of being dropped. Falling back rather than creating a session is
        deliberate: minting one here would restart the hygiene clock as a side
        effect of writing a document — the same two-halves-in-one-call this task
        exists to undo. Only a project that has never had a session at all is
        refused, because then there is genuinely no row to attach to.

        GENERATED, NOT COMPOSED (1.10, handoff-is-generated-from-the-journal):
        the document is projected from the records of the session's window
        (`handoff_generate`); what the caller passes is authored judgement laid
        on top and marked as such. With `host_session_id` it is written into
        that host's session, not the newest open one of another agent.
        """
        from handoff_generate import generate, merge_authored

        recent = self.be.session_list(1)
        current = (
            (self.be.session_current(host_session_id) if host_session_id else None)
            or self.be.session_current()
            or (recent[0] if recent else None)
        )
        if not current:
            raise ServiceError(
                "No session has ever been started in this project, so there is "
                "nothing to attach a handoff to. Start one: "
                ".tausik/tausik session start"
            )
        # One live holder (github#126): the document says WHEN it was written
        # and WHICH handoff it takes over from — recorded, not implied by the
        # order of rows. The previous one stays readable (`--session N`). The
        # write is a single UPDATE, so there is no moment with zero holders.
        from datetime import datetime, timezone

        handoff = merge_authored(generate(self.be, current), handoff)
        # Microseconds: two writes in one second must still have an order.
        handoff["written_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        # The checkpoint counter's zero point (SENAR 9.3): a recorded fact of
        # the handoff, from which "calls since checkpoint" is derived.
        if not current.get("ended_at"):
            from checkpoint_signal import calls_now

            handoff["calls_at_write"] = calls_now(self.be) or 0
        previous = self.be.session_last_handoff()
        if previous and previous["id"] != current["id"]:
            handoff["supersedes"] = previous["id"]
        self.be.session_update_handoff(current["id"], handoff)
        closed = (
            " (closed — attached to the most recent session)" if current.get("ended_at") else ""
        )
        return f"Handoff saved for session #{current['id']}{closed}."

    def session_last_handoff(self, session_id: int | None = None) -> dict[str, Any] | None:
        """The live handoff; with `session_id`, the handoff of that past session.

        Until 1.10 only the newest handoff was readable, and a table recorded in
        session #179's handoff had to be recovered from the IDE transcript —
        outside the framework (github#137). A missing session and a session
        without a handoff are refused with different words, never answered
        with someone else's handoff.
        """
        row = self.be.session_last_handoff(session_id)
        if session_id is not None:
            if not row:
                raise ServiceError(f"Session #{session_id} does not exist.")
            if not row.get("handoff"):
                raise ServiceError(f"Session #{session_id} has no handoff recorded.")
        if row and row.get("handoff"):
            return dict(json.loads(row["handoff"]))
        return None
