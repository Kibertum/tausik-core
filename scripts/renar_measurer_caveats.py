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

The registry was empty between sessions #200 and #202, and emptiness is the
dangerous state: "nothing disclosed" and "nothing to disclose" render
identically. So emptiness must be DECLARED and the declaration must name the
repair that produced it — see REGISTRY_EMPTIED_BY, which is `None` again now
that an entry is back. Deleting the last entry without saying what repaired it
fails a test, exactly as adding an entry without an open task does.

IT DID NOT STAY EMPTY, AND THE ENTRY IS NOT A RELAPSE. §13.3.5 was never
assessed by this registry before: it rode as a literal `True` with its premise
in a comment. Session #202 derived it, and the quality sweep of that same session
measured that the derivation reddened on ADR-013's doc-lint duty — a different
obligation — while remaining unable to red on its own. The verdict went back to a
constant, which is the honest description of what the generator can see, and this
entry is what keeps that constant from reading as a measured result.

That is the same defect the RENAR-1 withdrawal was about: a value printed
without the right to print it (decisions#292). The difference is only that here
we are the ones printing it, into an artifact we just told an external tracker
to read.

EMPTY AGAIN SINCE #213, AND AGAIN BY A REPAIR. The §13.3.5 entry's remaining
complaint was that the header published every `true` as earned while five of
seven were constants. The manifest now publishes a BASIS per clause
(renar_mandatory_clauses: measured / declared / machinery / vacuous) with the
ratchet watching each constant's premise named in the artifact, so a constant
is no longer printed as a measurement anywhere. That disclosure was this
registry's whole purpose for the entry, and it is now carried by the artifact
itself; the entry left, and REGISTRY_EMPTIED_BY names the task.

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
#
# EMPTY AGAIN, BY A REPAIR. The §13.3.5 entry said, in its own last sentence,
# what its remaining problem was: "it is a constant, one of five among seven
# mandatory clauses, and the header publishes every true as earned". Session
# #213 answered that sentence for every clause at once — each verdict now
# carries a BASIS (measured / declared / machinery / vacuous) published beside
# the confirmation, with the ratchet watching each constant's premise named in
# the artifact (renar_mandatory_clauses). §13.3.5 is published as `vacuous`
# with `renar_tc_premise.classes_appeared` named; three of the other four
# constants became measured or declared verdicts with red branches. What this
# entry disclosed is now said by the artifact itself, per clause, which is the
# repair — not the deletion — this registry admits as an exit.
MEASURER_CAVEATS: list[dict[str, str]] = []

# The counterpart ratchet. While MEASURER_CAVEATS is empty this must name the
# task whose closure retired the LAST entry, and that task must exist and be
# DONE — the mirror of the rule on entries, which must name a task that is still
# OPEN. Without it, emptying the registry is a one-line deletion that reads as
# "we have no unearned confirmations".
#
# Set back to None the moment an entry is added again.
REGISTRY_EMPTIED_BY: str | None = "mandatory-clauses-are-constants-published-as-earned"

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
        "# Every `true` under mandatory-clauses-confirmed is earned BY THE MEASURER\n"
        "# that printed it, as far as we know: the measurer-caveats registry is\n"
        "# empty, so no section appears below. That is a statement about our\n"
        "# MEASURERS, not a claim of conformance — for that read `level` and\n"
        "# `conformance-declaration`; and what each verdict rests on is in\n"
        "# `mandatory-clauses-basis` above.\n"
    )


def caveated_clauses() -> set[str]:
    """Clause names currently disclosed as unearned."""
    return {c["clause"] for c in MEASURER_CAVEATS}
