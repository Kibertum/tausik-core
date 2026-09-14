"""Obligations the standard states that do not reach us, declared out loud.

§13.3.3 p.90 names it as a negative scenario when a SPEC is produced from a ТЗ
carrying neither `source.tz-section` nor `source.adapt`, and ADR-006's source
table (p.76) makes `source.tz-section` mandatory on a SPEC always. Our three
SPECs carry no provenance field at all, and the substrate has no column to hold
one — the sub-check `spec-provenance-source` reads red, correctly.

WHY A DECLARATION AND NOT A REPAIR. The obligation presupposes a ТЗ. We have no
ТЗ as an artifact: the SPEC anchor `renar-adoption` points at `decisions#109`, a
record in our own database, and the owner ruled in session #209 (decision #307)
that this is NOT our ТЗ and that the absence is to be declared explicitly rather
than passed over in silence. A missing field says nothing; it looks identical to
an oversight, and an auditor cannot tell one from the other. This module makes
the artifact say which obligation does not reach us, on whose ruling, and where
the reasoning is recorded.

WHAT THIS IS NOT. It is not `renar_measurer_caveats`, and merging the two would
blur the only thing that matters about either. That registry says "the measurer
cannot go red on what it exists to catch" — a statement about OUR machinery,
whose exit is a REPAIR. This one says "the obligation has no subject here" — a
statement about the WORLD, whose exit is the world changing. Different claims,
different exits, different readers.

A DECLARATION IS NOT COMPLIANCE, and nothing here turns a sub-check green. The
red stays red; what changes is that the artifact now carries the reason next to
it.

THE PREMISE IS A CLAIM ABOUT THE WORLD, SO IT NEEDS A RATCHET. "No ТЗ exists"
was true when it was declared and is not guaranteed to stay true. The moment a
SPEC carries `source_tz_section`, the declaration over-reaches, and
:func:`premise_broken` is what notices. Like `renar_tc_premise.classes_appeared`
it compares against OUR declaration, so it is meaningful only against the live
project database and is deliberately NOT what the manifest section rests on —
the section is derived from whatever database it is handed.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from renar_br_premise import CONTROL_POINT_DECLARATION, premise_broken as _br_premise_broken
from renar_clause_reactive_adapt import SPEC_PROVENANCE_FIELDS

# The provenance field whose absence the owner's ruling is about. A SPEC may
# legitimately carry `source_adapt` instead — that is the other branch §13.3.3
# admits, and it does not depend on a ТЗ existing. Taken from the clause
# module's closed list rather than spelled again here, so a field renamed there
# cannot leave this watching a name nothing writes.
# That it really is one of them is asserted by a test, not by an `assert` here:
# a runtime check would fire at import in production for a mistake only a
# developer can make.
TZ_PROVENANCE_FIELD = "source_tz_section"

# The declaration itself is a LITERAL: it records a ruling, and a ruling is not
# derivable from the database it is about. What IS derived is its reach — see
# `section`, which never enumerates the artifacts it covers.
DECLARATIONS: list[dict[str, str]] = [
    {
        "clause": "§13.3.3 p.90 (negative scenario) / ADR-006 source table p.76",
        "obligation": (
            "a SPEC carries source.tz-section, always, for traceability; producing one "
            "from a ТЗ with neither source.tz-section nor source.adapt is the negative "
            "scenario stated literally"
        ),
        "inapplicable-because": (
            "the obligation presupposes a ТЗ, and no ТЗ exists here as an artifact. The "
            "SPEC anchor renar-adoption references decisions#109 — a record in our own "
            "database, not a specification handed to us — and the ADAPT relationship "
            "runs from ADAPT to SPEC, the direction opposite to the one the clause reads."
        ),
        "decided-by": "owner ruling, decision #307 (session #209)",
        "evidence-ref": "renar-first-tz-adapt",
        "not-a-claim-of-compliance": (
            "the sub-check spec-provenance-source stays RED; this declaration supplies "
            "the reason for the red, it does not remove it"
        ),
        "premise-watched-by": "renar_normative_inapplicability.premise_broken",
    },
    {
        "clause": "ADR-007 check-adapt-supersession, §10.11.1 p.485",
        "obligation": (
            "a control point catches a source.adapt reference left pointing at a "
            "withdrawn (superseded) ADAPT"
        ),
        "inapplicable-because": (
            "only for the SPEC half of the reference. `specs` holds none of the three "
            "provenance columns and decision #307 adds none, so a source.adapt "
            "reference cannot be written, let alone dangle — a gate over it would be "
            "the degenerate control this clause exists to prevent. The half that DOES "
            "have a subject was built instead: adapts.parent_adapt is a real column "
            "with a real foreign key, and renar_drift.detect_supersession_drift "
            "catches a delta-ADAPT hanging off a superseded parent."
        ),
        "decided-by": "owner ruling, decision #307 (session #209), applied in session #212",
        "evidence-ref": "check-adapt-supersession-gate-has-no-subject-yet",
        "premise-watched-by": "renar_normative_inapplicability.spec_adapt_reference_possible",
        "not-a-claim-of-compliance": (
            "the gate exists and RUNS over the carrier that exists; what is declared "
            "inapplicable is only the SPEC-side reference, which no column can hold"
        ),
    },
    # §13.3.8 / §10.11.1 (RENAR v1.1): the control-point half of the eighth
    # clause; the verdict half is `implements-edge-subsystem` in the clauses.
    CONTROL_POINT_DECLARATION,
]

# Emptiness must be DECLARED, never merely reached: "nothing to disclose" and
# "nobody wrote anything down" render identically, and only one of them is a
# statement. Deleting the last declaration without naming what made it
# unnecessary fails a test — the same discipline `renar_measurer_caveats` keeps.
REGISTRY_EMPTIED_BY: str | None = None

DISCLAIMER = (
    "Obligations of the standard that have no subject in this project, declared "
    "rather than passed over in silence. A declaration is NOT compliance: every "
    "sub-check these touch stays exactly as red as it was, and each entry names "
    "the premise that would end it."
)


def _provenance_columns(conn: sqlite3.Connection) -> tuple[str, ...]:
    """Which provenance fields the substrate can actually hold, if any."""
    cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(specs)")}
    return tuple(c for c in SPEC_PROVENANCE_FIELDS if c in cols)


def _spec_slugs(conn: sqlite3.Connection) -> tuple[str, ...]:
    return tuple(str(r[0]) for r in conn.execute("SELECT slug FROM specs ORDER BY slug"))


def _has_specs_table(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='specs'").fetchone()
    return row is not None


def covered_specs(conn: sqlite3.Connection) -> tuple[str, ...]:
    """The live SPECs this declaration reaches: those carrying no provenance at all.

    DERIVED, never enumerated. A fourth SPEC added tomorrow is covered the day it
    appears, and a SPEC that gains a provenance field leaves the declaration's
    reach without anyone remembering to edit a list.
    """
    if not _has_specs_table(conn):
        return ()
    cols = _provenance_columns(conn)
    if not cols:
        # No column can hold provenance, so every SPEC is bare by construction.
        return _spec_slugs(conn)
    bare = " AND ".join(f"({c} IS NULL OR {c}='')" for c in cols)
    return tuple(
        str(r[0]) for r in conn.execute(f"SELECT slug FROM specs WHERE {bare} ORDER BY slug")
    )


def premise_broken(conn: sqlite3.Connection) -> tuple[str, ...]:
    """SPECs that DO name a ТЗ section — the declaration's premise failing.

    A STATEMENT ABOUT OUR DECLARATION, NOT ABOUT A DATABASE. `eval_mandatory_clauses`
    runs against whatever database it is handed, fixtures included, and a fixture
    that adds the column and fills it is not the project this ruling was made
    about. So this is not what the manifest section rests on; its consumer is the
    repository's own guard test, run against the live project database.

    An empty result is the premise holding. A non-empty one means a ТЗ arrived
    and the declaration must be re-decided by its owner, not quietly widened.
    """
    if not _has_specs_table(conn) or TZ_PROVENANCE_FIELD not in _provenance_columns(conn):
        return ()
    return tuple(
        str(r[0])
        for r in conn.execute(
            f"SELECT slug FROM specs WHERE {TZ_PROVENANCE_FIELD} IS NOT NULL "
            f"AND {TZ_PROVENANCE_FIELD} != '' ORDER BY slug"
        )
    )


def spec_adapt_reference_possible(conn: sqlite3.Connection) -> bool:
    """Can a SPEC name an ADAPT at all — the second declaration's premise, inverted.

    That declaration says the SPEC half of `check-adapt-supersession` has no
    subject, and the reason is narrower than "no ТЗ": the column simply is not
    there, so no reference exists to dangle. The moment `source_adapt` appears,
    the reference becomes writable, the SPEC half acquires a subject, and the
    gate must be widened to cover it — this returning True is what says so.

    Deliberately about the COLUMN, not about rows. A column with no rows yet is
    already a subject; a column that does not exist is not one. That is the same
    distinction the detector's own docstring turns on, and getting it backwards
    is how a gate over nothing gets built.
    """
    return "source_adapt" in _provenance_columns(conn) if _has_specs_table(conn) else False


def implements_edge_carrier_exists(conn: sqlite3.Connection) -> bool:
    """Can a §13.3.8 implements-edge be written at all — the third declaration's
    premise, inverted. Delegates to `renar_br_premise.premise_broken`, which reads
    the schema for a BR class, a `level` admitting `subsystem`, or an `implements`
    column. True means the control point has acquired a subject and the
    declaration must be re-decided, not widened."""
    return bool(_br_premise_broken(conn))


def section(conn: sqlite3.Connection) -> dict[str, Any]:
    """The manifest's `normative-inapplicability` block, or {} when empty.

    Dropped entirely when there is nothing declared: a bare
    `normative-inapplicability: {}` reads as searched-and-found-none, which is a
    stronger claim than an empty registry supports.
    """
    if not DECLARATIONS:
        return {}
    covered = covered_specs(conn)
    return {
        "disclaimer": DISCLAIMER,
        "declarations": [{**d, "applies-to": list(covered)} for d in DECLARATIONS],
    }
