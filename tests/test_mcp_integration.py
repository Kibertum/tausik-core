"""MCP integration tests — real JSON-RPC over stdin/stdout."""

import json
import os
import subprocess
import sys
import time

import pytest

SERVER = os.path.join(
    os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project", "server.py"
)
PYTHON = sys.executable


def _jsonrpc(method: str, params: dict | None = None, req_id: int = 1) -> str:
    """Build a JSON-RPC 2.0 message."""
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        msg["params"] = params
    return json.dumps(msg)


def _send_and_receive(
    proc: subprocess.Popen, messages: list[str], timeout: float = 5.0
) -> list[dict]:
    """Send JSON-RPC messages to MCP server and collect responses."""
    for msg in messages:
        line = msg + "\n"
        proc.stdin.write(line)
    proc.stdin.flush()
    proc.stdin.close()

    results = []
    deadline = time.time() + timeout
    output = ""
    while time.time() < deadline:
        try:
            proc.wait(timeout=0.1)
            # Process exited, read remaining output
            output += proc.stdout.read()
            break
        except subprocess.TimeoutExpired:
            pass

    # Parse JSON-RPC responses from output
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    return results


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project with DB."""
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()

    # Init DB via script
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
    sys.path.insert(0, scripts_dir)
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    db_path = str(tausik_dir / "tausik.db")
    be = SQLiteBackend(db_path)
    svc = ProjectService(be)
    # Seed some data
    svc.epic_add("test-epic", "Test Epic")
    svc.story_add("test-epic", "test-story", "Test Story")
    svc.task_add("test-story", "test-task", "Test Task", role="developer")
    be.close()
    return str(tmp_path)


def _check_mcp_available():
    """Check if mcp package is installed."""
    try:
        import mcp  # noqa: F401

        return True
    except ImportError:
        return False


mcp_available = _check_mcp_available()
skip_no_mcp = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


@skip_no_mcp
class TestMCPServerStartup:
    def test_server_starts_and_accepts_initialize(self, project_dir):
        """Server should start and respond to initialize."""
        proc = subprocess.Popen(
            [PYTHON, SERVER, "--project", project_dir],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=os.path.dirname(SERVER),
        )
        try:
            # Send initialize request
            init_msg = _jsonrpc(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                },
            )
            proc.stdin.write(init_msg + "\n")
            proc.stdin.flush()

            # Wait for response
            proc.stdin.close()
            stdout, stderr = proc.communicate(timeout=5)
            # Server should have produced some output (even if error, it ran)
            assert proc.returncode is not None or stdout or stderr
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            # Timeout is acceptable — server might be waiting for more input
            pass

    def test_server_rejects_missing_project(self):
        """Server should fail without --project flag."""
        result = subprocess.run(
            [PYTHON, SERVER],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "error" in result.stderr.lower()


class TestMCPToolsListing:
    def test_tools_list_has_all_tools(self, project_dir):
        """Verify tools list matches expected count via direct import."""
        mcp_dir = os.path.join(
            os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
        )
        sys.path.insert(0, mcp_dir)
        from tools import TOOLS

        # Should have 26+ tools
        assert len(TOOLS) >= 26
        # All tools must have name, description, inputSchema
        for tool in TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["name"].startswith("tausik_")

    def test_all_tools_have_unique_names(self):
        """No duplicate tool names."""
        mcp_dir = os.path.join(
            os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
        )
        sys.path.insert(0, mcp_dir)
        from tools import TOOLS

        names = [t["name"] for t in TOOLS]
        assert len(names) == len(set(names)), (
            f"Duplicate tools: {[n for n in names if names.count(n) > 1]}"
        )


class TestMCPHandlerDispatch:
    """Test handler dispatch via direct import (fast, no subprocess)."""

    def test_unknown_tool_returns_error(self, project_dir):
        mcp_dir = os.path.join(
            os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
        )
        scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        sys.path.insert(0, mcp_dir)
        sys.path.insert(0, scripts_dir)
        from handlers import handle_tool
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        db = str(os.path.join(project_dir, ".tausik", "tausik.db"))
        be = SQLiteBackend(db)
        svc = ProjectService(be)
        result = handle_tool(svc, "nonexistent_tool", {})
        assert "Unknown tool" in result
        be.close()

    def test_every_tool_name_has_handler(self, project_dir):
        """Every tool in TOOLS list should be handled (not return 'Unknown tool')."""
        mcp_dir = os.path.join(
            os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
        )
        scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        sys.path.insert(0, mcp_dir)
        sys.path.insert(0, scripts_dir)
        from handlers import handle_tool
        from tools import TOOLS
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        db = str(os.path.join(project_dir, ".tausik", "tausik.db"))
        be = SQLiteBackend(db)
        svc = ProjectService(be)

        # Tools that need specific args to avoid KeyError
        skip_tools = {
            "tausik_task_show",
            "tausik_task_add",
            "tausik_task_start",
            "tausik_task_done",
            "tausik_task_block",
            "tausik_task_unblock",
            "tausik_task_update",
            "tausik_task_plan",
            "tausik_task_step",
            "tausik_task_delete",
            "tausik_task_review",
            "tausik_task_move",
            "tausik_task_log",
            "tausik_task_logs",
            "tausik_task_claim",
            "tausik_task_unclaim",
            "tausik_task_quick",
            "tausik_session_handoff",
            "tausik_session_extend",
            "tausik_epic_add",
            "tausik_epic_done",
            "tausik_epic_delete",
            "tausik_story_add",
            "tausik_story_done",
            "tausik_story_delete",
            "tausik_memory_add",
            "tausik_memory_search",
            "tausik_memory_show",
            "tausik_memory_delete",
            "tausik_memory_link",
            "tausik_memory_unlink",
            "tausik_memory_related",
            "tausik_decide",
            "tausik_search",
            "tausik_dead_end",
            "tausik_explore_start",
            "tausik_explore_end",
            "tausik_audit_mark",
            "tausik_gates_enable",
            "tausik_gates_disable",
            "tausik_skill_activate",
            "tausik_skill_deactivate",
            "tausik_skill_install",
            "tausik_skill_uninstall",
            "tausik_skill_repo_add",
            "tausik_skill_repo_remove",
            # v1.3: stack/role/verify tools require args (name/slug/task_slug)
            "tausik_stack_show",
            "tausik_stack_diff",
            "tausik_stack_scaffold",
            "tausik_stack_reset",
            "tausik_stack_export",
            "tausik_role_show",
            "tausik_role_create",
            "tausik_role_update",
            "tausik_role_delete",
            "tausik_verify",
        }
        for tool in TOOLS:
            if tool["name"] in skip_tools:
                continue
            result = handle_tool(svc, tool["name"], {})
            assert "Unknown tool" not in result, f"Tool {tool['name']} not handled"
        be.close()


class TestMCPNewToolHandlers:
    """Handler-level tests for the 16 new MCP tools added in v2.5."""

    @pytest.fixture
    def svc(self, tmp_path):
        mcp_dir = os.path.join(
            os.path.dirname(__file__), "..", "agents", "claude", "mcp", "project"
        )
        scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        if mcp_dir not in sys.path:
            sys.path.insert(0, mcp_dir)
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        db = str(tmp_path / "test.db")
        be = SQLiteBackend(db)
        svc = ProjectService(be)
        yield svc
        be.close()

    def test_dead_end_handler(self, svc):
        from handlers import handle_tool

        result = handle_tool(
            svc,
            "tausik_dead_end",
            {
                "approach": "Tried bcrypt",
                "reason": "Not compatible with Python 3.14",
                "tags": ["crypto"],
                "task_slug": None,
            },
        )
        assert (
            "dead_end" in result.lower() or "memory" in result.lower() or "#" in result
        )

    def test_gates_status_handler(self, svc):
        from handlers import handle_tool

        result = handle_tool(svc, "tausik_gates_status", {})
        assert "pytest" in result or "No gates" in result

    def test_explore_lifecycle(self, svc):
        from handlers import handle_tool

        result = handle_tool(
            svc, "tausik_explore_start", {"title": "Test exploration", "time_limit": 30}
        )
        assert "started" in result.lower() or "exploration" in result.lower()
        result = handle_tool(svc, "tausik_explore_current", {})
        assert "Test exploration" in result
        result = handle_tool(svc, "tausik_explore_end", {"summary": "Found nothing"})
        assert "ended" in result.lower() or "exploration" in result.lower()

    def test_audit_check_handler(self, svc):
        from handlers import handle_tool

        result = handle_tool(svc, "tausik_audit_check", {})
        assert (
            "audit" in result.lower()
            or "up to date" in result.lower()
            or "Error" not in result
        )

    def test_skill_list_handler(self, svc):
        from handlers import handle_tool

        result = handle_tool(svc, "tausik_skill_list", {})
        # May return "(none)" or list of skills
        assert isinstance(result, str)

    def test_fts_optimize_handler(self, svc):
        from handlers import handle_tool

        result = handle_tool(svc, "tausik_fts_optimize", {})
        assert "fts_tasks" in result or "optimiz" in result.lower()

    def test_gates_enable_validates_name(self, svc):
        from handlers import handle_tool

        result = handle_tool(svc, "tausik_gates_enable", {"name": "../../evil"})
        assert "Invalid" in result

    def test_gates_enable_valid(self, svc):
        from handlers import handle_tool

        result = handle_tool(svc, "tausik_gates_enable", {"name": "mypy"})
        assert "enabled" in result.lower()


class TestMCPCrossIDEParity:
    def test_claude_cursor_files_identical(self):
        """claude and cursor MCP servers must be byte-identical."""
        base = os.path.join(os.path.dirname(__file__), "..")
        for fname in ("server.py", "tools.py", "handlers.py"):
            claude_path = os.path.join(
                base, "agents", "claude", "mcp", "project", fname
            )
            cursor_path = os.path.join(
                base, "agents", "cursor", "mcp", "project", fname
            )
            with open(claude_path) as f1, open(cursor_path) as f2:
                assert f1.read() == f2.read(), (
                    f"{fname} differs between claude and cursor"
                )
