"""Test memory_compact: aggregate recent task_logs into a pattern summary."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


def _fresh_service(tmp_path):
    os.environ["TAUSIK_DIR"] = str(tmp_path / ".tausik")
    (tmp_path / ".tausik").mkdir()
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    db_path = str(tmp_path / ".tausik" / "tausik.db")
    be = SQLiteBackend(db_path)
    svc = ProjectService(be)
    return svc


def _seed_task_and_logs(svc, slug="t1"):
    """Create a task and seed a handful of log entries with patterns worth aggregating."""
    svc.task_add(None, slug, "Seed task for compact test")
    svc.be.task_log_add(
        slug, "AC verified: scripts/service_knowledge.py ✓", phase="testing"
    )
    svc.be.task_log_add(
        slug, "AC verified: tests/test_memory_block.py ✓", phase="testing"
    )
    svc.be.task_log_add(
        slug, "Fixed scripts/service_knowledge.py bug", phase="implementation"
    )
    svc.be.task_log_add(
        slug, "Added docs to agents/skills/start/SKILL.md", phase="review"
    )


class TestMemoryCompact:
    def test_empty_db_returns_empty(self, tmp_path):
        svc = _fresh_service(tmp_path)
        assert svc.memory_compact() == ""

    def test_reports_phases_words_and_files(self, tmp_path):
        svc = _fresh_service(tmp_path)
        _seed_task_and_logs(svc)

        out = svc.memory_compact()
        assert "Compacted logs (4 entries)" in out
        assert "testing=2" in out
        assert "implementation=1" in out
        assert "review=1" in out
        assert "scripts/service_knowledge.py" in out
        assert "(2×)" in out

    def test_top_words(self, tmp_path):
        svc = _fresh_service(tmp_path)
        svc.task_add(None, "t1", "seed")
        for _ in range(3):
            svc.be.task_log_add("t1", "fixed something here", phase="implementation")
        for _ in range(2):
            svc.be.task_log_add("t1", "added new feature", phase="implementation")
        out = svc.memory_compact()
        assert "fixed(3)" in out
        assert "added(2)" in out

    def test_last_n_limits_rows(self, tmp_path):
        svc = _fresh_service(tmp_path)
        svc.task_add(None, "t1", "seed")
        for i in range(100):
            svc.be.task_log_add("t1", f"entry {i}", phase="planning")
        out = svc.memory_compact(last_n=10)
        assert "Compacted logs (10 entries)" in out

    def test_suggestion_footer_present(self, tmp_path):
        svc = _fresh_service(tmp_path)
        _seed_task_and_logs(svc)
        out = svc.memory_compact()
        assert "memory add convention" in out or "dead_end" in out


class TestMcpAndCli:
    def test_mcp_handler_registered(self):
        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
            ),
        )
        from handlers import _DISPATCH
        from tools import TOOLS

        assert "tausik_memory_compact" in _DISPATCH
        assert any(t["name"] == "tausik_memory_compact" for t in TOOLS)

    def test_mcp_handler_output(self, tmp_path):
        svc = _fresh_service(tmp_path)
        _seed_task_and_logs(svc)
        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
            ),
        )
        from handlers import _do_memory_compact

        out = _do_memory_compact(svc, {})
        assert "Compacted logs" in out

    def test_cli_handler(self, tmp_path):
        svc = _fresh_service(tmp_path)
        _seed_task_and_logs(svc)
        from project_cli_extra import cmd_memory

        class Args:
            memory_cmd = "compact"
            last_n = 50

        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_memory(svc, Args())
        assert "Compacted logs" in buf.getvalue()

    def test_cli_empty_prints_placeholder(self, tmp_path):
        svc = _fresh_service(tmp_path)
        from project_cli_extra import cmd_memory

        class Args:
            memory_cmd = "compact"
            last_n = 50

        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_memory(svc, Args())
        assert "No task logs yet" in buf.getvalue()
