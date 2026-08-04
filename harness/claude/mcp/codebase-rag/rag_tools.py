"""MCP tool schemas for the codebase-rag server.

Declarations only — no logic. Split out of server.py so the transport
module is not 60% wire-format literal, mirroring the sibling package
harness/claude/mcp/project (tools*.py + handlers_*.py).

`Tool` is imported at module level here, so this module must only be
imported AFTER server.main() has cleared its guarded `import mcp` —
otherwise a missing dependency surfaces as a traceback instead of the
"mcp package not installed" hint.
"""

from __future__ import annotations

from mcp.types import Tool


def tool_definitions() -> list[Tool]:
    """The server's advertised tool surface, in list_tools() order."""
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
            description=(
                "Reindex project source code. Run after significant code "
                "changes. Emits stderr progress every 100 files. "
                "v1.5: soft time budget defaults to 300s (truncated=true "
                "in result when exceeded); a hard timeout envelope "
                "(budget + 60s) guarantees the call never hangs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["incremental", "full"],
                        "description": "incremental (git-changed only) or full (all files)",
                        "default": "incremental",
                    },
                    "max_seconds": {
                        "type": "integer",
                        "description": (
                            "Soft time limit for full indexing (default "
                            "300s). Indexing stops cleanly when exceeded; "
                            "result includes truncated=true."
                        ),
                        "minimum": 1,
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
