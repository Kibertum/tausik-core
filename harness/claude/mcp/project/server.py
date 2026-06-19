#!/usr/bin/env python3
"""TAUSIK MCP server — project management via SQLite.

Tools defined in tools.py, handlers in handlers.py.
"""

from __future__ import annotations

import argparse
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


def _usage_hint(tools: list[dict], name: str) -> str:
    """Compact usage line generated from the tool's inputSchema.

    v15p-self-correcting-cli: appended to error replies so the agent can
    correct the call in one retry instead of guessing argument names.
    """
    tool = next((t for t in tools if t.get("name") == name), None)
    if not tool:
        return ""
    schema = tool.get("inputSchema") or {}
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    if not props:
        return ""
    parts = [
        f"{key}{'*' if key in required else ''}:{spec.get('type', 'any')}"
        for key, spec in props.items()
    ]
    return f"usage: {name}({', '.join(parts)}) — * = required"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Project root directory")
    args = parser.parse_args()

    # Pin cwd to --project so handlers that resolve paths relative to cwd
    # (e.g. _project_dir() in handlers.py, cq_client config lookup) read the
    # right project regardless of the host's launch directory. Mirrors
    # tausik-brain server.py behavior — keeps the two MCP servers symmetric.
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

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in TOOLS
        ]

    import asyncio

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
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
            reply = f"Error: {e}"
            hint = _usage_hint(TOOLS, name)
            if hint:
                reply += "\n" + hint
            return [TextContent(type="text", text=reply)]

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
