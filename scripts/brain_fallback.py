"""Classify Notion errors into user-facing categories + render friendly messages.

Used by brain MCP handlers to produce graceful, actionable error text when
the brain is disabled, misconfigured, auth-failing, rate-limited, or offline.

Policy (single-source-of-truth for fallback UX):
  - brain disabled          → "run tausik brain init"
  - token env unset         → "export the token and retry"
  - auth (401/403)          → "token invalid/revoked; re-run tausik brain init"
  - not_found (404)         → "database/page missing; re-run setup"
  - rate_limit (429)        → "retry in <Retry-After> seconds (default 60)"
  - network (URLError/DNS)  → "offline; (search) local mirror only / (write)
                               not persisted — retry later"
  - server (5xx)            → "Notion server error; retry shortly"
  - unknown                 → show raw message
"""

from __future__ import annotations

from typing import Literal

from brain_notion_client import (
    NotionAuthError,
    NotionError,
    NotionNetworkError,
    NotionNotFoundError,
    NotionRateLimitError,
    NotionServerError,
)

Op = Literal["search", "get", "store"]

_DEFAULT_RATE_LIMIT_SECONDS = 60


def classify_error(exc: BaseException) -> str:
    """Return a category tag for the given exception.

    Category is determined by exception type — robust against message churn.
    Order matters: more specific subclasses must be matched before the base.
    """
    if isinstance(exc, NotionAuthError):
        return "auth"
    if isinstance(exc, NotionNotFoundError):
        return "not_found"
    if isinstance(exc, NotionRateLimitError):
        return "rate_limit"
    if isinstance(exc, NotionServerError):
        return "server"
    if isinstance(exc, NotionNetworkError):
        return "network"
    if isinstance(exc, NotionError):
        return "unknown"
    return "unknown"


def user_message(
    category: str,
    *,
    op: Op,
    detail: str = "",
    retry_after: int | None = None,
) -> str:
    """Render a friendly markdown message for an error category.

    `op` is either 'search' / 'get' / 'store' — only affects the network
    case where the implication for the caller differs (local-only vs. lost
    write). `retry_after` is the Retry-After value (seconds) parsed from the
    429 response, when available; defaults to 60 seconds for rate_limit.
    """
    if op not in ("search", "get", "store"):
        raise ValueError(f"op must be 'search'|'get'|'store', got {op!r}")
    if category == "auth":
        return (
            "_Notion auth failed — integration token is invalid or revoked._\n\n"
            "Re-run `.tausik/tausik brain init` or rotate the integration token."
        )
    if category == "not_found":
        return (
            "_Notion database or page not found._\n\n"
            "The brain config may reference a stale database_id. "
            "Re-run `.tausik/tausik brain init --force` to recreate."
        )
    if category == "rate_limit":
        secs = (
            retry_after
            if retry_after and retry_after > 0
            else _DEFAULT_RATE_LIMIT_SECONDS
        )
        return (
            f"_Rate-limited by Notion. Retry in {secs} seconds._\n\n"
            "If this persists, slow down or batch writes."
        )
    if category == "server":
        return (
            "_Notion server error — retries exhausted._\n\n"
            "This is a Notion-side outage. Local mirror is unaffected; "
            "retry in a few minutes."
        )
    if category == "network":
        if op == "store":
            return (
                "_Network unavailable — write was not persisted to Notion._\n\n"
                "The record is lost for this call; retry when your connection "
                "returns."
            )
        return (
            "_Offline — showing local mirror results only._\n\n"
            "Reconnect to reach the shared brain; local data is up to the "
            "last successful sync."
        )
    return f"_Notion error: {detail or 'unknown failure'}._"


def retry_after_from(exc: BaseException) -> int | None:
    """Extract Retry-After seconds from a NotionRateLimitError, if attached."""
    return getattr(exc, "retry_after", None)
