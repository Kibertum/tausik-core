"""TAUSIK MCP tool definitions — RENAR ADAPT artifacts (v16r-adapt).

Kept in its own module (filesize hygiene). ``category`` (findings), ``role``
(signatures) and ``status`` are CLOSED lists, and this module no longer keeps
its own copies of them: the enums are READ from ``service_adapts``, the one
place those lists live.

THE OLD SENTENCE HERE SAID "No mirror to keep in sync". It was true about the
TREE — harness/claude/mcp is canonical and copied to every IDE unchanged — and
false about the CONSTANTS, which sat right below it as literals. A mirror
pinned by a test is still a second literal that has to be edited in lockstep,
and the standard has already moved under one (ADR-013 took SPEC types from
nine to eleven; ``tools_spec`` was converted then, this module was not).

``scripts`` goes on ``sys.path`` here for the same reason and with the same
arithmetic as in ``tools_spec``: ``tools.py`` imports this module at import
time, while ``server.py`` only extends the path inside ``_get_service``. The
two levels are the DEPLOYED layout's — see that module's comment, and
``tests/test_mcp_deployed_layout_resolves.py``, which asserts every profile
resolves it to its own ``scripts``.
"""

from __future__ import annotations

import os
import sys

_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from service_adapts import (  # noqa: E402 — path must be set first
    ADAPT_STATUSES,
    FINDING_CATEGORIES,
    LINK_TARGETS,
    SIGNATURE_ROLES,
)

_FINDING_CATEGORIES = list(FINDING_CATEGORIES)
_SIGNATURE_ROLES = list(SIGNATURE_ROLES)
_LINK_TARGETS = list(LINK_TARGETS)
_ADAPT_STATUSES = list(ADAPT_STATUSES)

TOOLS_ADAPT = [
    {
        "name": "tausik_adapt_create",
        "description": "Create a RENAR ADAPT artifact header (§7). tz_ref (source TZ) is required. Starts in 'draft' for body parts + the architect's signature (§7.5).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "title": {"type": "string"},
                "tz_ref": {"type": "string", "description": "Source TZ id, e.g. TZ-2026-001"},
                "trigger_stage": {
                    "type": "string",
                    "description": "Stage that triggered this ADAPT (ADR-007) — how several ADAPTs of one ТЗ are told apart. Optional.",
                },
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
        "description": (
            "Add a backward finding to an ADAPT. category is a CLOSED list of "
            f"{len(_FINDING_CATEGORIES)} "
            f"({'/'.join(_FINDING_CATEGORIES)}) — a new category requires a "
            "standard amendment."
        ),
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
        "description": "Record the architect's signature (§7.5): role=architect signs the canonical ADAPT body with the project ed25519 key ⇒ status 'approved' (§13.3.3 p.77 — the status and the signature are separate facts). role=client is REFUSED: ADR-011 withdrew the client signature under ADAPT, and what the client approves belongs in an ACTZ.",
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
        "description": "List ADAPTs, optionally filtered by status (the §7.8.1 closed list: draft/review/asked/answered/approved/frozen/superseded). Returns JSON rows.",
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
                "supersession_rationale": {
                    "type": "string",
                    "description": "Why the parent is superseded (ADR-007 p.108). MANDATORY: a supersession that cannot cite the contradicting requirement is an empty record.",
                },
            },
            "required": ["parent_slug", "new_slug", "title", "tz_ref", "supersession_rationale"],
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
