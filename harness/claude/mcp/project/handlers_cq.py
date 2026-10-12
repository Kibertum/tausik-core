"""MCP handlers for the cq domain — cross-project knowledge over an external service.

Split out of handlers.py by mcp-handlers-god-module-split. Follows the
convention already set by handlers_spec.py / handlers_adapt.py: the module owns
its handlers AND the slice of the dispatch table that names them, and
handlers.py merges it with `_DISPATCH.update(...)`.

Separate from handlers_knowledge.py on purpose: that module is the project's own
store and always available, while everything here talks to a remote endpoint
that is optional, may be unconfigured, and may be down. Both handlers below have
to answer usefully when it is — which is a different contract, not a different
flavour of the same one.
"""

from __future__ import annotations

import json
import os
from typing import Any


def _get_cq_client() -> Any:
    """Get cq client from project config. Returns None if not configured."""
    try:
        from tausik_utils import tausik_config_path

        config_path = tausik_config_path(os.getcwd())
        if not os.path.exists(config_path):
            return None
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        from cq_client import get_cq_client

        return get_cq_client(config)
    except Exception:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return None


def _handle_cq_query(args: dict) -> str:
    """Query cq for cross-project knowledge."""
    client = _get_cq_client()
    if not client:
        return (
            "cq not configured. Add 'cq' section to .tausik/config.json with endpoint and api_key."
        )
    units = client.query(
        domains=args["domains"],
        language=args.get("language", ""),
        framework=args.get("framework", ""),
        limit=args.get("limit", 5),
    )
    if not units:
        return (
            "No cq knowledge found for these domains. cq may be unavailable or no matching entries."
        )
    lines = []
    for u in units:
        insight = u.get("insight", {})
        conf = u.get("evidence", {}).get("confidence", 0)
        lines.append(f"[{conf:.0%}] {insight.get('summary', '?')}")
        if insight.get("action"):
            lines.append(f"  Action: {insight['action']}")
    return "\n".join(lines)


def _handle_cq_publish(args: dict) -> str:
    """Publish knowledge to cq."""
    client = _get_cq_client()
    if not client:
        return "cq not configured. Add 'cq' section to .tausik/config.json."
    result = client.propose(
        domains=args["domains"],
        summary=args["summary"],
        detail=args.get("detail", ""),
        action=args.get("action", ""),
        languages=args.get("languages"),
    )
    if result and result.get("id"):
        return f"Published to cq: {result['id']}"
    return "Failed to publish to cq. Server may be unavailable."


CQ_HANDLERS = {
    "tausik_cq_query": lambda svc, args: _handle_cq_query(args),
    "tausik_cq_publish": lambda svc, args: _handle_cq_publish(args),
}
