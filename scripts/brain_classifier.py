"""Rule-based risk score for an EXPLICIT publish to the shared brain.

WHAT THIS NO LONGER DOES (decision #221, 1.8). It used to pick the destination
of a write: run the text past these markers, and a "general"-looking record went
to Notion on its own. That is gone. The rule failed in the direction that costs
something — six of this project's internal decisions were published, each
labelled "no project-specific markers detected", because a well-written record
usually reads generally. Visibility is a judgement about intent, and the words
cannot carry it.

The signals below did not change; their CONSUMER did. The sole production caller
is brain_publish_flow.assess_publish_risk, which maps target="local" to
risk="high" and BLOCKS an already-requested publish until `confirm_high_risk` is
set after human review. Nothing here initiates a write, and no caller branches
on the target to choose a store.

Contract:
    classify(content, category, *, cfg=None) -> Decision

The target field keeps its old name and its old meaning as a JUDGEMENT, not as
a routing instruction:
    - target="local": content has project-specific markers or blocklist
        hits — publishing it is high-risk.
    - target="brain": content looks generalizable — publishing it is low-risk.

Three signal sources (applied in order, first hit wins):
    1. Empty/whitespace content -> safe default local.
    2. memory_markers.detect_markers() -> absolute paths, source files,
         tausik command references, 3+-segment slugs.
    3. Union blocklist: cfg['project_names'] ∪ brain_project_registry.
         all_project_names().

Category tweaks: web_cache biases toward brain — slug-like matches (the
noisy class in URL query strings) are suppressed. Other categories treat
any marker as a local signal.

This is a risk scorer, not the gatekeeper — brain_scrubbing.py still runs
before any actual Notion write. Classification says "how project-specific
this looks"; scrubbing enforces "must not leak secrets".

Zero external deps. Pure function aside from a lazy registry read.
"""

from __future__ import annotations

import os
import sys
from typing import Iterable, Literal, NamedTuple

# memory_markers lives in scripts/hooks/; scripts/ is already on sys.path
# via pyproject.toml (pythonpath=scripts). Add the hooks dir so the module
# is importable without turning the dir into a package.
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
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
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
        raise ValueError(f"category must be one of {sorted(VALID_CATEGORIES)}, got {category!r}")

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
