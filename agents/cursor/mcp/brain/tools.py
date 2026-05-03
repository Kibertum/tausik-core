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
                "prefer_stack": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional stack hints (e.g. python, react). Matching rows get a "
                        "relevance boost after bm25 merge."
                    ),
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
    {
        "name": "brain_store_decision",
        "description": (
            "Record a project decision into the shared brain. Runs content "
            "through the scrubbing linter before writing to Notion; "
            "returns actionable errors if blocked. On success mirrors the "
            "page into the local SQLite for instant consistency."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Short title (required)."},
                "decision": {
                    "type": "string",
                    "description": "What was decided (required).",
                },
                "context": {"type": "string"},
                "rationale": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "stack": {"type": "array", "items": {"type": "string"}},
                "date": {
                    "type": "string",
                    "description": "ISO date; defaults to today.",
                },
                "generalizable": {"type": "boolean", "description": "Default true."},
                "superseded_by": {
                    "type": "string",
                    "description": "URL of superseding decision.",
                },
                "project_name": {
                    "type": "string",
                    "description": "Override project identity for hash. Default: cwd basename.",
                },
            },
            "required": ["name", "decision"],
        },
    },
    {
        "name": "brain_store_pattern",
        "description": (
            "Record a reusable pattern (architecture/design/idiom) into the "
            "shared brain. Scrubbed before write; mirrored locally on success. "
            "Optional artifact_taxonomy_kind (artifact|pattern|snippet); see "
            "docs/en/brain-artifact-taxonomy.md. Not persisted to Notion props in v1."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "when_to_use": {"type": "string"},
                "example": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "stack": {"type": "array", "items": {"type": "string"}},
                "date": {"type": "string"},
                "confidence": {
                    "type": "string",
                    "enum": ["experimental", "tested", "proven"],
                },
                "artifact_taxonomy_kind": {
                    "type": "string",
                    "enum": ["artifact", "pattern", "snippet"],
                    "description": "Logical card kind (validated; stripped before Notion write in v1).",
                },
                "scope": {
                    "type": "string",
                    "description": "Logical scope for the card (validated; not persisted to Notion v1); empty string rejected; required if brain.require_artifact_scope=true.",
                },
                "external_repo_url": {
                    "type": "string",
                    "description": (
                        "Optional https URL (canonical repo/submodule). Validated; "
                        "default reachability check; set brain.skip_external_repo_url_reachability_check to skip network; "
                        "not written to Notion props in v1."
                    ),
                },
                "confirm_high_risk": {
                    "type": "boolean",
                    "description": "Set true when draft shows risk_level high (human gate).",
                },
                "project_name": {"type": "string"},
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "brain_store_gotcha",
        "description": (
            "Record a gotcha / non-obvious trap into the shared brain. "
            "Scrubbed before write; mirrored locally on success. "
            "Optional artifact_taxonomy_kind — same contract as patterns; "
            "see docs/en/brain-artifact-taxonomy.md."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "wrong_way": {"type": "string"},
                "right_way": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "stack": {"type": "array", "items": {"type": "string"}},
                "date": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
                "evidence_url": {"type": "string"},
                "artifact_taxonomy_kind": {
                    "type": "string",
                    "enum": ["artifact", "pattern", "snippet"],
                    "description": "Logical card shape (validated; stripped before Notion write in v1).",
                },
                "scope": {
                    "type": "string",
                    "description": "Logical scope for the card (validated; not persisted to Notion v1); empty string rejected; required if brain.require_artifact_scope=true.",
                },
                "external_repo_url": {
                    "type": "string",
                    "description": (
                        "Optional https URL (canonical repo/submodule). Validated; "
                        "default reachability check; set brain.skip_external_repo_url_reachability_check to skip network; "
                        "not written to Notion props in v1."
                    ),
                },
                "confirm_high_risk": {
                    "type": "boolean",
                    "description": "Set true when draft shows risk_level high (human gate).",
                },
                "project_name": {"type": "string"},
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "brain_draft_artifact",
        "description": (
            "Dry-run artifact publish for pattern or gotcha: taxonomy, card, scrub, "
            "and classifier risk. No Notion write. Use before brain_store_pattern/gotcha "
            "when content may be project-specific."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["pattern", "gotcha"],
                    "description": "Artifact shape matching Notion category.",
                },
                "name": {"type": "string"},
                "description": {"type": "string"},
                "when_to_use": {"type": "string"},
                "example": {"type": "string"},
                "wrong_way": {"type": "string"},
                "right_way": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "stack": {"type": "array", "items": {"type": "string"}},
                "date": {"type": "string"},
                "confidence": {
                    "type": "string",
                    "enum": ["experimental", "tested", "proven"],
                },
                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                "evidence_url": {"type": "string"},
                "artifact_taxonomy_kind": {
                    "type": "string",
                    "enum": ["artifact", "pattern", "snippet"],
                },
                "scope": {"type": "string"},
                "external_repo_url": {
                    "type": "string",
                    "description": (
                        "Optional https URL — same validation as brain_store_pattern/gotcha."
                    ),
                },
            },
            "required": ["kind"],
        },
    },
    {
        "name": "brain_cache_web",
        "description": (
            "Cache a fetched web resource (docs page, StackOverflow answer, "
            "etc.) into the shared brain for cross-project reuse. Scrubbed "
            "before write; Content Hash auto-computed for dedup."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Page title or short label."},
                "url": {"type": "string"},
                "content": {"type": "string"},
                "query": {
                    "type": "string",
                    "description": "Original search/fetch query.",
                },
                "fetched_at": {"type": "string"},
                "ttl_days": {"type": "integer", "description": "Default 30."},
                "domain": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "project_name": {"type": "string"},
            },
            "required": ["name", "url", "content"],
        },
    },
]
