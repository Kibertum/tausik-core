"""Test memory_block: compact re-injection of decisions + conventions + dead ends.

This is the anti-drift mechanism: every /start and /checkpoint re-injects project
memory so the agent doesn't forget prior architectural choices.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


def _fresh_service(tmp_path):
    """Create a ProjectService pointing at an isolated DB inside tmp_path."""
    os.environ["TAUSIK_DIR"] = str(tmp_path / ".tausik")
    (tmp_path / ".tausik").mkdir()
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    db_path = str(tmp_path / ".tausik" / "tausik.db")
    be = SQLiteBackend(db_path)
    svc = ProjectService(be)
    return svc


class TestMemoryBlockContent:
    def test_empty_db_returns_empty_string(self, tmp_path):
        svc = _fresh_service(tmp_path)
        assert svc.memory_block() == ""

    def test_includes_decisions_conventions_deadends(self, tmp_path):
        svc = _fresh_service(tmp_path)
        svc.decide("Use SQLite, not Postgres, for local storage")
        svc.memory_add(
            "convention", "kebab-case slugs", "All task slugs must be kebab-case."
        )
        svc.dead_end(
            "Tried mypy with strict-optional", "Too many false positives in legacy code"
        )

        block = svc.memory_block()
        assert "## TAUSIK Memory Block" in block
        assert "Recent decisions" in block
        assert "SQLite" in block
        assert "Conventions" in block
        assert "kebab-case slugs" in block
        assert "Recent dead ends" in block
        assert "Tried mypy" in block

    def test_respects_max_lines_truncation(self, tmp_path):
        svc = _fresh_service(tmp_path)
        for i in range(60):
            svc.memory_add("convention", f"convention #{i}", f"Text for convention {i}")

        block = svc.memory_block(
            max_decisions=0, max_conventions=60, max_deadends=0, max_lines=20
        )
        lines = block.splitlines()
        assert len(lines) <= 21  # max_lines + optional truncation marker
        assert "truncated" in block

    def test_only_decisions(self, tmp_path):
        svc = _fresh_service(tmp_path)
        svc.decide("We will ship on Monday")
        block = svc.memory_block()
        assert "Recent decisions" in block
        assert "Conventions" not in block
        assert "Recent dead ends" not in block

    def test_long_title_is_trimmed(self, tmp_path):
        svc = _fresh_service(tmp_path)
        svc.memory_add("convention", "C" * 200, "body")
        block = svc.memory_block()
        for line in block.splitlines():
            if line.startswith("- #"):
                assert len(line) <= 120  # 80 char title + prefix


class TestMemoryBlockCli:
    def test_cli_memory_block_outputs(self, tmp_path):
        """The `tausik memory block` CLI sub-command must print the block to stdout."""
        # Use a pre-populated service then invoke the CLI against the same DB
        svc = _fresh_service(tmp_path)
        svc.decide("TestCli decision")
        svc.memory_add("convention", "test-convention", "body")

        # The CLI uses a different import path; easier to test the handler directly
        from project_cli_extra import cmd_memory

        class Args:
            memory_cmd = "block"
            max_decisions = 5
            max_conventions = 10
            max_deadends = 5
            max_lines = 50

        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_memory(svc, Args())
        output = buf.getvalue()
        assert "TestCli decision" in output
        assert "test-convention" in output


class TestMemoryBlockMcp:
    def test_mcp_handler_returns_formatted_string(self, tmp_path):
        svc = _fresh_service(tmp_path)
        svc.decide("MCP handler test")

        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
            ),
        )
        from handlers import _do_memory_block

        result = _do_memory_block(svc, {})
        assert "MCP handler test" in result

    def test_mcp_handler_empty_db(self, tmp_path):
        svc = _fresh_service(tmp_path)
        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
            ),
        )
        from handlers import _do_memory_block

        result = _do_memory_block(svc, {})
        assert "empty" in result.lower()

    def test_mcp_tool_registered(self):
        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
            ),
        )
        from tools import TOOLS

        names = {t["name"] for t in TOOLS}
        assert "tausik_memory_block" in names


class TestSessionStartIntegration:
    """SessionStart hook should call `memory block` and include output when available."""

    def test_hook_script_references_memory_block(self):
        """The hook source must invoke the memory block CLI command."""
        hook_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "hooks", "session_start.py"
        )
        source = open(hook_path, encoding="utf-8").read()
        assert '["memory", "block"]' in source


class TestSkillsDocumentation:
    def test_start_skill_mentions_memory_block(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "agents", "skills", "start", "SKILL.md"
        )
        content = open(path, encoding="utf-8").read()
        assert "tausik_memory_block" in content

    def test_checkpoint_skill_mentions_memory_block(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "agents",
            "skills",
            "checkpoint",
            "SKILL.md",
        )
        content = open(path, encoding="utf-8").read()
        assert "tausik_memory_block" in content
