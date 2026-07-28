#!/usr/bin/env python3
"""TAUSIK MCP server -- codebase RAG + knowledge search.

Tools:
  search_code       — FTS5 search across indexed source code
  search_knowledge  — search project memory, decisions, tasks
  reindex           — full or incremental code reindexing
  rag_status        — index health + staleness report
  archive_done      — archive completed tasks older than N days
"""

from __future__ import annotations

import argparse
import os
import sys


# Hard per-call envelope (seconds). The soft budget lives inside the indexer
# (rag_indexer.DEFAULT_MAX_SECONDS); this is the last line of defense so an
# unexpected block (subprocess, fs walk, db lock) surfaces as an explicit
# error instead of an infinite MCP hang (v15p-fix-rag-reindex-hang).
TOOL_TIMEOUT_DEFAULT_SEC = 120
REINDEX_TIMEOUT_MARGIN_SEC = 60
_REINDEX_SOFT_DEFAULT_SEC = 300  # mirrors rag_indexer.DEFAULT_MAX_SECONDS


def _tool_timeout_sec(name: str, arguments: dict) -> float:
    """Hard timeout for a tool call: soft budget + margin for reindex."""
    if name == "reindex":
        soft = arguments.get("max_seconds") or _REINDEX_SOFT_DEFAULT_SEC
        return float(soft) + REINDEX_TIMEOUT_MARGIN_SEC
    return float(TOOL_TIMEOUT_DEFAULT_SEC)


def _setup_paths(project_dir: str) -> None:
    """Add MCP package and scripts dirs to sys.path."""
    mcp_dir = os.path.dirname(os.path.abspath(__file__))
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)
    # Find scripts/ relative to this file (../../scripts from mcp/codebase-rag/)
    scripts_dir = os.path.normpath(os.path.join(mcp_dir, "..", "..", "scripts"))
    if os.path.isdir(scripts_dir) and scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


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

    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent
    except ImportError:
        print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    _setup_paths(args.project)

    # Imported only AFTER the guard above: rag_tools imports mcp.types at module
    # level, so hoisting this would turn "mcp package not installed" from a
    # readable hint into an ImportError traceback.
    from rag_handlers import call_tool_sync
    from rag_tools import tool_definitions

    server = Server("tausik-codebase-rag")
    project_dir = args.project

    @server.list_tools()
    async def list_tools():
        return tool_definitions()

    # Empty prompts/resources — hosts that call prompts/list unconditionally (OpenCode)
    # must get an empty answer, not -32601, or the log slanders a healthy server.
    @server.list_prompts()
    async def list_prompts():
        return []

    @server.list_resources()
    async def list_resources():
        return []

    import asyncio

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        timeout_sec = _tool_timeout_sec(name, arguments)
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(call_tool_sync, name, arguments, project_dir),
                timeout=timeout_sec,
            )
            return [TextContent(type="text", text=result)]
        except (asyncio.TimeoutError, TimeoutError):
            return [
                TextContent(
                    type="text",
                    text=(
                        f"Error: tool '{name}' timed out after "
                        f"{int(timeout_sec)}s (hard envelope). Worker thread "
                        "abandoned — likely a blocked subprocess or filesystem "
                        "walk. For reindex: retry with a smaller max_seconds, "
                        "or check for stuck git processes."
                    ),
                )
            ]
        except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
            return [TextContent(type="text", text=f"Error: {e}")]

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
