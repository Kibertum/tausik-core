"""tausik-brain MCP tool definitions — shared cross-project knowledge."""

from __future__ import annotations

_CATEGORY_ENUM = ["decisions", "web_cache", "patterns", "gotchas"]

TOOLS = [
    {
        "name": "brain_search",
        "description": (
            "Search the shared cross-project brain (decisions, cached web "
            "results, patterns, gotchas). Local SQLite FTS5 mirror first, "
            "Notion /search fallback when the local index has fewer hits "
            "than `limit`. Results merge with dedup by Notion page id; "
            "local hits win. Returns markdown."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text query. FTS5 operators are neutralized.",
                },
                "category": {
                    "type": "string",
                    "enum": _CATEGORY_ENUM,
                    "description": "Restrict to a single category (optional).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results across categories (default 10).",
                },
                "use_notion_fallback": {
                    "type": "boolean",
                    "description": "Hit Notion when local < limit hits (default true).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "brain_get",
        "description": (
            "Retrieve one brain record by Notion page id. Local first, "
            "Notion pages.retrieve fallback. Returns markdown."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Notion page id (with or without dashes).",
                },
                "category": {
                    "type": "string",
                    "enum": _CATEGORY_ENUM,
                    "description": "Which brain table to look up in.",
                },
                "use_notion_fallback": {
                    "type": "boolean",
                    "description": "Allow Notion fallback on local miss (default true).",
                },
            },
            "required": ["id", "category"],
        },
    },
]
