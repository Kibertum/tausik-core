"""TAUSIK shared utilities -- slug validation, timestamps, errors."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any


def tausik_config_path(project_dir: str) -> str:
    """Return the canonical path to the project's `.tausik/config.json`.

    Single source of truth used by bootstrap, MCP skill handlers, the CLI
    extras subparser, and the session-cleanup hook. Pure stdlib — safe to
    call before venv activation.
    """
    return os.path.join(project_dir, ".tausik", "config.json")


def fix_stdio_encoding() -> None:
    """Ensure stdout/stderr use UTF-8 on Windows (cp1251/cp1252 can't encode Unicode symbols).

    Call this at the top of every entry point (CLI, bootstrap, MCP server).
    On Linux/macOS this is a no-op since UTF-8 is the default.
    """
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]


_LOG_INSTALLED = False


def install_file_logging(project_dir: str | None = None) -> None:
    """Install rotating file handler at .tausik/tausik.log (5MB × 3)."""
    global _LOG_INSTALLED
    if _LOG_INSTALLED:
        return
    import logging
    import os
    from logging.handlers import RotatingFileHandler

    base = project_dir or os.getcwd()
    log_dir = os.path.join(base, ".tausik")
    if not os.path.isdir(log_dir):
        return
    try:
        handler = RotatingFileHandler(
            os.path.join(log_dir, "tausik.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setLevel(logging.WARNING)
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
        logging.getLogger("tausik").addHandler(handler)
        _LOG_INSTALLED = True
    except OSError:
        pass


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MAX_SLUG = 64


def safe_single_line(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("\n", " ").replace("\r", " ").strip()


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
        hint = f" Did you mean '{suggestion}'?" if suggestion and suggestion != slug else ""
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


def format_status_compact_json(data: dict[str, Any], duration_warning: str | None) -> str:
    """Dense JSON line for MCP/CLI ``--compact`` — default human status unchanged.

    v14b-session-active-time: also embeds session active/wall minutes and the
    configured limit so agents can read SENAR Rule 9.2 progress directly off
    the compact response without a follow-up tausik_status call.
    """

    counts = data["task_counts"]
    total = sum(counts.values())
    done = counts.get("done", 0)
    sess = data.get("session")
    payload: dict[str, Any] = {
        "tasks_done": done,
        "tasks_total": total,
        "tasks_planning": counts.get("planning", 0),
        "tasks_active": counts.get("active", 0),
        "tasks_blocked": counts.get("blocked", 0),
        "tasks_review": counts.get("review", 0),
        "session_id": int(sess["id"]) if sess else None,
        "epics": len(data.get("epics") or []),
    }
    if sess and "active_minutes" in data:
        payload["session_active_minutes"] = int(data["active_minutes"])
    if sess and "active_seconds" in data:
        payload["session_active_seconds"] = int(data["active_seconds"])
    if sess and "wall_minutes" in data:
        payload["session_wall_minutes"] = int(data["wall_minutes"])
    if "session_max_minutes" in data:
        payload["session_max_minutes"] = int(data["session_max_minutes"])
    if duration_warning:
        payload["session_warning"] = duration_warning
    exp = data.get("exploration")
    if exp:
        payload["exploration_open"] = True
        try:
            payload["exploration_id"] = int(exp["id"])
        except (KeyError, TypeError, ValueError):
            pass
        if exp.get("over_limit"):
            payload["exploration_over_limit"] = True
    overdue = data.get("audit_overdue_sessions")
    if overdue:
        payload["audit_overdue_sessions"] = int(overdue)
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
