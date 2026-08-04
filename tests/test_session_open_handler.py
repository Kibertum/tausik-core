"""v14b-session-open-compound-rpc — tausik_session_open envelope tests.

The compound RPC collapses /start Phase 1 from 5 sequential MCP calls
(session_start + status compact + last_handoff + task_list active+blocked
+ self_check) into a single round-trip. Each sub-section must be
best-effort and the envelope keys must always be present so /start can
render a degraded dashboard rather than crashing.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project"),
)

from handlers import handle_tool as _handle_tool  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    return ProjectService(SQLiteBackend(os.path.join(str(tmp_path), "tausik.db")))


@pytest.fixture
def seeded(svc):
    """Service with epic + 1 active + 1 blocked + 1 planning task."""
    svc.epic_add("e", "Epic")
    svc.story_add("e", "s", "Story")
    svc.task_add("s", "active-task", "Active task", goal="g", role="developer")
    svc.task_update(
        "active-task",
        acceptance_criteria="1. works\n2. returns error on invalid input",
    )
    svc.task_start("active-task")
    svc.task_add("s", "blocked-task", "Blocked task", goal="g", role="developer")
    svc.task_block("blocked-task", "waiting on upstream")
    svc.task_add("s", "planning-task", "Planning task", goal="g", role="developer")
    return svc


class TestEnvelopeKeysAlwaysPresent:
    def test_session_open_envelope_keys_always_present(self, seeded):
        result = _handle_tool(seeded, "tausik_session_open", {})
        env = json.loads(result)
        assert set(env.keys()) >= {"session", "status", "handoff", "tasks", "self_check"}

    def test_session_open_envelope_on_empty_db(self, svc):
        # Even on a brand-new DB with no tasks, all 5 keys must be present.
        env = json.loads(_handle_tool(svc, "tausik_session_open", {}))
        assert "session" in env
        assert "status" in env
        assert "handoff" in env
        assert "tasks" in env
        assert "self_check" in env


class TestStatusSectionMatchesCompactFormat:
    def test_session_open_status_matches_compact_handler(self, seeded):
        compact_str = _handle_tool(seeded, "tausik_status", {"compact": True})
        compact = json.loads(compact_str)
        env = json.loads(_handle_tool(seeded, "tausik_session_open", {}))
        # The status section must mirror the compact tausik_status output.
        # session_id may differ if session_open started a new session — so
        # compare structure-bearing keys, not session_id which is volatile.
        for key in ("tasks_total", "tasks_done", "tasks_planning"):
            assert env["status"].get(key) == compact.get(key), (
                f"status.{key} diverged from tausik_status compact"
            )


class TestHandoffNullWhenAbsent:
    def test_session_open_handoff_null_when_absent(self, seeded):
        env = json.loads(_handle_tool(seeded, "tausik_session_open", {}))
        # Fresh DB has no prior handoff — must be null, not error or missing.
        assert env["handoff"] is None


class TestTasksSplitActiveBlocked:
    def test_session_open_tasks_split_active_blocked(self, seeded):
        env = json.loads(_handle_tool(seeded, "tausik_session_open", {}))
        active_slugs = {t["slug"] for t in env["tasks"]["active"]}
        blocked_slugs = {t["slug"] for t in env["tasks"]["blocked"]}
        assert "active-task" in active_slugs
        assert "blocked-task" in blocked_slugs
        # Planning tasks must NOT leak into either bucket — /start filters them.
        assert "planning-task" not in active_slugs
        assert "planning-task" not in blocked_slugs

    def test_session_open_task_entries_slim_to_three_keys(self, seeded):
        env = json.loads(_handle_tool(seeded, "tausik_session_open", {}))
        for bucket in ("active", "blocked"):
            for t in env["tasks"][bucket]:
                # Trim to slug/title/status — drop the heavy created_at/notes/etc.
                assert set(t.keys()) == {"slug", "title", "status"}


class TestSelfCheckPresent:
    def test_session_open_self_check_present(self, seeded):
        env = json.loads(_handle_tool(seeded, "tausik_session_open", {}))
        # Self-check sub-call must always populate the section, even if the
        # self_check module fails to import (then it surfaces an "error" key).
        assert isinstance(env["self_check"], dict)
        # On a real test run with self_check importable we expect a server
        # field; on import failure it has an "error" sentinel — accept either.
        assert "server" in env["self_check"] or "error" in env["self_check"]


class TestEnvelopeProjection:
    """session-open-envelope-90pct-noise — the envelope ships only what /start renders.

    Measured before the fix, on a real session: 49 165 chars, of which
    self_check.current_mtimes (13 637) + self_check.watched_modules (12 385)
    were module→mtime telemetry the dashboard never reads, and session.handoff
    (15 480) was a \\u-escaped duplicate of the top-level handoff section
    (4 720 unescaped — Cyrillic inflates 3.3x when JSON-escaped inside a nested
    string). ~5 KB of signal in a 49 KB payload, which blew past the host's
    tool-result ceiling: the compound RPC built to replace five calls degraded
    into a file dump costing MORE than the five it replaced.
    """

    # Ceiling for a realistic envelope. Generous against the ~5 KB of real signal,
    # but far below any single dropped blob — so re-adding one fails this.
    BUDGET = 8000

    @staticmethod
    def _fat_self_check(n_modules: int = 120) -> dict:
        """A self_check report shaped like a real one: absolute paths + mtimes."""
        paths = {
            f"d:\\Work\\Kibertum\\clients\\kibertum\\tausik\\core\\scripts\\module_{i:03d}.py": (
                1785176436.215096 + i
            )
            for i in range(n_modules)
        }
        return {
            "server": "tausik-project",
            "pid": 33816,
            "startup_time_iso": "2026-07-27T20:49:57.445944+00:00",
            "watched_modules_count": len(paths),
            "watched_modules": dict(paths),
            "current_mtimes": dict(paths),
            "drift_detected": False,
            "stale_modules": [],
            "sibling_mcp_count": 0,
            "sibling_mcp_pids": [],
            "sibling_introspection_error": None,
            "sibling_warning": "",
            "remediation": "MCP modules in sync; no action needed.",
        }

    @staticmethod
    def _cyrillic_handoff() -> dict:
        """A handoff the size real ones reach (>= 4 KB of Cyrillic prose)."""
        line = (
            "Закрыта задача state-roundtrip-regression-sync-corrupts: команда sync "
            "была разрушительна и это прожило пять сессий подряд без обнаружения. "
        )
        return {
            "completed": [line * 2 for _ in range(8)],
            "in_progress": [],
            "key_files": ["scripts/state_import.py"],
            "dead_ends": [],
            "next_steps": ["Коммит отложен — требуется явное одобрение пользователя."],
            "warnings": ["Сессия #147: 104/180 минут ACTIVE."],
        }

    @pytest.fixture
    def fat_env(self, seeded, monkeypatch):
        """Envelope built over a realistic-sized self_check + handoff."""
        import self_check  # type: ignore[import-not-found]

        monkeypatch.setattr(self_check, "collect", self._fat_self_check)
        seeded.session_start()
        seeded.session_handoff(self._cyrillic_handoff())
        return json.loads(_handle_tool(seeded, "tausik_session_open", {}))

    def test_self_check_section_drops_module_telemetry(self, fat_env):
        """AC1 — 26 KB the dashboard never reads must not ride along."""
        sc = fat_env["self_check"]
        assert "watched_modules" not in sc
        assert "current_mtimes" not in sc
        # ...while the two signals /start Phase 3 actually renders survive.
        assert sc["drift_detected"] is False
        assert sc["stale_modules"] == []
        assert sc["watched_modules_count"] == 120

    def test_self_check_tool_keeps_full_telemetry(self, seeded, monkeypatch):
        """AC2 — narrowing applies to the envelope ONLY.

        `tausik_self_check` is the explicit, opt-in diagnostic; full fidelity is
        its entire purpose. Losing it here would trade one bug for another.
        """
        import self_check  # type: ignore[import-not-found]

        monkeypatch.setattr(self_check, "collect", self._fat_self_check)
        report = json.loads(_handle_tool(seeded, "tausik_self_check", {}))
        assert "watched_modules" in report
        assert "current_mtimes" in report

    def test_session_section_drops_handoff_duplicate(self, fat_env):
        """AC3 — the handoff ships once, parsed, not twice with one copy escaped."""
        assert "handoff" not in fat_env["session"]
        assert "tasks_done" not in fat_env["session"]
        # The parsed section still carries it — this is a de-duplication, not a loss.
        assert fat_env["handoff"] is not None
        assert "Закрыта задача" in json.dumps(fat_env["handoff"], ensure_ascii=False)

    def test_session_section_is_allowlisted(self, fat_env):
        """AC1/AC3 — allowlist, so a heavy field added upstream can't re-inflate."""
        assert set(fat_env["session"].keys()) <= {
            "id",
            "started_at",
            "ended_at",
            "model_id",
            "model_version",
        }

    def test_envelope_stays_under_budget(self, fat_env):
        """AC4 — the regression guard itself."""
        size = len(json.dumps(fat_env, ensure_ascii=False))
        assert size <= self.BUDGET, f"session_open envelope grew to {size} chars"

    def test_budget_guard_has_teeth(self):
        """AC4 — prove the ceiling FAILS on regression, rather than passing vacuously.

        A budget assertion that would hold even with the blobs restored tests
        nothing. Each dropped section alone must exceed the whole budget.
        """
        raw = self._fat_self_check()
        assert len(json.dumps(raw["watched_modules"])) > self.BUDGET
        assert len(json.dumps(raw["current_mtimes"])) > self.BUDGET
        # The handoff duplicate is over budget too, once \u-escaped as it was
        # when nested inside the session row's JSON string column.
        nested = json.dumps(json.dumps(self._cyrillic_handoff()))
        assert len(nested) > self.BUDGET

    def test_envelope_leaks_no_absolute_host_paths(self, fat_env):
        """AC7 — /start runs unattended every session, so this is a standing export.

        The dropped fields published 108 absolute paths of the developer's tree
        (client name included in the directory layout) plus machine mtimes. The
        envelope must carry no absolute host path at all; relative repo paths
        inside handoff prose are authored content, not host leakage, so the
        assertion anchors on the working directory prefix.
        """
        blob = json.dumps(fat_env, ensure_ascii=False).lower()
        assert os.getcwd().lower() not in blob
        assert "d:\\work\\kibertum" not in blob

    def test_stale_modules_named_by_basename_not_path(self, seeded, monkeypatch):
        """AC7 — on real drift, name the culprit without shipping its absolute path.

        The remediation is "restart your IDE"; a basename identifies the stale
        module for that. The full path stays available via `tausik_self_check`.
        """
        import self_check  # type: ignore[import-not-found]

        drifted = self._fat_self_check()
        drifted["drift_detected"] = True
        drifted["stale_modules"] = [
            {
                "module": "handlers.py",
                "path": "d:\\Work\\Kibertum\\clients\\kibertum\\tausik\\core\\scripts\\handlers.py",
                "snapshot_mtime": 1785176436.2,
                "current_mtime": 1785176999.9,
                "delta_seconds": 563.7,
                "reason": "edited-after-startup",
            }
        ]
        monkeypatch.setattr(self_check, "collect", lambda: drifted)
        env = json.loads(_handle_tool(seeded, "tausik_session_open", {}))
        stale = env["self_check"]["stale_modules"]
        assert stale[0]["module"] == "handlers.py"
        assert stale[0]["reason"] == "edited-after-startup"
        assert "path" not in stale[0]
        # And the drift headline still reaches /start — the narrowing must not
        # mute the one signal that tells the agent to stop trusting MCP.
        assert env["self_check"]["drift_detected"] is True

    def test_error_sections_pass_through_unprojected(self):
        """A failed section carries only {"error": ...}; an allowlist would erase it.

        That would defeat the degraded-dashboard design the watchdog exists for.
        """
        from handlers_session import _project, _project_self_check

        err = {"error": "self_check timed out after 6s"}
        assert _project(err, ("id", "started_at")) == err
        assert _project_self_check(err) == err


class TestSchemaRegistration:
    def test_tausik_session_open_in_tools_extra_schema(self):
        for ide in ("claude", "cursor"):
            sys.path.insert(
                0,
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "harness",
                    ide,
                    "mcp",
                    "project",
                ),
            )
        # Re-import tools_extra after path insert (last wins on repeat import).
        import importlib

        import tools_extra

        importlib.reload(tools_extra)
        names = {t["name"] for t in tools_extra.TOOLS_EXTRA}
        assert "tausik_session_open" in names

    def test_tausik_session_open_takes_no_required_args(self):
        import importlib

        import tools_extra

        importlib.reload(tools_extra)
        spec = next(t for t in tools_extra.TOOLS_EXTRA if t["name"] == "tausik_session_open")
        assert spec["inputSchema"].get("required", []) == []
