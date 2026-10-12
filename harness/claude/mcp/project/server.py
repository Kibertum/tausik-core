#!/usr/bin/env python3
"""TAUSIK MCP server — project management via SQLite.

Tools defined in tools.py, handlers in handlers.py.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback

# The argument guard is shared with the codebase-rag server and lives in
# scripts/ (sibling-mcp-servers-still-drop-unknown-arguments): one list of
# rules, not one per server. scripts/ must be importable before main() runs,
# from the deployed profile (.claude/mcp/project -> .claude/scripts) and from the
# source tree (harness/claude/mcp/project -> scripts) alike.
for _hops in (2, 4):
    _cand = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * _hops, "scripts")
    )
    if os.path.isfile(os.path.join(_cand, "mcp_arguments.py")):
        if _cand not in sys.path:
            sys.path.insert(0, _cand)
        break

from mcp_arguments import (  # noqa: E402
    declared_arguments,
    reject_unknown_arguments,
)
from mcp_arguments import error_reply as _error_reply  # noqa: E402
from mcp_arguments import usage_hint as _usage_hint  # noqa: E402

__all__ = ["declared_arguments", "reject_unknown_arguments", "_error_reply", "_usage_hint"]


def _get_service(project_dir: str):
    """Create ProjectService for project."""
    mcp_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.normpath(os.path.join(mcp_dir, "..", "..", "scripts"))
    if os.path.isdir(scripts_dir) and scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    db_path = os.path.join(project_dir, ".tausik", "tausik.db")
    be = SQLiteBackend(db_path)
    return ProjectService(be)


def main():
    # UTF-8 stdio before any output — MCP servers launch directly (not via the
    # CLI wrapper); a Windows cp1251 host crashes on Cyrillic paths/messages.
    _scripts_dir = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
    )
    if os.path.isdir(_scripts_dir) and _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    try:
        from tausik_utils import fix_stdio_encoding

        fix_stdio_encoding()
    except Exception:  # noqa: BLE001,S110 — never let stdio setup crash the server
        pass

    # Pin the moment this process started, for the bootstrap_drift gate's
    # third link: a redeploy under a running server changes the files on disk
    # and nothing the server executes. The snapshot covers the scripts tree
    # the server imports from and this mcp/ tree it is itself part of. Taken
    # here, at the top of main, so no later import can move it — and never
    # fatal: a server that cannot snapshot must still serve.
    try:
        import running_source_drift

        running_source_drift.record_start(os.path.dirname(os.path.abspath(__file__)))
    except Exception:  # noqa: BLE001,S110 - a server that cannot snapshot must still serve
        pass

    parser = argparse.ArgumentParser()
    # OPTIONAL SINCE THE MULTI-TENANT SEAM. With it the server is pinned and behaves exactly
    # as before — that is how the host launches it today and how a cron job says what it
    # means. Without it the project is resolved per request; see `tenancy.py` for what that
    # costs and why the cost is only paid in that mode.
    parser.add_argument(
        "--project",
        default=None,
        help="Project root directory. Omit to resolve per request.",
    )
    args = parser.parse_args()

    # Pin cwd to --project so handlers that resolve paths relative to cwd
    # (_project_dir() in handlers_skill.py, the config lookup in handlers_cq.py,
    # the user-override path in handlers_stack.py) read the right project
    # regardless of the host's launch directory. Mirrors tausik-brain
    # server.py behavior — keeps the two MCP servers symmetric.
    if args.project is not None:
        if not os.path.isdir(args.project):
            print(
                f"Error: --project {args.project!r} is not a directory.",
                file=sys.stderr,
            )
            sys.exit(2)
        os.chdir(args.project)

    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import ListToolsResult, TextContent, Tool
    except ImportError:
        print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    from handlers import handle_tool
    from tools import TOOLS

    # v14b-mcp-stale-module-detector: eager-import the self-check module so
    # its startup snapshot of watched-module mtimes runs BEFORE the JSON-RPC
    # loop accepts tool calls. `tausik_self_check` later compares this
    # baseline against current on-disk mtimes to detect stale-module hangs
    # (gotchas #77 / #79 / #80).
    import self_check  # noqa: F401

    server = Server("tausik-project")
    from tenancy import ProjectUnresolved, ServiceRegistry

    registry = ServiceRegistry(args.project, _get_service)
    # The listing needs A service to read the active task's scope ACL from. Pinned, that is
    # the one project; per request, it is whichever project the working directory resolves to
    # at the moment the host asks — and if none does, the listing must still answer, because a
    # host that cannot list tools reads as a dead server rather than as an unopened project.
    svc = registry.service(registry.pinned) if registry.pinned else None

    # state-roundtrip-regression-sync-corrupts: warm the git-native projection off
    # the request path. session_open's `sync_suggested` section is watchdog-bounded,
    # and its FIRST call is the only one /start ever makes — cold module import plus
    # a cold read of the whole tree overran that budget every session, so the signal
    # was permanently invisible. Daemon thread: nothing waits on it, and it only
    # warms I/O (no memoized verdict — that would go stale on the next DB write).
    import threading

    from state_triggers import prewarm

    if svc is not None:
        threading.Thread(target=prewarm, args=(svc,), name="state-prewarm", daemon=True).start()

    # mcp-scope-tools-exposure: expose only the tools the active task's
    # scope_tools ACL allows (∪ always-safe-core). Fail-open by construction —
    # feature off / no active task / nobody declared scope_tools / any error →
    # all tools. Hiding is a UX+token optimization, NOT the security barrier:
    # call_tool and the write-gate are untouched, so a hidden tool called
    # directly still passes existing enforcement.
    # The list depends on that state, so it carries ttlMs=0 / cacheScope=private
    # (MCP 2026-07-28 CacheableResult): a client must not reuse a stale surface.
    # Два фильтра, и порядок важен: `expose_tools` решает, КАКИЕ инструменты
    # видны (ACL области задачи), `apply_tiers` — насколько подробно. Сперва
    # состав, потом подробность: урезать схему у инструмента, который всё
    # равно скрыт, значило бы платить указателем за невидимое.
    from mcp_tool_scope import LIST_CACHE_HINT, expose_tools
    from mcp_tool_tiers import apply_tiers

    def _listing_service():
        """A service for the ACL read, or None. Never raises: see the comment above `svc`."""
        if svc is not None:
            return svc
        try:
            return registry.for_call()
        except Exception:  # noqa: BLE001 - an unopened project still gets the full tool list
            return None

    @server.list_tools()
    async def list_tools():
        tools = [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in apply_tiers(expose_tools(TOOLS, _listing_service()))
        ]
        return ListToolsResult.model_validate({"tools": tools, **LIST_CACHE_HINT})

    # TAUSIK exposes no prompts and no resources — only tools. Some hosts (OpenCode)
    # request prompts/list and resources/list unconditionally, without consulting the
    # advertised capabilities, and log a `-32601 Method not found` for each. The
    # server is healthy and its tools work, but the log reads like a dead server: a
    # user chasing a real bug wasted a debugging cycle concluding "TAUSIK MCP is
    # down". Answering with an empty list costs nothing and keeps the log honest.
    @server.list_prompts()
    async def list_prompts():
        return []

    @server.list_resources()
    async def list_resources():
        return []

    import asyncio

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        # BEFORE the handler, not inside its try: once handle_tool runs the write
        # has already happened and there is nothing left to refuse. One point in
        # the dispatcher rather than a check per tool — the swallowing was a
        # property of the way any tool is called, not of any one of them. Kept
        # out of the except below so the host log does not read a refused typo as
        # a crashed tool: nothing failed, the call was turned away.
        try:
            reject_unknown_arguments(TOOLS, name, arguments)
        except ValueError as e:
            return [TextContent(type="text", text=_error_reply(TOOLS, name, e))]
        try:
            project_dir = registry.resolve()
            call_svc = registry.service(project_dir)
        except ProjectUnresolved as e:
            # NOT a traceback and NOT a crash: the server is healthy, the request simply has
            # no project. The agent gets the two ways out, which is the difference between an
            # error it can act on and one it reports to a human.
            return [TextContent(type="text", text=str(e))]

        def _run_tool():
            with registry.call_context(project_dir):
                return handle_tool(call_svc, name, arguments)

        try:
            result = await asyncio.to_thread(_run_tool)
            return [TextContent(type="text", text=result)]
        except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
            # Full traceback to host stderr for diagnostics, mirroring
            # tausik-brain server. The text reply to the agent stays minimal
            # so frame-locals (potentially containing secrets/paths) do not
            # leak into model context.
            print(
                f"[tausik-project] tool {name!r} failed:\n{traceback.format_exc()}",
                file=sys.stderr,
            )
            return [TextContent(type="text", text=_error_reply(TOOLS, name, e))]

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
