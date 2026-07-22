"""l26-complexity-self-declared: make an understated complexity VISIBLE at close.

Every hard QG-0 gate keys on ``task.complexity in ('medium', 'complex')`` — the
scope_paths requirement (gate_qg0_check) and the rollback_plan requirement.
Complexity is DECLARED BY THE AGENT, so declaring ``simple`` (or leaving it
unset) silently downgrades SENAR Rule 2 and Rule 6 to mere warnings.

This detects the dodge at task-done — the first point an objective signal
exists: the files the task actually touched — and surfaces it instead of letting
it pass in silence (Decision #158). It is ADVISORY, never blocking: the proxy is
deliberately imperfect (a four-file rename is legitimately simple), so a false
positive costs only one advisory line, and the mechanism must never crash the
close (gotcha #271). The point is visibility, not prevention — a low declaration
that dodged the gates is recorded and shown, not punished.
"""

from __future__ import annotations

# Objective ceilings on how many files a task of each declared complexity is
# expected to touch. Deliberately lenient: a simple task legitimately edits one
# or two files; touching MANY is the hallmark of the medium/complex work whose
# scope/rollback gates were dodged. These are the visibility thresholds, not a
# hard gate — raising them only quiets advisories, it never weakens a gate.
_SIMPLE_MAX_FILES = 3
_MEDIUM_MAX_FILES = 10

_RANK = {"simple": 1, "medium": 2, "complex": 3}


def implied_complexity(file_count: int) -> str:
    """The complexity the touched-file count alone would imply."""
    if file_count > _MEDIUM_MAX_FILES:
        return "complex"
    if file_count > _SIMPLE_MAX_FILES:
        return "medium"
    return "simple"


def understatement(declared: str | None, relevant_files: list[str] | None) -> dict | None:
    """Return ``{declared, implied, file_count}`` when the declared complexity is
    LOWER than what the touched-file count implies, else ``None``.

    A ``None``/unknown ``declared`` is treated as ``simple``: an unset complexity
    dodges exactly the same gates as an explicit ``simple`` and so earns the same
    scrutiny. ``complex`` can never be understated (nothing outranks it).
    """
    # De-duplicate before counting: a caller that merges two `git diff` lists,
    # or a wrapper that double-adds a path, would otherwise inflate the count and
    # cross a threshold it should not — an avoidable false-positive advisory.
    files = list(dict.fromkeys(f for f in (relevant_files or []) if f))
    count = len(files)
    declared_key = (declared or "simple").strip().lower()
    declared_rank = _RANK.get(declared_key, 1)  # unknown label -> treat as simple
    implied = implied_complexity(count)
    if _RANK[implied] > declared_rank:
        return {"declared": declared_key, "implied": implied, "file_count": count}
    return None


def warn_if_understated(be, slug: str, declared: str | None, relevant_files) -> str:
    """Detect an understated complexity, record it, and return a visible warning.

    Returns ``""`` when the declaration is honest. Records one supervision
    DETECTION event (``action='complexity_understated'``, details carry only the
    COUNT — never the paths) when it is not. Everything here is best-effort and
    swallowed: it runs inside ``task_done`` and must never block or crash the
    close (Decision #158, gotcha #271).
    """
    try:
        u = understatement(declared, relevant_files)
    except Exception:  # noqa: BLE001 — best-effort: never blocks the close
        return ""
    if u is None:
        return ""
    try:
        be.event_add(
            "supervision",
            slug,
            "complexity_understated",
            f"declared={u['declared']} implied={u['implied']} files={u['file_count']}",
        )
    except Exception:  # noqa: BLE001 — best-effort telemetry, never blocks
        pass
    return (
        f"COMPLEXITY UNDERSTATED: declared '{u['declared']}' but touched "
        f"{u['file_count']} files — implies '{u['implied']}'. QG-0 scope/rollback "
        f"hard gates key on complexity, so a low declaration downgraded SENAR "
        f"Rules 2/6 to warnings. Recorded for audit."
    )
