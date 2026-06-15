"""TAUSIK MCP tool definitions — RENAR SPEC artifacts (v16r-spec-types).

Kept in its own module (filesize hygiene). ``type`` is a CLOSED list of 9 —
enforced both by the enum here and the service + DB CHECK.
"""

from __future__ import annotations

_SPEC_TYPES = ["ARCH", "API", "DATA", "INT", "PROC", "UI", "AI", "SEC", "OPS"]
_SPEC_RELATIONS = ["implements", "constrained_by"]
_SPEC_STATUSES = ["draft", "active", "deprecated"]

TOOLS_SPEC = [
    {
        "name": "tausik_spec_add",
        "description": "Create a RENAR SPEC artifact. type is a CLOSED list of 9 (ARCH/API/DATA/INT/PROC/UI/AI/SEC/OPS) — a new type requires a standard amendment, not a free-text value. version is required.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "type": {"type": "string", "enum": _SPEC_TYPES, "description": "Closed SPEC type"},
                "title": {"type": "string"},
                "version": {"type": "string", "description": "e.g. v1, 1.0-draft"},
                "content_ref": {
                    "type": "string",
                    "description": "Pointer to the spec doc (path/URL)",
                },
                "status": {
                    "type": "string",
                    "enum": _SPEC_STATUSES,
                    "description": "Default draft",
                },
            },
            "required": ["slug", "type", "title", "version"],
        },
    },
    {
        "name": "tausik_spec_list",
        "description": "List SPECs, optionally filtered by type. Returns JSON rows.",
        "inputSchema": {
            "type": "object",
            "properties": {"type": {"type": "string", "enum": _SPEC_TYPES}},
        },
    },
    {
        "name": "tausik_spec_show",
        "description": "Show a SPEC plus the tasks linked to it (JSON).",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_spec_update",
        "description": "Patch mutable SPEC fields (title, version, content_ref, status). type and slug are immutable.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "title": {"type": "string"},
                "version": {"type": "string"},
                "content_ref": {"type": "string"},
                "status": {"type": "string", "enum": _SPEC_STATUSES},
            },
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_spec_delete",
        "description": "Delete a SPEC (cascades its task links).",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_spec_link",
        "description": "Link a task to a SPEC it implements / is constrained by. Both must exist (no silent dangling link).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_slug": {"type": "string"},
                "spec_slug": {"type": "string"},
                "relation": {
                    "type": "string",
                    "enum": _SPEC_RELATIONS,
                    "description": "Default implements",
                },
            },
            "required": ["task_slug", "spec_slug"],
        },
    },
    {
        "name": "tausik_spec_unlink",
        "description": "Remove a task↔SPEC link.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_slug": {"type": "string"},
                "spec_slug": {"type": "string"},
                "relation": {
                    "type": "string",
                    "enum": _SPEC_RELATIONS,
                    "description": "Default implements",
                },
            },
            "required": ["task_slug", "spec_slug"],
        },
    },
    {
        "name": "tausik_spec_search",
        "description": "FTS5 search over SPEC slug/title/content_ref (JSON rows).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "description": "Default 20"},
            },
            "required": ["query"],
        },
    },
]
