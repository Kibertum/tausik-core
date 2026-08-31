"""Confirmations the manifest prints that its measurer has not earned.

`mandatory-clauses-confirmed` prints `true` for every §13.3 clause whose
measurer says so. Some of those measurers are known — measured, not suspected —
to be incapable of going red on the violations they exist to catch. Until they
are fixed, the published manifest states something we know to be false.

An entry leaves this list only when its measurer is REPAIRED, never when the
caveat becomes inconvenient. §13.3.3 left it that way (the count of ADAPT rows
became named sub-checks in renar_clause_reactive_adapt) and the clause now
reads false, which is the disclosure the caveat was standing in for.

That is the same defect the RENAR-1 withdrawal was about: a value printed
without the right to print it (decisions#292). The difference is only that here
we are the ones printing it, into an artifact we just told an external tracker
to read.

This module does NOT fix the measurers. It makes the manifest say, in the
artifact itself, which confirmations are not to be relied on and which open task
carries the fix. A caveat is worth less than a repair — but a published false
confirmation with no caveat is worth less than both.
"""

from __future__ import annotations

from typing import Any

# Not a place to park a defect. Every entry names an OPEN task, and a test fails
# when the named task is missing or already closed — otherwise "disclosed"
# quietly becomes a substitute for "fixed".
MEASURER_CAVEATS: list[dict[str, str]] = [
    {
        "clause": "spec-types-closed-list",
        "measured-as": "the 9 SPEC types this project enforces",
        "why-degenerate": (
            "§13.3.4 closes the list at ELEVEN types. Nine of eleven is not a "
            "confirmation of the closed list; the evidence string says 9 and the "
            "confirmation says true."
        ),
        "open-task": "spec-closed-list-is-nine-while-the-standard-has-eleven",
    },
]

DISCLAIMER = (
    "These confirmations are printed by a measurer we know cannot go red on the "
    "violations it exists to catch. This section is a DISCLOSURE, not a repair: "
    "it does not fix the measurers and does not substitute for closing the named "
    "tasks."
)


def caveats_section() -> dict[str, Any]:
    """The manifest's `measurer-caveats` block, or {} when there is nothing to say."""
    if not MEASURER_CAVEATS:
        return {}
    return {
        "disclaimer": DISCLAIMER,
        "unearned-confirmations": [dict(c) for c in MEASURER_CAVEATS],
    }


def caveated_clauses() -> set[str]:
    """Clause names currently disclosed as unearned."""
    return {c["clause"] for c in MEASURER_CAVEATS}
