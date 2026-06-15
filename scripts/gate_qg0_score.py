"""QG-0 intent-dimension scoring for tasks (prompt-master signal).

Extracted from `service_gates.py` for filesize-gate compliance. The function
computes a soft 9-dimension score: a task filling ≥5 is considered well-
contextualized. Hard QG-0 gates (goal, AC, negative scenario) are enforced
inside `service_gates.GateService` itself; this is the diagnostic helper
surfaced via `tausik task show` / `tausik status` so the user can see at a
glance which dimensions are missing.
"""

from __future__ import annotations

import re
from typing import Any


_FILE_RE = re.compile(
    r"\b[\w/.-]+\.(py|js|ts|tsx|jsx|go|rs|java|kt|php|md|json|yaml|yml|sql|sh)\b"
)
_MEMORY_RE = re.compile(r"\bmemory\s*#?\d+\b|\bmem_\d+\b|\b#\d+\s+\[", re.IGNORECASE)


def qg0_dimensions_score(task: dict[str, Any]) -> dict[str, bool]:
    """Score a task against 9 intent dimensions (prompt-master).

    Returns {dimension: bool}. A task filling ≥5 is considered well-contextualized.
    This is a soft signal — hard gates (goal, AC, negative scenario) are enforced elsewhere.
    """

    def _has(field: str) -> bool:
        val = task.get(field)
        return bool(val and str(val).strip())

    ac = (task.get("acceptance_criteria") or "") + " " + (task.get("notes") or "")
    evidence_plan = bool(_FILE_RE.search(ac) or _MEMORY_RE.search(ac))

    return {
        "goal": _has("goal"),
        "acceptance_criteria": _has("acceptance_criteria"),
        "scope": _has("scope"),
        "scope_exclude": _has("scope_exclude"),
        "role": _has("role"),
        "stack": _has("stack"),
        "complexity": _has("complexity"),
        "story_link": _has("story_slug") or _has("epic_slug"),
        "evidence_plan": evidence_plan,
    }
