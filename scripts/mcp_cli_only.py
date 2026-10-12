"""CLI commands that are deliberately NOT MCP tools — each with its reason.

The project rule is MCP-first. A command that exists only in the CLI is a gap in
that rule, and a gap nobody wrote down looks the same as one nobody noticed. So
the intentional ones are listed here with the reason and the decision behind
them; tests/test_mcp_cli_only.py refuses an entry without a reason and an entry
whose command has since appeared as an MCP tool (the registry would then lie).

The MCP surface is on a ratchet (tausik/gates.json `mcp_surface`): every tool is
sent to the model on each turn by hosts that do not defer schemas, so a tool
must pay for itself. That is why a rarely-run command stays in the terminal.
"""

from __future__ import annotations

CLI_ONLY: dict[str, dict[str, str]] = {
    "redact": {
        "reason": (
            "--apply rewrites the knowledge history irreversibly and belongs in a "
            "terminal after reading the dry run; the dry run and `redact list` are "
            "run rarely and do not pay for a tool on the ratcheted MCP surface"
        ),
        "decided_by": "decision #385",
        "mcp_tool": "tausik_redact",
    },
    "task obsolete": {
        "reason": (
            "closing a task as obsolete is a judgment about the backlog, taken rarely "
            "and usually on the owner's word; it skips QG-2 by design, so it stays a "
            "deliberate terminal act instead of one more tool on the ratcheted MCP surface"
        ),
        "decided_by": "decision #390",
        "mcp_tool": "tausik_task_obsolete",
    },
}
