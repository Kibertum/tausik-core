"""Logical artifact-card validation for Shared Brain writes (patterns/gotchas).

`scope` is a v1 logical field: validated here, stripped before Notion (no column in v1).
Optional `external_repo_url`: validated here (format + optional HTTP reachability),
stripped before Notion (no column in v1).

See harness/schemas/brain-artifact-card.schema.json and docs/en/brain-artifact-taxonomy.md.
"""

from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import urlparse

_SCOPE_STORE_CATEGORIES = frozenset({"patterns", "gotchas"})


def validate_artifact_card_for_store(
    category: str,
    fields: Mapping[str, Any],
    cfg: Mapping[str, Any],
) -> tuple[bool, str | None]:
    """Return (ok, error_message).

    Empty or whitespace-only `scope` always fails when the key is present.
    When `brain.require_artifact_scope` is true, `scope` must be present and non-empty.
    """
    if category not in _SCOPE_STORE_CATEGORIES:
        return True, None

    strict_scope = bool(cfg.get("require_artifact_scope"))

    if "scope" not in fields:
        if strict_scope:
            return False, "scope is required when brain.require_artifact_scope is true"
        return True, None

    scope = fields.get("scope")
    if scope is None:
        return False, "scope cannot be null"
    if not isinstance(scope, str):
        return False, "scope must be a string"
    if not scope.strip():
        return False, "scope must be a non-empty string"

    return True, None


def check_external_repo_url_reachable(url: str, timeout: float = 12.0) -> tuple[bool, str | None]:
    """HTTP(S) GET with a short read — rejects connect/DNS/TLS failures and bad HTTP codes."""
    import ssl
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    ctx = ssl.create_default_context()
    req = Request(
        url.strip(),
        headers={
            "User-Agent": "TAUSIK-brain/1.4 (+https://github.com/Kibertum/SENAR)",
            "Accept": "*/*",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            code = resp.getcode()
            resp.read(512)
    except HTTPError as e:
        code = e.code
        if code in (404, 410):
            return False, f"external_repo_url not found (HTTP {code})"
        if code >= 400 and code not in (401, 403):
            return False, f"external_repo_url returned HTTP {code}"
        return True, None
    except URLError as e:
        reason = getattr(e, "reason", e)
        return False, f"external_repo_url not reachable: {reason!r}"
    except OSError as e:
        return False, f"external_repo_url not reachable: {e}"

    if code in (404, 410):
        return False, f"external_repo_url not found (HTTP {code})"
    if code >= 400 and code not in (401, 403):
        return False, f"external_repo_url returned HTTP {code}"
    return True, None


def validate_external_repo_url_for_store(
    category: str,
    fields: Mapping[str, Any],
    cfg: Mapping[str, Any],
) -> tuple[bool, str | None]:
    """Validate optional logical field ``external_repo_url`` (patterns/gotchas only)."""
    if category not in _SCOPE_STORE_CATEGORIES:
        return True, None
    if "external_repo_url" not in fields:
        return True, None

    raw = fields.get("external_repo_url")
    if raw is None:
        return False, "external_repo_url cannot be null"
    if not isinstance(raw, str):
        return False, "external_repo_url must be a string"
    u = raw.strip()
    if not u:
        return False, "external_repo_url cannot be empty or whitespace-only"

    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https"):
        return False, "external_repo_url must use http:// or https://"
    if not parsed.netloc:
        return False, "external_repo_url must include a host"

    if bool(cfg.get("skip_external_repo_url_reachability_check")):
        return True, None

    return check_external_repo_url_reachable(u)
