"""Rule-based classifier: route memory writes to local .tausik or shared brain.

Contract:
    classify(content, category, *, cfg=None) -> Decision

Returns a Decision telling the caller where to write:
    - target="local": content has project-specific markers or blocklist
        hits — keep it in the project's .tausik/tausik.db.
    - target="brain": content looks generalizable — safe for the shared brain.

Three signal sources (applied in order, first hit wins):
    1. Empty/whitespace content -> safe default local.
    2. memory_markers.detect_markers() -> absolute paths, source files,
         tausik command references, 3+-segment slugs.
    3. Union blocklist: cfg['project_names'] ∪ brain_project_registry.
         all_project_names().

Category tweaks: web_cache biases toward brain — slug-like matches (the
noisy class in URL query strings) are suppressed. Other categories treat
any marker as a local signal.

This is a classifier, not a gatekeeper — brain_scrubbing.py still runs
before any actual Notion write. Classification says "where to send";
scrubbing enforces "must not leak secrets".

Zero external deps. Pure function aside from a lazy registry read.
"""

from __future__ import annotations

import os
import sys
from typing import Iterable, Literal, NamedTuple

# memory_markers lives in scripts/hooks/; scripts/ is already on sys.path
# via pyproject.toml (pythonpath=scripts). Mirror the notify_on_done.py
# idiom: make the hooks dir importable without turning it into a package.
_HOOKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks")
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from memory_markers import Match, detect_markers  # noqa: E402

VALID_CATEGORIES = frozenset({"decision", "pattern", "gotcha", "web_cache"})
_BRAIN_BIAS_CATEGORIES = frozenset({"web_cache"})


class Decision(NamedTuple):
    target: Literal["local", "brain"]
    reason: str
    markers: list[Match]
    blocklist_hit: str | None


def _blocklist_names(cfg: dict | None) -> list[str]:
    names: list[str] = []
    if cfg:
        for n in cfg.get("project_names") or []:
            if isinstance(n, str) and n.strip():
                names.append(n)
    try:
        import brain_project_registry

        for n in brain_project_registry.all_project_names():
            if isinstance(n, str) and n.strip() and n not in names:
                names.append(n)
    except Exception:
        # Registry file missing / unreadable → cfg-only blocklist.
        pass
    return names


def _first_blocklist_hit(content: str, names: Iterable[str]) -> str | None:
    haystack = content.lower()
    for name in names:
        needle = name.strip().lower()
        if needle and needle in haystack:
            return name
    return None


def classify(
    content: str,
    category: str,
    *,
    cfg: dict | None = None,
) -> Decision:
    """Route a content blob to 'local' or 'brain' based on markers + blocklist."""
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"category must be one of {sorted(VALID_CATEGORIES)}, got {category!r}"
        )

    if not content.strip():
        return Decision("local", "empty content", [], None)

    markers = detect_markers(content)
    if category in _BRAIN_BIAS_CATEGORIES:
        markers = [m for m in markers if m.kind != "slug"]

    if markers:
        first = markers[0]
        return Decision(
            "local",
            f"{first.kind} marker detected: {first.match!r}",
            markers,
            None,
        )

    hit = _first_blocklist_hit(content, _blocklist_names(cfg))
    if hit is not None:
        return Decision(
            "local",
            f"project name in blocklist: {hit!r}",
            [],
            hit,
        )

    return Decision("brain", "no project-specific markers detected", [], None)
