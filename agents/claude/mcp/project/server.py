#!/usr/bin/env python3
"""TAUSIK MCP server — project management via SQLite.

Tools defined in tools.py, handlers in handlers.py.
"""

from __future__ import annotations

import argparse
import os
import sys


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Project root directory")
    args = parser.parse_args()

    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool
    except ImportError:
        print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    from handlers import handle_tool
    from tools import TOOLS

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
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
