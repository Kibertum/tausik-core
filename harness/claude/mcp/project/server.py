#!/usr/bin/env python3
"""TAUSIK MCP server — project management via SQLite.

Tools defined in tools.py, handlers in handlers.py.
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys
import traceback


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


def declared_arguments(tools: list[dict], name: str) -> tuple[dict, set] | None:
    """The (properties, required) a tool's inputSchema declares, or None if unknown.

    The single unfolding of a tool schema in this module. Both the usage line
    and the unknown-argument check read it, so there is exactly one answer to
    "what may this tool be called with" — a second list of names next to the
    first is a future divergence, not a check.

    None means the schema knows nothing about `name`. That is not the same as
    "declares no arguments" ({}, set()), and the two callers below act on the
    distinction rather than collapsing it.
    """
    tool = next((t for t in tools if t.get("name") == name), None)
    if not tool:
        return None
    schema = tool.get("inputSchema") or {}
    return (schema.get("properties") or {}), set(schema.get("required") or [])


def _usage_hint(tools: list[dict], name: str) -> str:
    """Compact usage line generated from the tool's inputSchema.

    v15p-self-correcting-cli: appended to error replies so the agent can
    correct the call in one retry instead of guessing argument names.
    """
    declared = declared_arguments(tools, name)
    if declared is None:
        return ""
    props, required = declared
    if not props:
        return ""
    parts = [
        f"{key}{'*' if key in required else ''}:{spec.get('type', 'any')}"
        for key, spec in props.items()
    ]
    return f"usage: {name}({', '.join(parts)}) — * = required"


def _error_reply(tools: list[dict], name: str, exc: BaseException) -> str:
    """The one shape every refusal takes: the reason, then how to call it right.

    Both refusal paths in call_tool go through here so a rejected argument name
    and a handler that raised are answered identically. An agent that learns to
    read one reply can read the other.
    """
    reply = f"Error: {exc}"
    hint = _usage_hint(tools, name)
    return f"{reply}\n{hint}" if hint else reply


def reject_unknown_arguments(tools: list[dict], name: str, arguments: dict | None) -> None:
    """Raise ValueError when the call carries a name the tool never declared.

    mcp-server-drops-unknown-arguments-silently: an undeclared argument used to
    be dropped on the floor, so a typo in a parameter name was indistinguishable
    from success. `story` passed where the schema says `story_slug` created seven
    tasks with no story attached; nothing anywhere said a word, and the release
    count read them as missing. The CLI answers the same slip with a loud
    refusal, so the two surfaces disagreed about whether it was an error at all.

    Undeclared names only. Values of DECLARED arguments are already validated by
    the service below and refuse loudly (a 70-character slug against the limit of
    64 names itself and prints usage) — checking them again here would duplicate
    a working check in a second place.

    An unknown TOOL raises nothing: that is the dispatcher's refusal to make, and
    complaining about its arguments would name the wrong problem.
    """
    declared = declared_arguments(tools, name)
    if declared is None:
        return
    props, _ = declared
    unknown = [key for key in (arguments or {}) if key not in props]
    if not unknown:
        return
    parts = []
    for key in unknown:
        near = difflib.get_close_matches(key, list(props), n=1, cutoff=0.6)
        parts.append(f"{key!r} (did you mean {near[0]!r}?)" if near else repr(key))
    tail = f" {name} declares no arguments." if not props else ""
    raise ValueError(f"{name} does not declare {', '.join(parts)}.{tail}")


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
    except Exception:  # noqa: BLE001 — never let stdio setup crash the server
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Project root directory")
    args = parser.parse_args()

    # Pin cwd to --project so handlers that resolve paths relative to cwd
    # (_project_dir() in handlers_skill.py, the config lookup in handlers_cq.py,
    # the user-override path in handlers_stack.py) read the right project
    # regardless of the host's launch directory. Mirrors tausik-brain
    # server.py behavior — keeps the two MCP servers symmetric.
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
        from mcp.types import TextContent, Tool
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
    svc = _get_service(args.project)

    # state-roundtrip-regression-sync-corrupts: warm the git-native projection off
    # the request path. session_open's `sync_suggested` section is watchdog-bounded,
    # and its FIRST call is the only one /start ever makes — cold module import plus
    # a cold read of the whole tree overran that budget every session, so the signal
    # was permanently invisible. Daemon thread: nothing waits on it, and it only
    # warms I/O (no memoized verdict — that would go stale on the next DB write).
    import threading

    from state_triggers import prewarm

    threading.Thread(target=prewarm, args=(svc,), name="state-prewarm", daemon=True).start()

    # mcp-scope-tools-exposure: expose only the tools the active task's
    # scope_tools ACL allows (∪ always-safe-core). Fail-open by construction —
    # feature off / no active task / nobody declared scope_tools / any error →
    # all tools. Hiding is a UX+token optimization, NOT the security barrier:
    # call_tool and the write-gate are untouched, so a hidden tool called
    # directly still passes existing enforcement.
    from mcp_tool_scope import expose_tools

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in expose_tools(TOOLS, svc)
        ]

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
            result = await asyncio.to_thread(handle_tool, svc, name, arguments)
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
