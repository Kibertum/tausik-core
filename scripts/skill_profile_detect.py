"""Detect IDE + model from environment for TAUSIK skill profile resolution.

Two independent axes (B8-pre axis decision):
- IDE: claude-code / cursor / qwen-code / codex (host harness)
- Model: opus / sonnet / haiku / gpt-4 / gpt-5 / gpt-5-5 / qwen (LLM)

Both detections are best-effort and pure — return None on uncertainty,
never raise, no side-effects. The model dimension is often unknown
because Cursor/Qwen don't expose the active model via env by default;
in that case skills load with IDE overlay only.

Public API:
    detect_ide() -> str | None
    detect_model() -> str | None
    normalize_model_profile_slug(raw: str) -> str
"""

from __future__ import annotations

import os
import re
from typing import Final

VALID_IDES: Final[frozenset[str]] = frozenset({"claude", "cursor", "qwen", "codex"})

VALID_MODELS: Final[frozenset[str]] = frozenset(
    {"opus", "sonnet", "haiku", "gpt-4", "gpt-5", "gpt-5-5", "qwen"}
)

_IDE_ENV_MARKERS: Final[tuple[tuple[str, str], ...]] = (
    ("claude", "CLAUDE_CODE_SSE_PORT"),
    ("claude", "CLAUDE_CODE_ENTRYPOINT"),
    ("claude", "CLAUDECODE"),
    ("cursor", "CURSOR_TRACE_ID"),
    ("cursor", "CURSOR_DIR"),
    ("qwen", "QWEN_CODE"),
    ("qwen", "QWEN_HOME"),
    ("codex", "CODEX_SANDBOX_DIR"),
    ("codex", "CODEX_HOME"),
)

_MODEL_ENV_VARS: Final[tuple[str, ...]] = (
    "TAUSIK_MODEL",
    "ANTHROPIC_MODEL",
    "CLAUDE_CODE_MODEL",
    "OPENAI_MODEL",
    "OPENAI_API_MODEL",
    "QWEN_MODEL",
)


def normalize_model_profile_slug(raw: str) -> str:
    """Lowercase + collapse non-alphanum to single hyphen + trim hyphens.

    Examples:
        "GPT-5" -> "gpt-5"
        "gpt-5.5" -> "gpt-5-5"
        "  Claude Sonnet 4.6  " -> "claude-sonnet-4-6"
        "" -> ""
        non-string -> ""
    """
    if not isinstance(raw, str):
        return ""
    s = raw.strip().lower()
    if not s:
        return ""
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _model_from_raw(raw: str) -> str | None:
    """Map a raw model string from env into a known short slug, or None."""
    slug = normalize_model_profile_slug(raw)
    if not slug:
        return None
    # Direct hits first
    if slug in VALID_MODELS:
        return slug
    # Fuzzy: substring-based mapping for common naming conventions
    if "opus" in slug:
        return "opus"
    if "sonnet" in slug:
        return "sonnet"
    if "haiku" in slug:
        return "haiku"
    if "gpt-5-5" in slug or slug.startswith("gpt-5-5"):
        return "gpt-5-5"
    if "gpt-5" in slug or slug.startswith("gpt-5"):
        return "gpt-5"
    if "gpt-4" in slug or slug.startswith("gpt-4"):
        return "gpt-4"
    if "qwen" in slug:
        return "qwen"
    return None


def detect_ide() -> str | None:
    """Return canonical IDE slug from env vars, or None if uncertain.

    Probes a small set of well-known env markers per IDE. First match wins;
    multiple IDE markers in a single shell are not expected in practice.
    """
    for ide_slug, env_name in _IDE_ENV_MARKERS:
        if os.environ.get(env_name):
            return ide_slug
    return None


def detect_model() -> str | None:
    """Return canonical model slug from env vars, or None if uncertain.

    Walks _MODEL_ENV_VARS in priority order, returning the first parseable
    hit. None is the honest answer for hosts that don't expose the model
    (Cursor/Qwen UI selection); callers fall back to IDE-only overlay.
    """
    for env_name in _MODEL_ENV_VARS:
        raw = os.environ.get(env_name)
        if not raw:
            continue
        mapped = _model_from_raw(raw)
        if mapped:
            return mapped
    return None
