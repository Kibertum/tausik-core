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
        "clause": "tc-pos-neg-pairing",
        "measured-as": (
            "constant true: the clause is vacuous while no TC artifact class exists, "
            "and the manifest generator cannot observe the arrival of one"
        ),
        "why-degenerate": (
            "The premise is honest and re-measured — no TC table exists under any "
            "name. What the CLAUSE cannot do is notice when that stops being true. "
            "The ratchet that notices (renar_tc_premise.classes_appeared) compares "
            "the live classes against OUR declaration, so it is meaningless on any "
            "other database, and eval_mandatory_clauses runs on whatever database "
            "it is handed — every fixture included. Deriving the verdict from the "
            "remaining finding was tried in #202 and was worse: a SPEC-DOC artifact "
            "belongs to ADR-013's doc-lint duty, so the clause reddened on an "
            "unrelated obligation while still staying green on its own. It reds "
            "only via the ADR-013 guard test, which since #203 runs in any "
            "checkout — it reads the canonical schema rather than a live database, "
            "so CI executes it. What remains is the clause itself: it is a "
            "constant, one of five among seven mandatory clauses, and the header "
            "publishes every true as earned."
        ),
        # RE-POINTED IN #203, NOT RETIRED. The sentence above used to end "which
        # CI does not have", and closing db-gated-ratchets-never-run-in-ci made
        # that false — so it was corrected rather than left standing. But that
        # task fixed WHERE the ratchet runs, not the degeneracy this caveat
        # discloses: the clause is still a constant that cannot notice a TC class
        # arriving. Retiring the caveat because its old open-task closed would
        # have been the deletion this registry exists to prevent, so it now names
        # the task that actually holds the remaining problem.
        "open-task": "mandatory-clauses-are-constants-published-as-earned",
    }
]

# The counterpart ratchet. While MEASURER_CAVEATS is empty this must name the
# task whose closure retired the LAST entry, and that task must exist and be
# DONE — the mirror of the rule on entries, which must name a task that is still
# OPEN. Without it, emptying the registry is a one-line deletion that reads as
# "we have no unearned confirmations".
#
# Set back to None the moment an entry is added again.
REGISTRY_EMPTIED_BY: str | None = None

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
