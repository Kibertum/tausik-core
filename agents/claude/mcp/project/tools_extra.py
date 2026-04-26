"""TAUSIK MCP tool definitions — extra tools: dead ends, explorations, audit, gates, skills, maintenance."""

from __future__ import annotations

TOOLS_EXTRA = [
    # === Dead End Documentation (SENAR Rule 9.4) ===
    {
        "name": "tausik_dead_end",
        "description": "Document a dead end — failed approach with reason. SENAR Rule 9.4",
        "inputSchema": {
            "type": "object",
            "properties": {
                "approach": {"type": "string", "description": "What was tried"},
                "reason": {"type": "string", "description": "Why it failed"},
                "task_slug": {
                    "type": "string",
                    "description": "Related task slug (optional)",
                },
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["approach", "reason"],
        },
    },
    # === Exploration (SENAR Section 5.1) ===
    {
        "name": "tausik_explore_start",
        "description": "Start a time-bounded exploration (SENAR Section 5.1). No production code allowed",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Exploration topic"},
                "time_limit": {
                    "type": "integer",
                    "description": "Time limit in minutes (default 30)",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "tausik_explore_end",
        "description": "End current exploration with optional summary",
        "inputSchema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "What was discovered"},
                "create_task": {
                    "type": "boolean",
                    "description": "Create a task from exploration findings",
                },
            },
        },
    },
    {
        "name": "tausik_explore_current",
        "description": "Show current active exploration (if any)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # === Audit (SENAR Rule 9.5) ===
    {
        "name": "tausik_audit_check",
        "description": "Check if periodic audit is needed (SENAR Rule 9.5)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tausik_audit_mark",
        "description": "Mark periodic audit as completed for current session. Requires active session",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # === Gates Management ===
    {
        "name": "tausik_gates_status",
        "description": "Show quality gates status — enabled/disabled, grouped by stack",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tausik_gates_enable",
        "description": "Enable a quality gate by name (e.g. pytest, ruff, tsc, eslint). Use gates_status to see available gates",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Gate name (e.g. tsc, eslint, pytest)",
                }
            },
            "required": ["name"],
        },
    },
    {
        "name": "tausik_gates_disable",
        "description": "Disable a quality gate by name. Use gates_status to see available gates",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Gate name"}},
            "required": ["name"],
        },
    },
    # === Skill Lifecycle ===
    {
        "name": "tausik_skill_list",
        "description": "List all skills: active (installed), vendored (available to activate), and available from repos",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tausik_skill_activate",
        "description": "Activate a vendored skill by name. Copies skill to IDE skills directory and persists in config. Use skill_list to see available skills",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill name (e.g. ui-ux-pro-max, seo-audit)",
                }
            },
            "required": ["name"],
        },
    },
    {
        "name": "tausik_skill_deactivate",
        "description": "Deactivate a vendor skill by name. Removes from IDE skills directory. Core skills cannot be deactivated",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Skill name"}},
            "required": ["name"],
        },
    },
    # === Skill Install ===
    {
        "name": "tausik_skill_install",
        "description": "Install a skill from a TAUSIK-compatible repo. Copies skill files, installs pip dependencies. Use skill_repo_list to see available repos and skills",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill name to install (e.g. jira, bitrix24)",
                }
            },
            "required": ["name"],
        },
    },
    {
        "name": "tausik_skill_uninstall",
        "description": "Uninstall a skill completely (remove files and config)",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Skill name"}},
            "required": ["name"],
        },
    },
    {
        "name": "tausik_skill_repo_add",
        "description": "Add a TAUSIK-compatible skill repository. Clones repo, validates tausik-skills.json, indexes available skills",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Git URL (e.g. https://github.com/Kibertum/tausik-skills)",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "tausik_skill_repo_remove",
        "description": "Remove a skill repository",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Repo name"}},
            "required": ["name"],
        },
    },
    {
        "name": "tausik_skill_repo_list",
        "description": "List configured skill repositories and their available skills",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # === Maintenance ===
    {
        "name": "tausik_update_claudemd",
        "description": "Update CLAUDE.md dynamic section (session, tasks, version)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tausik_fts_optimize",
        "description": "Optimize FTS5 full-text search indexes",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # === Stack registry (read + scaffold) ===
    {
        "name": "tausik_stack_list",
        "description": "List all registered stacks (built-in + user) with source and gate count",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tausik_stack_show",
        "description": "Resolved stack decl (built-in + user override merged) with source tracking",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "tausik_stack_lint",
        "description": "Validate every user override under .tausik/stacks/<name>/stack.json",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tausik_stack_diff",
        "description": "Unified diff of built-in vs user override for one stack",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "tausik_doctor",
        "description": "Health diagnostic — venv + DB + MCP + skills + drift + config + gates + session",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tausik_verify",
        "description": "Ad-hoc scoped verify for a task; records to verify cache",
        "inputSchema": {
            "type": "object",
            "properties": {"task_slug": {"type": "string"}},
            "required": ["task_slug"],
        },
    },
    {
        "name": "tausik_stack_reset",
        "description": "Remove user override at .tausik/stacks/<name>/ (restore built-in default)",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "tausik_stack_export",
        "description": "Print resolved (built-in + user merged) stack decl as JSON",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
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
        "description": "Bootstrap roles from agents/roles/*.md + distinct task.role values (idempotent)",
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
