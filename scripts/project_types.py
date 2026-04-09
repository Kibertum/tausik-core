"""TAUSIK types -- constants and validation sets."""

from __future__ import annotations

# --- Constants ---

VALID_TASK_STATUSES = frozenset({"planning", "active", "blocked", "review", "done"})
VALID_STORY_STATUSES = frozenset({"open", "active", "done"})
VALID_EPIC_STATUSES = frozenset({"active", "done", "archived"})
VALID_STACKS = frozenset(
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
    }
)
VALID_COMPLEXITIES = frozenset({"simple", "medium", "complex"})
VALID_MEMORY_TYPES = frozenset(
    {"pattern", "gotcha", "convention", "context", "dead_end"}
)
VALID_EDGE_RELATIONS = frozenset(
    {"supersedes", "caused_by", "relates_to", "contradicts"}
)
VALID_NODE_TYPES = frozenset({"memory", "decision"})
COMPLEXITY_SP = {"simple": 1, "medium": 3, "complex": 8}
