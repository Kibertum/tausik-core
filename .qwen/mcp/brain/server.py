#!/usr/bin/env python3
"""tausik-brain MCP server — shared cross-project knowledge.

Thin launcher. Tools defined in tools.py; dispatch in handlers.py.
The server does not read brain config at startup — tools themselves
return a "not configured" hint when called on a disabled brain.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import traceback


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Project root directory")
    args = parser.parse_args()

    # Ensure project scripts/ and this mcp dir are on sys.path so handlers.py
    # can import brain_* modules. Layout: .claude/mcp/brain/ → .claude/scripts/
    # (matches agents/claude/mcp/project/server.py).
    this_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.normpath(os.path.join(this_dir, "..", "..", "scripts"))
    for p in (this_dir, scripts_dir):
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)

    # Pin cwd so any relative-path lookups (e.g. basename for project_name)
    # resolve against the project root.
    if args.project and os.path.isdir(args.project):
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

    server = Server("tausik-brain")

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

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            result = await asyncio.to_thread(handle_tool, name, arguments)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            print(
                f"[tausik-brain] tool {name!r} failed:\n{traceback.format_exc()}",
                file=sys.stderr,
            )
            return [TextContent(type="text", text=f"Error: {e}")]

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
