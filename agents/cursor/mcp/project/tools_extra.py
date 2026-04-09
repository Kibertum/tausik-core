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
]
