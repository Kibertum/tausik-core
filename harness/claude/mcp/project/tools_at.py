"""TAUSIK MCP tool definitions — RENAR AT (Acceptance Test) artifacts (Sec8A).

Kept in its own module (filesize hygiene). Full CLI parity, same as tools_actz.
These tools RECORD the result of the isolated-generation procedure
(docs/en/at-generation-procedure.md) — none of them generate anything.
"""

from __future__ import annotations

TOOLS_AT = [
    {
        "name": "tausik_at_create",
        "description": "Record a RENAR AT (Acceptance Test, Sec8A) — the RESULT of the isolated-generation procedure (docs/en/at-generation-procedure.md), not a generator. tz_text (verbatim contract quote) and generated_by (who recorded this) are mandatory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "tz_ref": {"type": "string"},
                "tz_text": {
                    "type": "string",
                    "description": "Verbatim quote of the contract clause",
                },
                "scenario": {"type": "string", "description": "The acceptance check itself"},
                "source_as_of": {
                    "type": "string",
                    "description": "Which final-TZ moment (completed_at) this AT was derived from",
                },
                "generated_by": {
                    "type": "string",
                    "description": "Who recorded this (orchestrator identity)",
                },
            },
            "required": ["slug", "tz_ref", "tz_text", "scenario", "source_as_of", "generated_by"],
        },
    },
    {
        "name": "tausik_at_show",
        "description": "Show an AT record (JSON).",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_at_list",
        "description": "List AT records, optionally filtered by tz_ref (JSON rows).",
        "inputSchema": {
            "type": "object",
            "properties": {"tz_ref": {"type": "string"}},
        },
    },
    {
        "name": "tausik_at_delete",
        "description": "Delete an AT record.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "tausik_at_search",
        "description": "FTS5 search over AT slug/tz_ref/tz_text/scenario (JSON rows).",
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
        "name": "tausik_at_check_freshness",
        "description": "Which AT records are STALE against the CURRENT final-TZ (Sec8A property 2: regenerate before every trial). Returns only the stale ones — empty means nothing needs regeneration. Omit slug to check all.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
        },
    },
    {
        "name": "tausik_at_record_result",
        "description": "Record one observed trial outcome for an AT (append-only history — a re-run is a new row, never an overwrite).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "outcome": {"type": "string", "enum": ["red", "green"]},
                "note": {"type": "string"},
            },
            "required": ["slug", "outcome"],
        },
    },
    {
        "name": "tausik_at_diagnose",
        "description": "Route an AT's LATEST recorded outcome against a caller-supplied tc_outcome (Sec8A.4/Sec10.4.3's four-cell matrix). TC has no first-class artifact in TAUSIK yet — this tool never reads pytest/verification_runs itself; tc_outcome must be supplied explicitly. Refuses an AT with no recorded trial.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "tc_outcome": {"type": "string", "enum": ["red", "green"]},
            },
            "required": ["slug", "tc_outcome"],
        },
    },
    {
        "name": "tausik_at_release_readiness",
        "description": "Sec8A.4's release gate: ready only when EVERY AT's latest outcome is green AND fresh against the current final-TZ. Reads no TC — distinct from QG-4 (optional, business outcome).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]
