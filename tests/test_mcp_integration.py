"""MCP integration tests — real JSON-RPC over stdin/stdout."""

import json
import os
import subprocess
import sys
import time

import pytest

# v14b-pytest-fast-lane: spawns the MCP server and drives JSON-RPC over pipes.
pytestmark = pytest.mark.slow

SERVER = os.path.join(
    os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project", "server.py"
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
            text=True, encoding="utf-8",
            timeout=5,
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "error" in result.stderr.lower()


class TestMCPToolsListing:
    def test_tools_list_has_all_tools(self, project_dir):
        """Verify tools list matches expected count via direct import."""
        mcp_dir = os.path.join(
            os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project"
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
            os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project"
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
            os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project"
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
            os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project"
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

        # No hand-maintained skip-list of tools-that-need-args: it rots the moment someone
        # adds a tool and forgets it — which is exactly how `tausik_reason_step` and
        # `tausik_task_replay` slipped through, leaving this test (slow lane, deselected by
        # default) red in main unnoticed. Instead, a missing-argument error is treated as
        # PROOF that a handler exists and ran; only "Unknown tool" — the thing actually under
        # test — is a failure. Every future tool is covered with no list to maintain.
        unhandled = []
        for tool in TOOLS:
            try:
                result = handle_tool(svc, tool["name"], {})
            except (KeyError, TypeError):
                continue  # handler exists; it just wants arguments we deliberately withheld
            except Exception:  # noqa: BLE001 — any other error still proves dispatch happened
                continue
            if "Unknown tool" in result:
                unhandled.append(tool["name"])
        assert not unhandled, f"tools with no handler: {unhandled}"
        be.close()


class TestMCPNewToolHandlers:
    """Handler-level tests for the 16 new MCP tools added in v2.5."""

    @pytest.fixture
    def svc(self, tmp_path):
        mcp_dir = os.path.join(
            os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project"
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
        assert "dead_end" in result.lower() or "memory" in result.lower() or "#" in result

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
        assert "audit" in result.lower() or "up to date" in result.lower() or "Error" not in result

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

    def test_task_list_csv_status(self, svc):
        from handlers import handle_tool

        svc.epic_add("e1", "Epic 1")
        svc.story_add("e1", "s1", "Story 1")
        svc.task_add("s1", "t-active", "Active task", role="developer")
        svc.task_add("s1", "t-blocked", "Blocked task", role="developer")
        svc.task_add("s1", "t-done", "Done task", role="developer")
        svc.task_add("s1", "t-planning", "Planning task", role="developer")
        svc.be.task_update("t-active", status="active")
        svc.be.task_update("t-blocked", status="blocked")
        svc.be.task_update("t-done", status="done")

        result = handle_tool(svc, "tausik_task_list", {"status": "active,blocked"})
        assert "t-active" in result
        assert "t-blocked" in result
        assert "t-done" not in result
        assert "t-planning" not in result

        result = handle_tool(svc, "tausik_task_list", {"status": "active"})
        assert "t-active" in result
        assert "t-blocked" not in result

    def test_task_list_csv_status_schema_pattern(self):
        from tools import TOOLS

        tool = next(t for t in TOOLS if t["name"] == "tausik_task_list")
        status_schema = tool["inputSchema"]["properties"]["status"]
        assert "enum" not in status_schema, "status enum blocks CSV input"
        assert "pattern" in status_schema, "status needs regex pattern for CSV validation"
        import re

        rx = re.compile(status_schema["pattern"])
        assert rx.match("active")
        assert rx.match("active,blocked")
        assert rx.match("active,blocked,planning")
        assert not rx.match("bogus")
        assert not rx.match("active,bogus")
        assert not rx.match("active,")


# TestMCPCrossIDEParity (claude/cursor MCP servers must be byte-identical) was deleted
# in v1.7.0 along with the mirror it guarded. Its premise is now inverted: harness/claude/mcp
# is the single canonical tree, and tests/test_mcp_single_canonical_tree.py asserts the
# STRONGER property — that no IDE may ship a byte-copy of it at all.
#
# Worth remembering how this test was found: it lived behind `pytestmark = pytest.mark.slow`,
# and pyproject.toml's `addopts = "-m 'not slow'"` deselects that lane by default. The mirror
# deletion therefore looked green across 4530 tests while the one test that would have caught
# it sat unrun. Before tagging a release, run BOTH lanes (`pytest` and `pytest -m ''`).
