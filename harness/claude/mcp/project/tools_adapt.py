"""TAUSIK MCP tool definitions — RENAR ADAPT artifacts (v16r-adapt).

Kept in its own module (filesize hygiene). ``category`` (findings) and ``role``
(signatures) are CLOSED lists — enforced both by the enum here and the service +
DB CHECK. Mirrored in harness/claude + harness/cursor.
"""

from __future__ import annotations

_FINDING_CATEGORIES = [
    "contradiction",
    "gap",
    "hidden-assumption",
    "feasibility",
    "regulatory",
    "terminology",
    "scope",
]
_SIGNATURE_ROLES = ["client", "architect"]
_LINK_TARGETS = ["task", "spec"]
_ADAPT_STATUSES = ["draft", "signed", "superseded"]

TOOLS_ADAPT = [
    {
        "name": "tausik_adapt_create",
        "description": "Create a RENAR ADAPT artifact header (§7). tz_ref (source TZ) is required. Starts in 'draft' for body parts + dual signature.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "title": {"type": "string"},
                "tz_ref": {"type": "string", "description": "Source TZ id, e.g. TZ-2026-001"},
            },
            "required": ["slug", "title", "tz_ref"],
        },
    },
    {
        "name": "tausik_adapt_interpret",
        "description": "Add a forward-interpretation entry (§7.4.3). tz_ref/citation/interpretation/scope_in/scope_out are MANDATORY; term_mapping + scenarios optional.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "adapt_slug": {"type": "string"},
                "tz_ref": {"type": "string", "description": "'ТЗ§N.N'"},
                "citation": {"type": "string"},
                "engineering_interpretation": {"type": "string"},
                "scope_in": {"type": "string"},
                "scope_out": {"type": "string"},
                "term_mapping": {"type": "string"},
                "scenarios": {"type": "string"},
            },
            "required": [
                "adapt_slug",
                "tz_ref",
                "citation",
                "engineering_interpretation",
                "scope_in",
                "scope_out",
            ],
        },
    },
    {
        "name": "tausik_adapt_finding",
        "description": "Add a backward finding to an ADAPT. category is a CLOSED list of 7 (contradiction/gap/hidden-assumption/feasibility/regulatory/terminology/scope) — a new category requires a standard amendment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "adapt_slug": {"type": "string"},
                "category": {"type": "string", "enum": _FINDING_CATEGORIES},
                "description": {"type": "string"},
                "tz_ref": {"type": "string"},
                "resolution": {"type": "string"},
            },
            "required": ["adapt_slug", "category", "description"],
        },
    },
    {
        "name": "tausik_adapt_sign",
        "description": "Record a dual signature (§7.5). role=architect signs the canonical ADAPT body with the project ed25519 key; role=client records a name+timestamp. Both roles present ⇒ status 'signed'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "adapt_slug": {"type": "string"},
                "role": {"type": "string", "enum": _SIGNATURE_ROLES},
                "signed_by": {"type": "string", "description": "Signer identity"},
            },
            "required": ["adapt_slug", "role", "signed_by"],
        },
    },
    {
        "name": "tausik_adapt_show",
        "description": "Show an ADAPT with its forward interpretations, backward findings, signatures and links (JSON).",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_adapt_list",
        "description": "List ADAPTs, optionally filtered by status (draft/signed/superseded). Returns JSON rows.",
        "inputSchema": {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": _ADAPT_STATUSES}},
        },
    },
    {
        "name": "tausik_adapt_delta",
        "description": "Create a delta-ADAPT superseding a parent (§7.6). The parent becomes 'superseded'; a later link to it is a FATAL dangling reference (§7.6.4).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "parent_slug": {"type": "string"},
                "new_slug": {"type": "string"},
                "title": {"type": "string"},
                "tz_ref": {"type": "string", "description": "delta-TZ id"},
            },
            "required": ["parent_slug", "new_slug", "title", "tz_ref"],
        },
    },
    {
        "name": "tausik_adapt_link",
        "description": "Link an ADAPT to a task or spec. target must exist (no silent dangling link); linking to a SUPERSEDED ADAPT is a FATAL error (§7.6.4).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "adapt_slug": {"type": "string"},
                "target_type": {"type": "string", "enum": _LINK_TARGETS},
                "target_slug": {"type": "string"},
            },
            "required": ["adapt_slug", "target_type", "target_slug"],
        },
    },
    {
        "name": "tausik_adapt_search",
        "description": "FTS5 search over ADAPT slug/title/tz_ref (JSON rows).",
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
