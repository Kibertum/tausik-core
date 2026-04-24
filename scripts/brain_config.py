"""Brain section of project config — shared cross-project knowledge.

Thin layer on top of project_config.load_config(): reads the `brain` key,
merges it with safe defaults, validates, and exposes a handful of pure
helpers used by the brain MCP tools and init wizard.

No Notion network I/O happens here — this module only parses and
validates local configuration.
"""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from typing import cast

from project_config import load_config

DEFAULT_BRAIN: dict = {
    "enabled": False,
    "local_mirror_path": "~/.tausik-brain/brain.db",
    "notion_integration_token_env": "NOTION_TAUSIK_TOKEN",
    "database_ids": {
        "decisions": "",
        "web_cache": "",
        "patterns": "",
        "gotchas": "",
    },
    "project_names": [],
    "ttl_web_cache_days": 30,
    "ttl_decisions_days": None,
    "private_url_patterns": [],
}

_BRAIN_CATEGORIES = ("decisions", "web_cache", "patterns", "gotchas")


def load_brain(cfg: dict | None = None) -> dict:
    """Return merged brain config (defaults overridden by user values)."""
    if cfg is None:
        cfg = load_config()
    user_brain = cfg.get("brain", {}) or {}
    merged = dict(DEFAULT_BRAIN)
    merged["database_ids"] = dict(DEFAULT_BRAIN["database_ids"])
    for key, value in user_brain.items():
        if key == "database_ids" and isinstance(value, dict):
            merged["database_ids"].update(value)
        else:
            merged[key] = value
    return merged


def is_brain_enabled(cfg: dict | None = None) -> bool:
    return bool(load_brain(cfg).get("enabled"))


def validate_brain(cfg: dict | None = None) -> list[str]:
    """Validate brain config. Returns list of error messages (empty if valid).

    Validation is strict only when brain.enabled is true — disabled brain
    passes even with empty fields so users can configure incrementally.
    """
    brain = load_brain(cfg)
    errors: list[str] = []

    for pat in brain.get("private_url_patterns") or []:
        if not isinstance(pat, str):
            errors.append(
                f"brain.private_url_patterns: expected string, got {type(pat).__name__}"
            )
            continue
        try:
            re.compile(pat)
        except re.error as e:
            errors.append(f"brain.private_url_patterns: invalid regex {pat!r}: {e}")

    if not brain.get("enabled"):
        return errors

    db_ids = brain.get("database_ids") or {}
    for category in _BRAIN_CATEGORIES:
        if not db_ids.get(category):
            errors.append(
                f"brain.database_ids.{category} is empty but brain is enabled"
            )

    token_env = brain.get("notion_integration_token_env") or ""
    if not token_env:
        errors.append(
            "brain.notion_integration_token_env is empty but brain is enabled"
        )
    elif not os.environ.get(token_env):
        errors.append(
            f"brain enabled but env var {token_env!r} is not set — integration token missing"
        )

    ttl_web = brain.get("ttl_web_cache_days")
    if ttl_web is not None and (not isinstance(ttl_web, int) or ttl_web <= 0):
        errors.append("brain.ttl_web_cache_days must be a positive integer or null")

    ttl_dec = brain.get("ttl_decisions_days")
    if ttl_dec is not None and (not isinstance(ttl_dec, int) or ttl_dec <= 0):
        errors.append("brain.ttl_decisions_days must be a positive integer or null")

    return errors


def get_brain_mirror_path(cfg: dict | None = None) -> str:
    """Absolute filesystem path to the local brain SQLite mirror.

    Expands ~ and $ENV_VAR / ${ENV_VAR} references.
    """
    raw = cast(
        str,
        load_brain(cfg).get("local_mirror_path") or DEFAULT_BRAIN["local_mirror_path"],
    )
    return os.path.abspath(os.path.expandvars(os.path.expanduser(raw)))


def compute_project_hash(project_name: str) -> str:
    """SHA256(canonical_name)[:16] — 16 hex chars = 64-bit privacy-preserving id.

    Canonicalization: NFC-normalize, strip(), lower(), collapse internal
    whitespace to '-'. NFC is required because the same logical name
    encoded differently (e.g. precomposed 'é' U+00E9 vs decomposed 'e'+U+0301)
    would otherwise hash to different ids and register as two different
    projects sharing the same brain workspace.

    See references/brain-db-schema.md §2 for the privacy rationale.
    """
    if not isinstance(project_name, str) or not project_name.strip():
        raise ValueError("project_name must be a non-empty string")
    normalized = unicodedata.normalize("NFC", project_name)
    canonical = re.sub(r"\s+", "-", normalized.strip().lower())
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
