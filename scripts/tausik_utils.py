"""TAUSIK shared utilities -- slug validation, timestamps, errors."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone


def fix_stdio_encoding() -> None:
    """Ensure stdout/stderr use UTF-8 on Windows (cp1251/cp1252 can't encode Unicode symbols).

    Call this at the top of every entry point (CLI, bootstrap, MCP server).
    On Linux/macOS this is a no-op since UTF-8 is the default.
    """
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MAX_SLUG = 64


class ServiceError(Exception):
    """Business logic error -- shown to user."""


MAX_TITLE = 512
MAX_CONTENT = 100_000


def utcnow_iso() -> str:
    """Return current UTC time as ISO-8601 string (Z suffix for consistency with SQLite triggers)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitize_slug(slug: str) -> str:
    """Make a best-effort valid slug from arbitrary input.

    Lowercase, replace runs of non-slug chars with a hyphen, strip leading/trailing
    hyphens, trim to MAX_SLUG, ensure first char is alphanumeric.
    Used only to SUGGEST a fix in error messages — never auto-applied.
    """
    import re as _re

    cleaned = _re.sub(r"[^a-z0-9]+", "-", (slug or "").lower()).strip("-")
    if not cleaned:
        return ""
    if not cleaned[0].isalnum():
        cleaned = cleaned.lstrip("-")
    return cleaned[:MAX_SLUG]


def validate_slug(slug: str) -> None:
    """Raise ValueError if slug is invalid. Error message suggests a sanitized alternative."""
    if not slug or not SLUG_RE.match(slug):
        suggestion = sanitize_slug(slug)
        hint = (
            f" Did you mean '{suggestion}'?"
            if suggestion and suggestion != slug
            else ""
        )
        raise ValueError(f"Invalid slug '{slug}': must match [a-z0-9][a-z0-9-]*.{hint}")
    if len(slug) > MAX_SLUG:
        raise ValueError(f"Slug '{slug[:20]}...' is {len(slug)} chars, max {MAX_SLUG}")


def validate_length(field: str, value: str, limit: int = MAX_TITLE) -> None:
    """Raise ValueError if value exceeds limit."""
    if len(value) > limit:
        raise ValueError(f"Field '{field}' is {len(value)} chars, max {limit}")


def validate_content(field: str, value: str | None) -> None:
    """Raise ValueError if content exceeds MAX_CONTENT."""
    if value and len(value) > MAX_CONTENT:
        raise ValueError(f"Field '{field}' is {len(value)} chars, max {MAX_CONTENT}")


def slugify(title: str, max_len: int = 50) -> str:
    """Generate a slug from title: lowercase, alphanumeric + hyphens."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:max_len] if slug else "task"
