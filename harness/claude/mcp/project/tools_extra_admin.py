"""TAUSIK MCP tool definitions — admin tools: role CRUD + stack scaffold.

Split from tools_extra.py (`v14b-tools-extra-preempt-split`) — the parent
file was at 399/400 lines, one line off the filesize gate, so the next
tool addition would have failed. Roles + stack_scaffold are a cohesive
"admin / configuration-modifying" group; read-only stack tools and the
core gate / verify entries stay in tools_extra.py.
"""

from __future__ import annotations

TOOLS_EXTRA_ADMIN = [
    # === Roles (CRUD; hybrid SQLite + markdown profile) ===
    {
        "name": "tausik_role_list",
        "description": "All roles ordered by slug, with task usage count",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tausik_role_show",
        "description": "Role row + markdown profile + linked task count",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_role_create",
        "description": "Insert role row. Optionally clone profile from `extends` slug.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "extends": {
                    "type": "string",
                    "description": "Existing role slug to clone profile from",
                },
            },
            "required": ["slug", "title"],
        },
    },
    {
        "name": "tausik_role_update",
        "description": "Update role title/description metadata",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_role_delete",
        "description": "Delete role. Refuses if tasks reference it (use force=true to override).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "force": {
                    "type": "boolean",
                    "description": "Delete even if tasks reference this role",
                },
            },
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_role_seed",
        "description": "Bootstrap roles from harness/roles/*.md + distinct task.role values (idempotent)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tausik_stack_scaffold",
        "description": "Generate skeleton .tausik/stacks/<name>/{stack.json, guide.md}. Refuses overwrite without force.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "kebab-case stack slug"},
                "extends_builtin": {
                    "type": "string",
                    "description": "Built-in stack to extend (e.g. 'python'). Sets extends:builtin:<X>.",
                },
                "force": {
                    "type": "boolean",
                    "description": "Overwrite existing files",
                },
            },
            "required": ["name"],
        },
    },
]
