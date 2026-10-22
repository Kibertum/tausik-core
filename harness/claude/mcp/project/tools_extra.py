"""TAUSIK MCP tool definitions — extra tools: dead ends, explorations, audit, gates, skills, maintenance."""

from __future__ import annotations

TOOLS_EXTRA = [
    # === Pooled verification (1.11.3 Track A; parity with verify --tasks /
    # verify --story / verify --epic and story|epic done --verify-handle) ===
    {
        "name": "tausik_verify_cohort",
        "description": (
            "Verify >=2 explicit tasks in one union-scope pass. Reuse fails on member, state, "
            "gate, security, evidence, or dependency drift. CLI: `verify --tasks`."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Task slugs forming the cohort (>=2).",
                },
                "scope": {
                    "type": "string",
                    "enum": ["lightweight", "standard", "high", "critical", "manual"],
                    "description": "SENAR Rule 5 verification tier (default standard).",
                },
            },
            "required": ["tasks"],
        },
    },
    {
        "name": "tausik_verify_hierarchy",
        "description": (
            "Verify a story or epic's review-ready non-done tasks in one pass; refuses empty "
            "or one-task pools. CLI: `verify --story/--epic`."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["story", "epic"]},
                "slug": {"type": "string"},
                "scope": {
                    "type": "string",
                    "enum": ["lightweight", "standard", "high", "critical", "manual"],
                    "description": "SENAR Rule 5 verification tier (default standard).",
                },
            },
            "required": ["kind", "slug"],
        },
    },
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
                    "description": "Skill name to install (e.g. pdf, docs, excel)",
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
        "description": "Add a TAUSIK-compatible skill repository. Clones repo, validates tausik-skills.json, indexes available skills. Third-party URLs require force=true (opt-in to trust)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Git URL (e.g. https://github.com/Kibertum/tausik-skills)",
                },
                "force": {
                    "type": "boolean",
                    "description": "Required true when URL is not the official Kibertum/tausik-skills repo",
                },
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
    {
        "name": "tausik_skill_catalog",
        "description": "Discovery: list skills offered by configured/cloned skill repos. Optional repo filter; optional JSON output.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repo name (see tausik_skill_repo_list). Omit to list all repos.",
                },
                "as_json": {
                    "type": "boolean",
                    "description": "Return JSON instead of human-readable text. Default false.",
                },
            },
        },
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
        "name": "tausik_graph",
        "description": "Build, inspect, or summarize the project's evidence-backed artifact graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": ["build", "show", "status"],
                    "description": "What to do. Default: status.",
                },
                "path": {
                    "type": "string",
                    "description": "Repo-relative path — required by command=show.",
                },
                "rebuild": {
                    "type": "boolean",
                    "description": "command=build: drop what is stored first.",
                },
            },
        },
    },
    {
        "name": "tausik_doctor",
        "description": "Health diagnostic — venv + DB + MCP + skills + drift + config + gates + session",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tausik_memory_brief",
        "description": (
            "memory-only playbook in one call: profile, do/dont, decide_vs_memory, "
            "next_hint. Budgeted (default max_bytes=8192). Never starts a session."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "max_bytes": {
                    "type": "integer",
                    "description": "Hard UTF-8 budget for the JSON body (default 8192).",
                    "minimum": 512,
                    "maximum": 65536,
                },
            },
        },
    },
    {
        "name": "tausik_verify",
        "description": (
            "Run verification gates. With task_slug, scope to its relevant files; without it, "
            "run the full suite. Pass the returned verify_handle (valid for 1 hour, SINGLE-USE) to "
            "tausik_task_done. File or gate changes invalidate the handle."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_slug": {
                    "type": "string",
                    "description": (
                        "Task slug to verify against. Optional: when omitted "
                        "the run is full-suite and is NOT cached (matches "
                        "CLI `tausik verify` without --task)."
                    ),
                },
                "scope": {
                    "type": "string",
                    "enum": ["lightweight", "standard", "high", "critical", "manual"],
                    "description": (
                        "SENAR Rule 5 verification tier. Defaults to "
                        "`standard`. Used as the recorded scope label."
                    ),
                },
                "trigger": {
                    "type": "string",
                    "enum": ["verify", "task-done"],
                    "description": (
                        "Gate trigger to run. Defaults to `verify` (heavy "
                        "gates). `task-done` exists for parity / dry-run."
                    ),
                },
                "full_path": {
                    "type": "boolean",
                    "description": "memory-only: run only when the owner asks. Default is profile=disabled.",
                },
            },
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
    # Roles CRUD + stack_scaffold moved to tools_extra_admin.TOOLS_EXTRA_ADMIN
    # (`v14b-tools-extra-preempt-split` — was 399/400 lines).
    # === MCP self-check (v14b-mcp-stale-module-detector) ===
    {
        "name": "tausik_self_check",
        "description": (
            "Detect stale MCP modules and sibling project servers. Call from /start; "
            "restart the IDE on drift and use the CLI meanwhile."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    # === Session-open compound RPC (v14b-session-open-compound-rpc) ===
    {
        "name": "tausik_session_open",
        "description": (
            "Open /start in one call: session, context, status, handoff, active/blocked tasks, "
            "and self-check. Sections fail independently with inline errors."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tausik_tool_schema",
        "description": (
            "Return a tool's full input schema, search tool names, or list all names. "
            "Use before calling a deferred-schema tool."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Exact tool name."},
                "query": {
                    "type": "string",
                    "description": "Substring of a tool name; empty string lists all names.",
                },
            },
        },
    },
]
