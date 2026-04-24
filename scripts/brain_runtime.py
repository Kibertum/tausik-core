"""Shared runtime helpers for brain read/write callers.

Callers today:
- service_knowledge.decide() (auto-routing CLI path)
- scripts/hooks/brain_post_webfetch.py (auto-cache WebFetch results)
- agents/<ide>/mcp/brain/handlers.py (MCP read+write dispatch)

`open_brain_deps()` is the shared setup primitive — returns
(conn, client, cfg) with None-semantics for "brain disabled" and
"token missing". Fold-in point promised in the old brain_runtime
docstring: it's now live and both handlers files use it.

Zero external deps. Never raises: wrap failures as (False, reason) tuples
in the try_brain_write_* wrappers. open_brain_deps propagates sqlite
errors from open_brain_db — callers decide how to surface them.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any

_FAST_FALLBACK_TIMEOUT = 5.0


def _format_scrub_detectors(result: dict) -> str:
    """Surface detector names only — never raw `match` (may contain PII / ANSI)."""
    issues = result.get("issues") or []
    detectors = sorted({i.get("detector", "?") for i in issues if isinstance(i, dict)})
    return ", ".join(detectors) if detectors else "matched patterns"


def _build_notion_client(cfg: dict) -> Any | None:
    """Return a NotionClient if the config's token env var is set, else None.

    Connected with a short timeout + single retry so MCP calls fail fast
    when Notion is unreachable; the brain's local mirror still serves reads.
    """
    import brain_notion_client

    token_env = cfg.get("notion_integration_token_env") or ""
    token = os.environ.get(token_env, "") if token_env else ""
    if not token:
        return None
    return brain_notion_client.NotionClient(
        token,
        timeout=_FAST_FALLBACK_TIMEOUT,
        max_retries=1,
    )


def open_brain_deps() -> tuple[sqlite3.Connection | None, Any | None, dict]:
    """Open the brain mirror + (optional) Notion client based on config.

    Returns:
      (None, None, cfg)          if brain is disabled
      (conn, None, cfg)          if brain is enabled but token env unset
      (conn, client, cfg)        happy path — mirror open, client ready

    The caller owns `conn` and is responsible for closing it. This matches
    the pre-existing contract in the MCP handlers which never closed the
    connection inside the request lifecycle (short-lived subprocess).
    """
    import brain_config
    import brain_sync

    cfg = brain_config.load_brain()
    if not cfg.get("enabled"):
        return None, None, cfg
    path = brain_config.get_brain_mirror_path()
    conn = brain_sync.open_brain_db(path)
    client = _build_notion_client(cfg)
    return conn, client, cfg


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
            return False, f"scrub_blocked: {_format_scrub_detectors(result)}"
        return False, f"{status}: {result.get('error', 'unknown')}"
    except Exception as e:  # noqa: BLE001
        return False, f"exception: {e}"


def try_brain_write_web_cache(
    url: str,
    content: str,
    cfg: dict,
    *,
    query: str = "",
    title: str | None = None,
) -> tuple[bool, str]:
    """Attempt a brain write for a web_cache entry.

    Same contract as try_brain_write_decision — returns
    (True, notion_page_id) on ok/ok_not_mirrored, (False, reason) otherwise.
    The PostToolUse caller uses the reason only for stderr logging; it
    never surfaces to the user.

    Scrubbing, mirror upsert, and content_hash are all handled inside
    brain_mcp_write.store_record. This wrapper just owns token lookup,
    db open, and the (bool, str) contract.
    """
    try:
        import brain_mcp_write
        import brain_notion_client
        import brain_sync
        from brain_config import get_brain_mirror_path

        if not url or not content:
            return False, "url and content are required"

        token_env = cfg.get("notion_integration_token_env") or ""
        token = os.environ.get(token_env, "") if token_env else ""
        if not token:
            return False, "token env var not set"

        client = brain_notion_client.NotionClient(token, timeout=5.0, max_retries=1)
        conn = brain_sync.open_brain_db(get_brain_mirror_path(cfg))
        # Notion's Name title is bounded at 60 chars; url is a safe fallback
        # (always non-empty by the guard above) when the tool returned no title.
        name_src = title.strip() if isinstance(title, str) and title.strip() else url
        fields: dict[str, Any] = {
            "name": name_src[:60],
            "url": url,
            "content": content,
        }
        if query:
            fields["query"] = query
        ttl = cfg.get("ttl_web_cache_days")
        if isinstance(ttl, int) and ttl > 0:
            fields["ttl_days"] = ttl
        result = brain_mcp_write.store_record(client, conn, "web_cache", fields, cfg)
        status = result.get("status", "")
        if status in ("ok", "ok_not_mirrored"):
            return True, result.get("notion_page_id", "")
        if status == "scrub_blocked":
            return False, f"scrub_blocked: {_format_scrub_detectors(result)}"
        return False, f"{status}: {result.get('error', 'unknown')}"
    except Exception as e:  # noqa: BLE001
        return False, f"exception: {e}"
