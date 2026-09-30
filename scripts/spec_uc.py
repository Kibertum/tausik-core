"""SPEC-UC body check (RENAR 1.1 §8.5.12, §8.5.12.1, ADR-018).

A use case names who acts — `role: human | agent` — and every step points at
the statement it exercises, addressed as `<artifact-id>#n` (§15.1.1: the n-th
sentence of the normative section of that artifact). A step without a ref is a
structural-completeness violation (§8.5.12.1), so `spec add --type UC` refuses
it here instead of letting the gap reach QG-0 of the description set.

What counts as a step: a numbered list line (`1. …`, `2) …`) in the body. What
counts as a ref: a token `SOMETHING-ID#<digits>` — e.g. `SPEC-UI-login#3`,
`SR-012#1`. The check is structural on purpose; whether the referenced statement
exists is the business of the coverage control, not of this parser.
"""

from __future__ import annotations

import re

_ROLE = re.compile(r"^\s*role\s*:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)
_STEP = re.compile(r"^\s*(\d+)[.)]\s+(.*\S)\s*$", re.MULTILINE)
_REF = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Za-z0-9_]+)+#\d+\b")
ROLES = ("human", "agent")


def check_uc_body(body: str) -> list[str]:
    """Problems with a SPEC-UC body, as sentences; [] when it is structurally complete."""
    problems: list[str] = []
    m = _ROLE.search(body or "")
    if not m:
        problems.append("no `role:` line — a use case names its actor: human | agent (§8.5.12)")
    elif m.group(1).lower() not in ROLES:
        problems.append(f"role {m.group(1)!r} is not one of human | agent (§8.5.12)")
    steps = _STEP.findall(body or "")
    if not steps:
        problems.append("no numbered steps — a use case is a sequence of steps (§8.5.12)")
    for num, text in steps:
        if not _REF.search(text):
            problems.append(f"step {num} has no statement ref `<id>#n` (§8.5.12.1): {text[:60]!r}")
    return problems
