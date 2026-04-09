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
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any


def _setup_paths(project_dir: str) -> None:
    """Add MCP package and scripts dirs to sys.path."""
    mcp_dir = os.path.dirname(os.path.abspath(__file__))
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)
    # Find scripts/ relative to this file (../../scripts from mcp/codebase-rag/)
    scripts_dir = os.path.normpath(os.path.join(mcp_dir, "..", "..", "scripts"))
    if os.path.isdir(scripts_dir) and scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


def _get_rag_store(project_dir: str):
    """Create FTS5-based RAG store."""
    from rag_store import RAGStore

    db_path = os.path.join(project_dir, ".tausik", "rag", "rag.db")
    return RAGStore(db_path)


def _get_web_cache(project_dir: str):
    """Create web search cache."""
    from rag_web_cache import WebCache

    db_path = os.path.join(project_dir, ".tausik", "rag", "web_cache.db")
    return WebCache(db_path)


def _get_backend(project_dir: str):
    """Create SQLiteBackend for knowledge search."""
    from project_backend import SQLiteBackend

    db_path = os.path.join(project_dir, ".tausik", "tausik.db")
    return SQLiteBackend(db_path)


def _format_code_results(results: list[dict]) -> str:
    """Format code search results for display."""
    if not results:
        return "No code matches found. Try different keywords or run `reindex` first."
    lines = []
    seen_files: dict[str, int] = {}
    for r in results:
        fp = r["file_path"]
        seen_files[fp] = seen_files.get(fp, 0) + 1
        loc = f":{r['start_line']}-{r['end_line']}" if r.get("start_line") else ""
        lang = f" [{r['language']}]" if r.get("language") else ""
        lines.append(f"--- {fp}{loc}{lang} ---")
        # Truncate long content
        content = r["content"]
        if len(content) > 1500:
            content = content[:1500] + "\n... (truncated)"
        lines.append(content)
        lines.append("")
    header = f"Found {len(results)} chunks across {len(seen_files)} files:\n"
    return header + "\n".join(lines)


def _format_knowledge_results(results: dict[str, list]) -> str:
    """Format knowledge search results."""
    if not any(results.values()):
        return "No knowledge matches found."
    lines = []
    for scope, items in results.items():
        if not items:
            continue
        lines.append(f"\n=== {scope.upper()} ({len(items)} results) ===")
        for item in items[:8]:
            if "slug" in item:
                status = f" [{item.get('status', '')}]" if item.get("status") else ""
                lines.append(f"  {item['slug']}: {item.get('title', '')}{status}")
                if item.get("goal"):
                    lines.append(f"    Goal: {item['goal'][:150]}")
            elif "decision" in item:
                lines.append(f"  #{item.get('id', '?')}: {item['decision'][:150]}")
            elif "query" in item:
                lines.append(f"  [{item.get('created_at', '')}] {item['query'][:100]}")
            elif "title" in item:
                lines.append(
                    f"  {item.get('title', '')}: {item.get('content', '')[:120]}"
                )
            else:
                lines.append(f"  {str(item)[:150]}")
    return "\n".join(lines)


def _find_related_tasks(be, file_paths: list[str]) -> str:
    """Find tasks whose relevant_files match any of the given paths."""
    all_tasks = be.task_list()
    related = []
    for task in all_tasks:
        rf = task.get("relevant_files")
        if not rf:
            continue
        try:
            files = json.loads(rf) if isinstance(rf, str) else rf
        except (json.JSONDecodeError, TypeError):
            files = [rf] if isinstance(rf, str) else []
        for fp in files:
            if any(fp in path or path in fp for path in file_paths):
                status = f" [{task['status']}]" if task.get("status") else ""
                related.append(f"  {task['slug']}: {task.get('title', '')}{status}")
                break
    return "\n".join(related)


def _extract_relevant_files(tasks: list[dict]) -> list[str]:
    """Extract unique file paths from tasks' relevant_files."""
    files: list[str] = []
    seen: set[str] = set()
    for task in tasks:
        rf = task.get("relevant_files")
        if not rf:
            continue
        try:
            items = json.loads(rf) if isinstance(rf, str) else rf
        except (json.JSONDecodeError, TypeError):
            items = [rf] if isinstance(rf, str) else []
        for f in items:
            if f and f not in seen:
                seen.add(f)
                files.append(f)
    return files


def _staleness_report(be) -> dict:
    """Analyze knowledge staleness."""
    # Count done tasks
    done_tasks = be.task_list("done")
    active_tasks = be.task_list("active")
    planning_tasks = be.task_list("planning")
    memories = be.memory_list(n=1000)

    # Find old done tasks (completed > 30 days ago)
    now = datetime.now(timezone.utc)
    stale_tasks = []
    for t in done_tasks:
        if t.get("completed_at"):
            try:
                completed = datetime.fromisoformat(t["completed_at"])
                age_days = (now - completed).days
                if age_days > 30:
                    stale_tasks.append({"slug": t["slug"], "age_days": age_days})
            except (ValueError, TypeError):
                pass

    return {
        "total_tasks": len(done_tasks) + len(active_tasks) + len(planning_tasks),
        "done_tasks": len(done_tasks),
        "active_tasks": len(active_tasks),
        "stale_done_tasks": len(stale_tasks),
        "total_memories": len(memories),
        "recommendation": (
            f"Archive {len(stale_tasks)} done tasks older than 30 days"
            if stale_tasks
            else "Knowledge base is clean"
        ),
    }


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

    _setup_paths(args.project)
    server = Server("tausik-codebase-rag")
    project_dir = args.project

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="search_code",
                description="Search project source code using full-text search. Use for finding implementations, functions, patterns in the codebase.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (keywords, function names, patterns)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results (default 15)",
                            "default": 15,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="search_knowledge",
                description="Search project knowledge base: tasks, memory, decisions. Use for finding past decisions, task history, learned patterns.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "scope": {
                            "type": "string",
                            "description": "Scope: all, tasks, memory, decisions",
                            "default": "all",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="reindex",
                description="Reindex project source code. Run after significant code changes.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["incremental", "full"],
                            "description": "incremental (git-changed only) or full (all files)",
                            "default": "incremental",
                        },
                    },
                },
            ),
            Tool(
                name="rag_status",
                description="Get RAG index health, knowledge staleness report, and recommendations.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="archive_done",
                description="Archive completed tasks older than N days. Moves them from active queries but preserves in search index. Reduces noise in task lists.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "older_than_days": {
                            "type": "integer",
                            "description": "Archive tasks completed more than N days ago (default 30)",
                            "default": 30,
                        },
                    },
                },
            ),
            Tool(
                name="cache_web_result",
                description="Cache a web search result for future reuse. Saves tokens by avoiding repeated web fetches. Call after WebFetch/WebSearch to store the result.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query or topic",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to cache (web page text, search results, etc.)",
                        },
                        "url": {
                            "type": "string",
                            "description": "Source URL (optional)",
                            "default": "",
                        },
                        "ttl_hours": {
                            "type": "integer",
                            "description": "Cache lifetime in hours (default 24)",
                            "default": 24,
                        },
                    },
                    "required": ["query", "content"],
                },
            ),
            Tool(
                name="search_web_cache",
                description="Search cached web results BEFORE making new web requests. Returns cached content if available and fresh. Saves tokens on repeated lookups.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {
                            "type": "integer",
                            "description": "Max results (default 5)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
        ]

    import asyncio

    def _sync_call_tool(name: str, arguments: dict) -> str:
        """All tool logic runs here — in a thread, not blocking the event loop."""
        if name == "search_code":
            store = _get_rag_store(project_dir)
            try:
                results = store.search(arguments["query"], arguments.get("limit", 15))
                output = _format_code_results(results)
                if results:
                    try:
                        be = _get_backend(project_dir)
                        found_files = list({r["file_path"] for r in results})
                        related = _find_related_tasks(be, found_files)
                        if related:
                            output += "\n\n=== RELATED TASKS ===\n" + related
                        be.close()
                    except Exception:
                        pass
                return output
            finally:
                store.close()

        elif name == "search_knowledge":
            be = _get_backend(project_dir)
            try:
                results = be.search_all(
                    arguments["query"],
                    arguments.get("scope", "all"),
                )
                output = _format_knowledge_results(results)
                if results.get("tasks"):
                    files = _extract_relevant_files(results["tasks"])
                    if files:
                        output += "\n\n=== CODE REFERENCES ===\n"
                        output += "\n".join(f"  {f}" for f in files)
                return output
            finally:
                be.close()

        elif name == "reindex":
            store = _get_rag_store(project_dir)
            try:
                from rag_indexer import index_full, index_incremental

                mode = arguments.get("mode", "incremental")
                if mode == "full":
                    stats = index_full(project_dir, store)
                else:
                    stats = index_incremental(project_dir, store)
                return json.dumps(stats, indent=2)
            finally:
                store.close()

        elif name == "rag_status":
            store = _get_rag_store(project_dir)
            try:
                code_status = store.status()
            finally:
                store.close()
            be = _get_backend(project_dir)
            try:
                staleness = _staleness_report(be)
            finally:
                be.close()
            # Web cache status (optional — DB may not exist yet)
            web_status: dict[str, Any] = {}
            try:
                cache = _get_web_cache(project_dir)
                web_status = cache.status()
                cache.close()
            except Exception:
                web_status = {"total_entries": 0}
            return json.dumps(
                {
                    "code_index": code_status,
                    "knowledge": staleness,
                    "web_cache": web_status,
                },
                indent=2,
            )

        elif name == "archive_done":
            be = _get_backend(project_dir)
            try:
                days = arguments.get("older_than_days", 30)
                return _archive_old_tasks(be, days)
            finally:
                be.close()

        elif name == "cache_web_result":
            cache = _get_web_cache(project_dir)
            try:
                cache.store(
                    query=arguments["query"],
                    content=arguments["content"],
                    url=arguments.get("url", ""),
                    ttl_hours=arguments.get("ttl_hours", 24),
                )
                return f"Cached: '{arguments['query']}' ({len(arguments['content'])} chars, TTL {arguments.get('ttl_hours', 24)}h)"
            finally:
                cache.close()

        elif name == "search_web_cache":
            cache = _get_web_cache(project_dir)
            try:
                results = cache.search(arguments["query"], arguments.get("limit", 5))
                if not results:
                    return "No cached results found. Proceed with web search."
                lines = [f"Found {len(results)} cached result(s):\n"]
                for r in results:
                    url = f" ({r['url']})" if r.get("url") else ""
                    lines.append(
                        f"--- {r['query']}{url} [fetched: {r['fetched_at']}] ---"
                    )
                    content = r["content"]
                    if len(content) > 2000:
                        content = content[:2000] + "\n... (truncated)"
                    lines.append(content)
                    lines.append("")
                return "\n".join(lines)
            finally:
                cache.close()

        return f"Unknown tool: {name}"

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            result = await asyncio.to_thread(_sync_call_tool, name, arguments)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )

    asyncio.run(_run())


def _archive_old_tasks(be, older_than_days: int) -> str:
    """Archive done tasks older than N days."""
    now = datetime.now(timezone.utc)
    done_tasks = be.task_list("done")
    archived = []

    for t in done_tasks:
        if not t.get("completed_at"):
            continue
        try:
            completed = datetime.fromisoformat(t["completed_at"])
            age_days = (now - completed).days
            if age_days > older_than_days:
                # Mark as archived by adding [archived] prefix to notes
                current_notes = t.get("notes", "") or ""
                if "[archived]" not in current_notes:
                    be.task_update(
                        t["slug"],
                        notes=f"[archived] {current_notes}".strip(),
                    )
                    archived.append(f"{t['slug']} ({age_days}d old)")
        except (ValueError, TypeError):
            continue

    if not archived:
        return f"No tasks older than {older_than_days} days to archive."
    return f"Archived {len(archived)} tasks:\n" + "\n".join(
        f"  - {a}" for a in archived
    )


if __name__ == "__main__":
    main()
