"""Guard: every TAUSIK MCP server must answer prompts/list and resources/list.

TAUSIK exposes only tools — no prompts, no resources. That is fine; what is not fine
is *how* the servers used to say so. They registered `list_tools` and `call_tool` and
nothing else, so a `prompts/list` request came back as JSON-RPC `-32601 Method not
found`. Hosts that ask unconditionally (OpenCode does, without consulting the
advertised capabilities) then fill their log with:

    MCP error -32601: Method not found  failed to get prompts  tausik-project
    MCP error -32601: Method not found  failed to get prompts  tausik-brain

The servers were healthy and their tools worked. But a user debugging a real, separate
breakage read that log and concluded "TAUSIK MCP servers are down" — a false diagnosis
that cost a debugging cycle. TAUSIK forbids silent errors; this is the mirror image, a
loud non-error, and it misleads just as effectively. Answering with an empty list is
free and keeps the log truthful.

Two levels, because neither alone is enough:

  * `test_every_harness_server_registers_*` — a structural sweep over every shipped
    server (brain, project, codebase-rag). Catches a NEW server that forgets the
    handlers.
  * `test_decorator_pattern_really_registers_*` — proves the pattern we used actually
    lands a handler in the SDK's `request_handlers` and flips `get_capabilities`.
    A grep can only show the text is present; this shows the text does something.

This sweep used to cover six servers, because harness/cursor/mcp held a byte-copy of
harness/claude/mcp. That mirror is gone (see test_mcp_single_canonical_tree.py):
copy_mcp hands the canonical tree to every IDE, so three servers is the whole set.

Run: pytest tests/test_mcp_answers_prompts_list.py -v
"""

from __future__ import annotations

import ast
import glob
import os

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Every MCP server shipped by TAUSIK. Discovered, not hardcoded, so a new server or a
# new IDE mirror is covered the moment it lands.
_SERVERS = sorted(glob.glob(os.path.join(_ROOT, "harness", "*", "mcp", "*", "server.py")))

_REQUIRED_HANDLERS = ("list_prompts", "list_resources")


def _registered_decorators(path: str) -> set[str]:
    """Return the set of `server.<name>()` decorators applied to functions in the file.

    Parsed from the AST rather than grepped: a mention inside a comment or a docstring
    must not count as registration.
    """
    tree = ast.parse(open(path, encoding="utf-8").read())
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            # Shape: @server.list_prompts()  ->  Call(func=Attribute(attr='list_prompts'))
            func = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(func, ast.Attribute):
                found.add(func.attr)
    return found


def test_servers_were_discovered():
    """A glob that silently matches nothing would make every test below vacuous."""
    assert len(_SERVERS) >= 3, (
        f"expected >=3 harness MCP servers (brain, project, codebase-rag), "
        f"found {len(_SERVERS)}: {_SERVERS}"
    )


@pytest.mark.parametrize("path", _SERVERS, ids=lambda p: os.path.relpath(p, _ROOT))
def test_every_harness_server_registers_prompts_and_resources(path):
    """No server may leave prompts/list or resources/list unanswered."""
    registered = _registered_decorators(path)
    assert "list_tools" in registered, (
        f"{os.path.relpath(path, _ROOT)}: no list_tools handler — parser is looking at "
        f"the wrong thing, found only {sorted(registered)}"
    )
    missing = [h for h in _REQUIRED_HANDLERS if h not in registered]
    assert not missing, (
        f"{os.path.relpath(path, _ROOT)} does not register {missing}; hosts that call "
        f"prompts/list will get -32601 and the log will report a healthy server as dead"
    )


def test_ast_guard_ignores_mentions_in_comments():
    """Negative scenario: a comment naming the handler must NOT satisfy the guard.

    Otherwise the comment we added explaining the fix would itself 'pass' the test.
    """
    import tempfile

    source = (
        "def main():\n"
        "    server = Server('x')\n"
        "    # TODO: add @server.list_prompts() and @server.list_resources()\n"
        '    """list_prompts list_resources"""\n'
        "    @server.list_tools()\n"
        "    async def list_tools():\n"
        "        return []\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(source)
        tmp = f.name
    try:
        registered = _registered_decorators(tmp)
        assert registered == {"list_tools"}
        assert "list_prompts" not in registered
    finally:
        os.unlink(tmp)


def test_decorator_pattern_really_registers_handlers():
    """Prove `@server.list_prompts()` lands a real handler — not just source text.

    This is the claim the structural sweep above cannot make on its own.
    """
    mcp_server = pytest.importorskip("mcp.server")
    mcp_types = pytest.importorskip("mcp.types")

    server = mcp_server.Server("tausik-test")

    # Before: the SDK knows nothing about prompts/resources.
    assert mcp_types.ListPromptsRequest not in server.request_handlers
    assert mcp_types.ListResourcesRequest not in server.request_handlers

    @server.list_prompts()
    async def list_prompts():
        return []

    @server.list_resources()
    async def list_resources():
        return []

    # After: the requests that used to raise -32601 now have handlers.
    assert mcp_types.ListPromptsRequest in server.request_handlers
    assert mcp_types.ListResourcesRequest in server.request_handlers


def test_empty_prompts_do_not_suppress_the_tool_list():
    """Registering empty prompts/resources must not cost us the tools capability."""
    mcp_server = pytest.importorskip("mcp.server")
    mcp_types = pytest.importorskip("mcp.types")
    pytest.importorskip("mcp.server.lowlevel")

    server = mcp_server.Server("tausik-test")

    @server.list_tools()
    async def list_tools():
        return []

    @server.list_prompts()
    async def list_prompts():
        return []

    @server.list_resources()
    async def list_resources():
        return []

    assert mcp_types.ListToolsRequest in server.request_handlers
    opts = server.create_initialization_options()
    assert opts.capabilities.tools is not None, "tools capability lost"
    assert opts.capabilities.prompts is not None, "prompts capability not advertised"
    assert opts.capabilities.resources is not None, "resources capability not advertised"
