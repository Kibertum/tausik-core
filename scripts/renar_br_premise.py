"""§13.3.8 (`implements`-edge on subsystem BR): vacuous here, and watched.

RENAR v1.1 added an eighth mandatory clause. For the scenario "a subsystem is a
product of its own" (§6.8.2) a BR with `level = subsystem`, whose parent system
holds at least one approved BR, must carry `implements[]` pointing at an
applicable BR of the parent; the carrier must run the `implements`-edge
validation control point of §10.11.1 (target inside the approved set version,
no cycles, excluded target → warning, no `implements[]` on `level: system`).

WHY THE VERDICT IS VACUOUS AND NOT A REPAIR. The clause's subject is a BR class
with a `level`. This substrate holds none: `specs`, `adapts`, `actz` and the
task/spec links are the requirement-side classes, and no column anywhere holds
a system/subsystem level. The word `implements` does occur here twice, and
neither occurrence is the edge the clause names:

  * `task_specs.relation = 'implements'` — a task implementing a SPEC;
  * the artifact graph's `implements` relation — code implementing a requirement.

Both run from work to requirement. §13.3.8's edge runs BR → BR across two
levels of one hierarchy, and nothing here can hold either end of it. A gate over
that edge would be the degenerate control §13.9.4 forbids — exactly the shape
`renar_normative_inapplicability` already declares for the SPEC half of
check-adapt-supersession.

THE PREMISE IS A CLAIM ABOUT THE WORLD, SO IT NEEDS A RATCHET. "No BR class, no
level" was true when declared (session #250, corpus commit c3dd6b0) and is not
guaranteed to stay true. `premise_broken` reads the schema, not a list: the day a
table carries a `level` column admitting `subsystem`, a table named for business
requirements, or a column named `implements`, the declaration over-reaches and
the guard test in tests/test_renar_br_premise.py goes red on the canonical schema —
the schema `tausik init` creates, which is what the declaration is about (the same
distinction `renar_tc_premise.classes_appeared` turns on, minus its CI gap).
"""

from __future__ import annotations

import re
import sqlite3

# Names a BR class would plausibly take. A list on purpose: the ratchet must
# see an arrival under any of them, and the schema check on `level` below is
# the net for a name this list did not guess.
BR_TABLE_NAMES = frozenset({"business_requirements", "requirements", "br", "brs"})
IMPLEMENTS_COLUMN = "implements"
SUBSYSTEM_LEVEL = "subsystem"

# A `level` column whose declaration admits `subsystem` — the CHECK list is
# comma-separated, so the window is a span, not "up to the next comma". A ratchet
# may err towards red: a false red is read by a person, a false green by no one.
_LEVEL_WITH_SUBSYSTEM = re.compile(
    r"\blevel\b.{0,200}?\b" + re.escape(SUBSYSTEM_LEVEL) + r"\b", re.IGNORECASE | re.DOTALL
)

CLAUSE = "§13.3.8 (implements-edge on subsystem BR; §10.11.1 control point)"

BR_PREMISE_WATCH = (
    "renar_br_premise.premise_broken via tests/test_renar_br_premise.py, on the canonical "
    "schema (conftest.canonical_schema_db — what `tausik init` creates, from git, so it "
    "RUNS IN CI); it reads the schema for a `level` column admitting `subsystem`, a "
    "BR-named table or an `implements` column, not a list of names"
)


def _tables(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    return [
        (str(r[0]), str(r[1] or ""))
        for r in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    ]


def level_carriers(conn: sqlite3.Connection) -> tuple[str, ...]:
    """Tables that could hold a subsystem-level BR: named for BR, or carrying a
    `level` column whose declaration admits `subsystem`."""
    out = []
    for name, sql in _tables(conn):
        if name.lower() in BR_TABLE_NAMES or _LEVEL_WITH_SUBSYSTEM.search(sql):
            out.append(name)
    return tuple(sorted(out))


def implements_edge_carriers(conn: sqlite3.Connection) -> tuple[str, ...]:
    """Tables with a column named `implements` — a place the edge could be written.

    A column, not a value: `task_specs.relation` may hold the string 'implements'
    and that is a task→SPEC link, not this edge. A column named `implements` on
    any table is a new place to write BR → BR, and that is what the ratchet is for.
    """
    out = []
    for name, _sql in _tables(conn):
        cols = {str(r[1]).lower() for r in conn.execute(f'PRAGMA table_info("{name}")')}
        if IMPLEMENTS_COLUMN in cols:
            out.append(name)
    return tuple(sorted(out))


def premise_broken(conn: sqlite3.Connection) -> tuple[str, ...]:
    """Carriers that would give §13.3.8 a subject — the declaration's premise failing.

    A STATEMENT ABOUT OUR DECLARATION, NOT ABOUT A DATABASE: a fixture that creates
    a `business_requirements` table is not the project this ruling was made about.
    Its consumer is the repository's guard test on the live database. An empty
    result is the premise holding; a non-empty one means the clause has acquired a
    subject and must be re-assessed — by measurement, not by widening this text.
    """
    return tuple(
        sorted(
            {f"table {t} (level/BR class)" for t in level_carriers(conn)}
            | {f"table {t} (implements column)" for t in implements_edge_carriers(conn)}
        )
    )


def implements_edge_clause() -> dict[str, object]:
    """§13.3.8 `implements-edge-subsystem`, derived from the premise instead of written.

    TAKES NO ARGUMENT, like `renar_tc_premise.pairing_clause` and for the same
    reason: the published verdict must not red on a fixture database that is not
    the one the declaration is about, and it cannot see the arrival itself — the
    ratchet that sees it is named in `premise-watched-by`.
    """
    return {
        "confirmed": True,
        "evidence": (
            "no BR class and no level column in the substrate → the subsystem "
            "implements-edge obligation is vacuous (§13.3.8); the two `implements` "
            "occurrences here (task_specs.relation, artifact-graph relation) run from "
            "work to requirement, not BR → BR; this clause cannot observe a BR class "
            "arriving — its basis is published as `vacuous` and renar_br_premise."
            "premise_broken watches the canonical schema on every test run"
        ),
    }


# The §10.11.1 control-point half, declared under normative-inapplicability.
CONTROL_POINT_DECLARATION: dict[str, str] = {
    "clause": "§13.3.8 / §10.11.1 implements-edge validation (RENAR v1.1)",
    "obligation": (
        "the carrier runs an implements-edge validation control point: target BR inside "
        "the approved set version of its system, no cycles, excluded target → warning, "
        "no implements[] on level: system"
    ),
    "inapplicable-because": (
        "no table holds a BR, a level, or an implements column, so an implements[] edge "
        "cannot be written, let alone validated — a gate over it would be the degenerate "
        "control §13.9.4 exists to prevent. The mandatory-clause half is published as "
        "`vacuous` (implements-edge-subsystem) rather than hidden here."
    ),
    "decided-by": "owner instruction, decision #364 (session #250), corpus v1.1 at c3dd6b0",
    "evidence-ref": "renar-corpus-v11-reassessment",
    "not-a-claim-of-compliance": (
        "nothing validates an edge that cannot exist; what is declared is that the "
        "obligation has no subject, and the ratchet that would end the declaration is "
        "named"
    ),
    # Watchers of declarations live in the declaring module, by that module's
    # own contract; it delegates to `premise_broken` here.
    "premise-watched-by": "renar_normative_inapplicability.implements_edge_carrier_exists",
}
