"""TAUSIK MCP tool definitions — RENAR ACTZ artifacts (Sec5A).

Kept in its own module (filesize hygiene). ``role``/``status``/``target_type``
are CLOSED lists, read from ``service_actz`` — the one place they live — never
retyped here (the mirror-drift lesson ``tools_adapt`` already documents).

FULL CLI PARITY, unlike ``tools_adapt`` (9 of 12 CLI subcommands have an MCP
tool; verify/unlink/delete do not) — a known, not-repeated gap.

``scripts`` goes on ``sys.path`` here for the same reason and with the same
arithmetic as in ``tools_adapt``.
"""

from __future__ import annotations

import os
import sys

_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from service_actz import (  # noqa: E402 — path must be set first
    ACTZ_STATUSES,
    LINK_TARGETS,
    SIGNATURE_ROLES,
)

_SIGNATURE_ROLES = list(SIGNATURE_ROLES)
_LINK_TARGETS = list(LINK_TARGETS)
_ACTZ_STATUSES = list(ACTZ_STATUSES)

TOOLS_ACTZ = [
    {
        "name": "tausik_actz_create",
        "description": "Create a RENAR ACTZ artifact header (Sec5A) — the contractual clarification protocol ('Протокол уточнения ТЗ N N'). tz_ref (source TZ) is required. Starts in 'draft'.",
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
        "name": "tausik_actz_point",
        "description": "Add a numbered point to a draft ACTZ. Points may only be added while status='draft' (frozen once any signature is recorded). tz_ref names which clause of the original ТЗ (or a prior ACTZ point) this point clarifies — final_tz drives off it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "actz_slug": {"type": "string"},
                "point_no": {"type": "integer"},
                "tz_ref": {"type": "string", "description": "Which ТЗ clause this clarifies"},
                "text": {"type": "string"},
            },
            "required": ["actz_slug", "point_no", "tz_ref", "text"],
        },
    },
    {
        "name": "tausik_actz_sign",
        "description": "Record a signature (Sec5.5.3). role=architect signs the canonical body with the project ed25519 key. role=client records signed_by+signed_at only (no cryptographic signature — this project has one key, not one per party). First signature ⇒ status='sent'; both roles ⇒ status='signed'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "actz_slug": {"type": "string"},
                "role": {"type": "string", "enum": _SIGNATURE_ROLES},
                "signed_by": {"type": "string", "description": "Signer identity"},
            },
            "required": ["actz_slug", "role", "signed_by"],
        },
    },
    {
        "name": "tausik_actz_verify",
        "description": "Verify the architect ed25519 signature against the current body. The client role has no cryptographic signature to verify.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_actz_show",
        "description": "Show an ACTZ with its points, signatures and links (JSON).",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_actz_list",
        "description": "List ACTZ headers, optionally filtered by status (draft/sent/signed/superseded). Returns JSON rows.",
        "inputSchema": {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": _ACTZ_STATUSES}},
        },
    },
    {
        "name": "tausik_actz_delta",
        "description": "Create a delta-ACTZ superseding a parent. The parent becomes 'superseded'; a later link to it is refused.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "parent_slug": {"type": "string"},
                "new_slug": {"type": "string"},
                "title": {"type": "string"},
                "tz_ref": {"type": "string", "description": "delta-TZ id"},
                "supersession_rationale": {
                    "type": "string",
                    "description": "Why the parent is superseded. MANDATORY.",
                },
            },
            "required": ["parent_slug", "new_slug", "title", "tz_ref", "supersession_rationale"],
        },
    },
    {
        "name": "tausik_actz_link",
        "description": "Link an ACTZ to a task or spec. Target must exist; linking to a SUPERSEDED ACTZ is refused.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "actz_slug": {"type": "string"},
                "target_type": {"type": "string", "enum": _LINK_TARGETS},
                "target_slug": {"type": "string"},
            },
            "required": ["actz_slug", "target_type", "target_slug"],
        },
    },
    {
        "name": "tausik_actz_unlink",
        "description": "Remove an ACTZ<->task/spec link.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "actz_slug": {"type": "string"},
                "target_type": {"type": "string", "enum": _LINK_TARGETS},
                "target_slug": {"type": "string"},
            },
            "required": ["actz_slug", "target_type", "target_slug"],
        },
    },
    {
        "name": "tausik_actz_delete",
        "description": "Delete an ACTZ (cascades points/signatures/links/decided-in edges).",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_actz_search",
        "description": "FTS5 search over ACTZ slug/title/tz_ref (JSON rows).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "description": "Default 20"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "tausik_actz_decided_in",
        "description": "Record that an ADAPT backward finding was decided-in a point of a SIGNED ACTZ, with provenance (linked_by). Refuses an unsigned target point.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "adapt_slug": {"type": "string"},
                "finding_id": {"type": "integer"},
                "actz_slug": {"type": "string"},
                "actz_point_no": {"type": "integer"},
                "linked_by": {"type": "string", "description": "Who recorded this edge"},
            },
            "required": ["adapt_slug", "finding_id", "actz_slug", "actz_point_no", "linked_by"],
        },
    },
    {
        "name": "tausik_actz_decided_in_remove",
        "description": "Remove a decided-in edge.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "adapt_slug": {"type": "string"},
                "finding_id": {"type": "integer"},
                "actz_slug": {"type": "string"},
                "actz_point_no": {"type": "integer"},
            },
            "required": ["adapt_slug", "finding_id", "actz_slug", "actz_point_no"],
        },
    },
    {
        "name": "tausik_actz_final_tz",
        "description": "The derived acceptance reference (Sec5A.4): per ТЗ clause, the latest both-role-signed ACTZ point, naming what it overrode. Read-only projection — nothing new is stored, ADAPT never enters it. as_of (ISO-8601) shows it at a past moment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "as_of": {"type": "string", "description": "ISO-8601 timestamp; omit for now"},
            },
        },
    },
    {
        "name": "tausik_actz_orphans",
        "description": "Signed ACTZ points no ADAPT reflects — an obligation outside requirements (Sec5A.4, fatal), found by query rather than by eye.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]
