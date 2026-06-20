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
