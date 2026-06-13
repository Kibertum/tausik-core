"""Structured root cause for defect tasks — SENAR Core Rule 7
(v15s-rule7-rootcause-hardgate).

The keyword floor in ``service_task_done`` already HARD-blocks closing a
defect task whose notes mention no cause at all. That floor stays
(decision #96). This module adds the *structured* layer on top: a closed
list of root-cause categories plus a parser that recognises the canonical

    Root cause (<category>): <description>. Prevention: <how to avoid>.

shape. A defect that satisfies the keyword floor but is NOT yet in this
structured form gets an *advisory* escalating nudge (never a hard block —
the floor is the only enforced gate). Coverage (% of done defect tasks
carrying a structured root cause) is surfaced in ``tausik metrics``.

Pure module: ``parse_root_cause`` / ``has_structured_root_cause`` need no
DB; ``root_cause_metrics`` takes a query callable (``backend._q``) so it
adds no method to the already-oversized backend modules.
"""

from __future__ import annotations

import re
from typing import Any, Callable

# Closed list of root-cause categories. Keep small and orthogonal — a long
# list defeats the purpose (the agent should pick the obvious bucket, not
# agonise over taxonomy). "other" is the explicit escape hatch.
ROOT_CAUSE_CATEGORIES: tuple[str, ...] = (
    "logic-error",
    "missing-validation",
    "race-condition",
    "config-error",
    "integration-mismatch",
    "regression",
    "edge-case",
    "performance",
    "dependency",
    "documentation",
    "other",
)
_CATEGORIES_SET = frozenset(ROOT_CAUSE_CATEGORIES)

# Canonical shape, bilingual (ru/en) to match the keyword floor. The category
# is captured generically and validated in Python so an *unknown* category is
# a clean "not structured" (AC4), distinguishable in tests from "no structure".
_RC_RE = re.compile(
    r"(?:root\s*cause|причина)\s*"
    r"[\(\[]\s*(?P<cat>[^\)\]]+?)\s*[\)\]]\s*"
    r"[:\-—–]\s*"
    r"(?P<desc>.+?)\s*"
    r"(?:prevention|предотвращение|профилактика)\s*"
    r"[:\-—–]\s*"
    r"(?P<prev>.+?)(?:\n|$)",
    re.IGNORECASE | re.DOTALL,
)


def parse_root_cause(notes: str | None) -> dict[str, str] | None:
    """Extract ``{category, description, prevention}`` from task notes.

    Returns ``None`` (never raises) when notes are empty, the canonical shape
    is absent, the category is outside :data:`ROOT_CAUSE_CATEGORIES`, or either
    the description or prevention is blank. Searches the whole notes blob so a
    single ``task log`` line anywhere is enough.
    """
    if not notes:
        return None
    m = _RC_RE.search(notes)
    if not m:
        return None
    cat = m.group("cat").strip().lower()
    if cat not in _CATEGORIES_SET:
        return None
    desc = m.group("desc").strip()
    prev = m.group("prev").strip()
    if not desc or not prev:
        return None
    return {"category": cat, "description": desc, "prevention": prev}


def has_structured_root_cause(notes: str | None) -> bool:
    """True when ``notes`` carry a valid structured root cause."""
    return parse_root_cause(notes) is not None


def root_cause_metrics(q: Callable[..., list[dict[str, Any]]]) -> dict[str, Any]:
    """Structured-root-cause coverage across *done defect* tasks.

    ``q`` is a backend query callable (``backend._q``) so this stays out of the
    >400-line backend modules. No defect tasks → coverage 0.0 with no division
    by zero (AC4). Best-effort on shape: a row missing ``notes`` counts as
    unstructured rather than raising.
    """
    rows = q("SELECT slug, notes FROM tasks WHERE defect_of IS NOT NULL AND status = 'done'")
    total = len(rows)
    structured = sum(1 for r in rows if has_structured_root_cause(r.get("notes")))
    coverage = (structured / total * 100.0) if total else 0.0
    return {
        "defect_done": total,
        "structured": structured,
        "coverage_pct": round(coverage, 2),
    }
