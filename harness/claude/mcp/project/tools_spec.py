"""TAUSIK MCP tool definitions — RENAR SPEC artifacts (v16r-spec-types).

Kept in its own module (filesize hygiene). ``type`` is a CLOSED list, and this
module no longer keeps its own copy of it: the enum is READ from
``service_specs``, the one place the list lives. A mirror pinned by a test is
still a second literal that has to be edited in lockstep, and the standard just
moved under it (nine types where §8.3 closes at eleven).

``scripts`` goes on ``sys.path`` here rather than being assumed: ``tools.py``
imports this module at import time, while ``server.py`` only extends the path
inside ``_get_service``, so an assumed path would break the server on startup.
"""

from __future__ import annotations

import os
import sys

# Ensure scripts dir is in path (once, at import time) — see module docstring.
#
# TWO levels, and the count belongs to the DEPLOYED layout: bootstrap copies
# this tree to `<profile>/mcp/project/`, so `../../scripts` is the profile's own
# `<profile>/scripts/`. It is NOT the count for this source tree, where the
# repository keeps `scripts/` at its root, three levels up — so here the insert
# silently adds a directory that does not exist. That is deliberate and
# harmless: nothing runs this copy as a server, and the only importers are
# tests, where pytest supplies the path — `pyproject.toml` sets
# `pythonpath = ["scripts"]` for every run. (Four conftest helpers insert it
# again locally; that is belt and braces, not the mechanism — naming those
# instead was this comment's first draft, and the review caught it.) Raising
# when the directory is missing would break the source tree and fix nothing in
# a profile.
#
# Written down because the arithmetic has been miscounted twice (sessions #209
# and #210), which is what a silent no-op buys you. `tests/
# test_mcp_deployed_layout_resolves.py` now asserts that every deployed profile
# resolves this to ITS OWN scripts — resolvability alone is not enough, since
# three levels up also finds a `service_specs.py`, the repository's.
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from service_specs import (  # noqa: E402 — path must be set first
    SPEC_RELATIONS,
    SPEC_STATUSES,
    SPEC_TYPES,
)

_SPEC_TYPES = list(SPEC_TYPES)
_SPEC_RELATIONS = list(SPEC_RELATIONS)
_SPEC_STATUSES = list(SPEC_STATUSES)

TOOLS_SPEC = [
    {
        "name": "tausik_spec_add",
        "description": (
            f"Create a RENAR SPEC artifact. type is a CLOSED list of {len(_SPEC_TYPES)} "
            f"({'/'.join(_SPEC_TYPES)}) — a new type requires a standard amendment, "
            "not a free-text value. version is required."
        ),
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
