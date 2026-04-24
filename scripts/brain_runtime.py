"""Shared runtime helpers for brain read/write callers.

Callers today: service_knowledge.decide() (auto-routing CLI path). Likely
next callers: brain-skill-ui, brain-search-proactive, brain-webfetch-hook.

The MCP handlers in agents/<ide>/mcp/brain/handlers.py also duplicate a
similar `_open_deps` — when a third in-tree caller lands, fold them into
this module. Not doing it now to keep the brain-decide-auto-route diff
minimal.

Zero external deps. Never raises: wrap failures as (False, reason) tuples.
"""

from __future__ import annotations

import os
from typing import Any


def try_brain_write_decision(
    text: str, rationale: str | None, cfg: dict
) -> tuple[bool, str]:
    """Attempt a brain write for a decision.

    Returns (True, notion_page_id) on success, (False, error_reason) on any
    failure — token missing, Notion network error, scrubbing block, bad
    config. Never raises: caller falls back to local on False.
    """
    try:
        import brain_mcp_write
        import brain_notion_client
        import brain_sync
        from brain_config import get_brain_mirror_path

        token_env = cfg.get("notion_integration_token_env") or ""
        token = os.environ.get(token_env, "") if token_env else ""
        if not token:
            return False, "token env var not set"

        client = brain_notion_client.NotionClient(token, timeout=5.0, max_retries=1)
        conn = brain_sync.open_brain_db(get_brain_mirror_path(cfg))
        fields: dict[str, Any] = {"name": text[:60], "decision": text}
        if rationale:
            fields["rationale"] = rationale
        result = brain_mcp_write.store_record(client, conn, "decisions", fields, cfg)
        status = result.get("status", "")
        if status in ("ok", "ok_not_mirrored"):
            return True, result.get("notion_page_id", "")
        if status == "scrub_blocked":
            # brain_mcp_write.store_record returns issues as list[dict] with
            # keys {detector, severity, match, hint}. Surface only the detector
            # names (closed set) — never the raw `match` values, which can
            # contain user content / ANSI / prompt-injection payloads.
            issues = result.get("issues") or []
            detectors = sorted(
                {i.get("detector", "?") for i in issues if isinstance(i, dict)}
            )
            detail = ", ".join(detectors) if detectors else "matched patterns"
            return False, f"scrub_blocked: {detail}"
        return False, f"{status}: {result.get('error', 'unknown')}"
    except Exception as e:  # noqa: BLE001
        return False, f"exception: {e}"
