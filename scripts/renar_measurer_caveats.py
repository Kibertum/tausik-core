"""Confirmations the manifest prints that its measurer has not earned.

`mandatory-clauses-confirmed` prints `true` for every §13.3 clause whose
measurer says so. A measurer known — measured, not suspected — to be incapable
of going red on the violations it exists to catch makes that `true` a published
statement we know to be false, and this module names those.

An entry leaves this list only when its measurer is REPAIRED, never when the
caveat becomes inconvenient. Both original entries left that way: §13.3.3 (the
count of ADAPT rows became named sub-checks in renar_clause_reactive_adapt, and
the clause now reads false) and §13.3.4 (the closed list reached the standard's
eleven, so the confirmation is earned).

THE REGISTRY IS THEREFORE EMPTY, and an empty registry is the dangerous state:
"nothing disclosed" and "nothing to disclose" render identically. So emptiness
must be DECLARED and the declaration must name the repair that produced it —
see REGISTRY_EMPTIED_BY. Deleting the last entry without saying what repaired
it fails a test, exactly as adding an entry without an open task does.

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
MEASURER_CAVEATS: list[dict[str, str]] = []

# The counterpart ratchet. While MEASURER_CAVEATS is empty this must name the
# task whose closure retired the LAST entry, and that task must exist and be
# DONE — the mirror of the rule on entries, which must name a task that is still
# OPEN. Without it, emptying the registry is a one-line deletion that reads as
# "we have no unearned confirmations".
#
# Set back to None the moment an entry is added again.
REGISTRY_EMPTIED_BY: str | None = "spec-closed-list-is-nine-while-the-standard-has-eleven"

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


def header_lines() -> str:
    """The manifest header's paragraph about this registry, matched to its state.

    Kept here rather than in renar_conformance because the claim is about THIS
    module's content: a header that names unearned confirmations while the
    registry is empty overstates the body it introduces — the same defect this
    registry exists to prevent, one level up.
    """
    if MEASURER_CAVEATS:
        return (
            "# NOT every `true` under mandatory-clauses-confirmed is earned: see\n"
            "# `measurer-caveats` below — it names each confirmation whose measurer\n"
            "# cannot go red, and the open task carrying the fix.\n"
        )
    return (
        "# Every `true` under mandatory-clauses-confirmed is EARNED as far as we\n"
        "# know: the measurer-caveats registry is empty, so no section appears\n"
        "# below. That is a statement about our MEASURERS, not a claim of\n"
        "# conformance — for that read `level` and `conformance-declaration`.\n"
    )


def caveated_clauses() -> set[str]:
    """Clause names currently disclosed as unearned."""
    return {c["clause"] for c in MEASURER_CAVEATS}
