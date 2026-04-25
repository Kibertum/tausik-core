"""TAUSIK types -- constants and validation sets."""

from __future__ import annotations

# --- Constants ---

VALID_TASK_STATUSES = frozenset({"planning", "active", "blocked", "review", "done"})
VALID_STORY_STATUSES = frozenset({"open", "active", "done"})
VALID_EPIC_STATUSES = frozenset({"active", "done", "archived"})

# Built-in stacks. Single source of truth lives in `stacks/<name>/stack.json`
# and is loaded by `stack_registry.default_registry()`. The hardcoded fallback
# below is used ONLY when the registry can't load (missing dir, IO error,
# import-time crash) — it keeps `from project_types import DEFAULT_STACKS`
# safe so the rest of the framework boots.
#
# Users extend this set via .tausik/config.json under the top-level
# "custom_stacks" array — see get_valid_stacks() below.
_FALLBACK_STACKS = frozenset(
    {
        "python",
        "fastapi",
        "django",
        "flask",
        "react",
        "next",
        "vue",
        "nuxt",
        "svelte",
        "typescript",
        "javascript",
        "go",
        "rust",
        "java",
        "kotlin",
        "swift",
        "flutter",
        "laravel",
        "php",
        "blade",
        # Infrastructure-as-Code (lint-only support, not policy-as-code)
        "ansible",
        "terraform",
        "helm",
        "kubernetes",
        "docker",
    }
)


def _load_default_stacks() -> frozenset[str]:
    """Read built-in stack names from the plugin registry.

    Defensive: any failure (missing dir, malformed JSON in user override,
    import error) falls back to `_FALLBACK_STACKS` and logs a warning, so
    `from project_types import DEFAULT_STACKS` never crashes module load.
    """
    try:
        from stack_registry import default_registry

        names = default_registry().all_stacks()
        if not names:
            return _FALLBACK_STACKS
        return frozenset(names)
    except Exception:  # noqa: BLE001 — module import must not crash
        import logging

        logging.getLogger("tausik.project_types").warning(
            "Stack registry unavailable; falling back to hardcoded DEFAULT_STACKS",
            exc_info=True,
        )
        return _FALLBACK_STACKS


DEFAULT_STACKS = _load_default_stacks()
# Backwards-compat alias — older code paths and tests reference VALID_STACKS
# directly. New code should call get_valid_stacks(cfg) so that user-defined
# custom stacks are honoured.
VALID_STACKS = DEFAULT_STACKS


def get_valid_stacks(cfg: dict | None = None) -> frozenset[str]:
    """Return the union of DEFAULT_STACKS and cfg['custom_stacks'].

    Custom stacks are expected to be a list[str] under the top-level
    ``custom_stacks`` config key. Non-string entries, empty strings, and
    a malformed (non-list) value are skipped silently — the framework
    falls back to the built-in set rather than failing the CLI on a
    user typo in config.json.
    """
    if not cfg:
        return DEFAULT_STACKS
    raw = cfg.get("custom_stacks")
    if not isinstance(raw, list):
        return DEFAULT_STACKS
    extra = {s.strip() for s in raw if isinstance(s, str) and s.strip()}
    if not extra:
        return DEFAULT_STACKS
    return frozenset(DEFAULT_STACKS | extra)


VALID_COMPLEXITIES = frozenset({"simple", "medium", "complex"})
VALID_TIERS = frozenset({"trivial", "light", "moderate", "substantial", "deep"})
VALID_MEMORY_TYPES = frozenset(
    {"pattern", "gotcha", "convention", "context", "dead_end"}
)
VALID_EDGE_RELATIONS = frozenset(
    {"supersedes", "caused_by", "relates_to", "contradicts"}
)
VALID_NODE_TYPES = frozenset({"memory", "decision"})
COMPLEXITY_SP = {"simple": 1, "medium": 3, "complex": 8}
