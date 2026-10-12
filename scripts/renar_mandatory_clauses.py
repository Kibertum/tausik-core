"""The eight mandatory clauses (§13.3), each with the BASIS its verdict rests on.

Seven under RENAR v1.0; v1.1 added §13.3.8 (implements-edge on subsystem BR),
assessed in session #250 (decision #364) as `vacuous` — see renar_br_premise.

`mandatory-clauses-confirmed` prints a bare ``true`` per clause, and the header
said every ``true`` was earned. Measured in session #213: of the seven, two
were derived from the substrate (§13.3.3, §13.3.5's premise) and five were
constants — ``True`` in a dict, three of them with an evidence string naming
a count as if a check had run. Planting the violation each clause names left
all five green (table in the task journal). Session #200 repaired §13.3.3 and
#202 §13.3.5 one at a time; the question "how many more" was never asked.

WHAT CHANGES. Every clause now carries a ``basis`` from a closed list, and the
manifest publishes it beside the confirmation:

* ``measured`` — derived from the database in hand, with a red branch a test
  can reach: §13.3.3 (reactive ADAPT), §13.3.4 (SPEC types), §13.3.7 (closed
  lists). A violating state turns the clause ``false``.
* ``declared`` — derived from a declaration this manifest itself publishes:
  §13.3.6 reads the ``quality-gates`` block and reddens on a sixth gate id, a
  core gate not ``required``, an optional gate in a state the standard does
  not admit. The block is the project's statement; the clause checks the
  statement's shape against the standard.
* ``machinery`` — true because the running framework enforces it, not because
  a row says so: §13.3.1 (task before code, verify before close) and §13.3.2
  (git + sqlite). The premise "the machinery is switched on" is watched by a
  repository test named in the artifact, so the constant cannot outlive it.
* ``vacuous`` — the obligation has no subject here: §13.3.5, no TC class.
  Honest, and unable to see the subject arrive; the ratchet that sees it is
  named in the artifact (``renar_tc_premise.classes_appeared`` on the live
  database).

A constant is not a lie; a constant PUBLISHED AS A MEASUREMENT is. The basis
block is what makes the artifact say which is which — the disclosure the
``measurer-caveats`` entry for §13.3.5 used to carry alone, generalised to
every clause and retired from that registry (``REGISTRY_EMPTIED_BY``).
"""

from __future__ import annotations

from typing import Any

from renar_br_premise import BR_PREMISE_WATCH, implements_edge_clause
from renar_clause_reactive_adapt import Subcheck

# Closed list of bases. A clause carries exactly one.
BASIS_KINDS = ("measured", "declared", "machinery", "vacuous")

# §13.3.6 / §10.4.4 — the standard's closed list of gate ids and the states it
# admits. Declarations of the STANDARD's lists (literals on purpose: the
# standard is external and not derivable from our database).
CLOSED_GATE_IDS = ("qg-0", "qg-1", "qg-2", "qg-3", "qg-4")
CORE_GATES = ("qg-0", "qg-1", "qg-2")
OPTIONAL_GATE_STATES = ("required", "declared", "absent")
CLAUSE_13_3_6 = "§13.3.6 (closed list of Quality Gates, §10.4.4 declaration)"

# THE PROJECT'S DECLARATION, in one place. `build_manifest` publishes it and
# `quality_gates_clause` judges it; before, the block was a literal inside the
# manifest builder and the clause never read it.
QUALITY_GATES_DECLARED: dict[str, str] = {
    "qg-0": "required",
    "qg-1": "required",
    "qg-2": "required",
    "qg-3": "declared",
    "qg-4": "absent",
}


def quality_gates_clause(declared: dict[str, str]) -> dict[str, Any]:
    """§13.3.6 judged over the declaration the manifest publishes.

    A pure function of its argument so the red branches are reachable: a gate
    id outside the closed list, a core gate declared anything but
    ``required``, an optional gate in a state §10.4.4 does not admit.
    """
    ids = Subcheck(
        "gate-ids-closed",
        set(declared) == set(CLOSED_GATE_IDS),
        CLAUSE_13_3_6,
        (
            f"exactly the {len(CLOSED_GATE_IDS)} gate ids of the closed list are declared"
            if set(declared) == set(CLOSED_GATE_IDS)
            else f"declared {sorted(set(declared) - set(CLOSED_GATE_IDS))} beyond the closed list, "
            f"missing {sorted(set(CLOSED_GATE_IDS) - set(declared))}"
        ),
    )
    not_required = [g for g in CORE_GATES if declared.get(g) != "required"]
    core = Subcheck(
        "core-gates-required",
        not not_required,
        CLAUSE_13_3_6,
        (
            "qg-0..qg-2 are declared required"
            if not not_required
            else f"core gate(s) not declared required: {not_required}"
        ),
    )
    optional = [g for g in CLOSED_GATE_IDS if g not in CORE_GATES]
    bad_state = {
        g: declared.get(g) for g in optional if declared.get(g) not in OPTIONAL_GATE_STATES
    }
    states = Subcheck(
        "optional-gate-states-admitted",
        not bad_state,
        CLAUSE_13_3_6,
        (
            "optional gates carry an admitted state"
            if not bad_state
            else f"optional gate state(s) the standard does not admit: {bad_state}"
        ),
    )
    subchecks = [ids, core, states]
    failed = [s.name for s in subchecks if not s.ok]
    return {
        "confirmed": not failed,
        "evidence": (
            f"{CLAUSE_13_3_6}: all {len(subchecks)} sub-checks hold"
            if not failed
            else f"{CLAUSE_13_3_6}: failed {failed}"
        ),
        "subchecks": [s.as_dict() for s in subchecks],
    }


# Where each non-measured premise is watched. Named in the artifact so a
# reader can go there; asserted by tests so the names cannot rot.
SOT_INVERSION_WATCH = (
    "tests/test_renar_mandatory_clauses.py::test_the_machinery_sot_inversion_rests_on_is_switched_on "
    "(verify_first blocking and enabled in the live gate registry; task_gate.py wired on "
    "BUILTIN_WRITE_MATCHER in bootstrap_hooks)"
)
SUBSTRATE_WATCH = (
    "tests/test_events_chain.py (V1 hash-chain of the event journal) and "
    "tests/test_renar_manifest_chain.py (the manifest's git audit journal)"
)
TC_PREMISE_WATCH = (
    "renar_tc_premise.classes_appeared via tests/test_renar_tc_premise.py, on the live "
    "project database — the only database the declaration describes; and the ADR-013 "
    "guard test (tests/test_spec_types_closed_list.py), which watches the same premise "
    "more broadly but SKIPS IN CI, because .tausik/ is gitignored and no workflow "
    "creates the database (task db-gated-ratchets-never-run-in-ci)"
)


def eval_mandatory_clauses(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The eight §13.3 verdicts, each with ``confirmed``, ``evidence`` and ``basis``."""
    s = bundle["signals"]
    return {
        # §13.3.1 — policy clause. The violations it names (reverse-engineering
        # SR from code, silent SR adaptation) need an SR class; none exists.
        # The positive duty holds by machinery: task before code (QG-0 hook),
        # verify before close (QG-2 gate). Not derivable from rows.
        "sot-inversion": {
            "confirmed": True,
            "evidence": "QG-0 task-before-code + QG-2 verify-first policy enforced",
            "basis": "machinery",
            "premise-watched-by": SOT_INVERSION_WATCH,
        },
        "substrate-v1-v6": {
            "confirmed": s["substrate_v1_v6"],
            "evidence": "git + sqlite WAL",
            "basis": "machinery",
            "premise-watched-by": SUBSTRATE_WATCH,
        },
        # §13.3.3 — named sub-checks (renar_clause_reactive_adapt).
        "adapt-per-tz": {**bundle["clause_13_3_3"], "basis": "measured"},
        # §13.3.4 — the substrate's CHECK against the declared list, plus rows.
        "spec-types-closed-list": {**bundle["clause_13_3_4"], "basis": "measured"},
        # §13.3.5 — vacuous while no TC class exists (renar_tc_premise).
        "tc-pos-neg-pairing": {
            **bundle["clause_13_3_5"],
            "basis": "vacuous",
            "premise-watched-by": TC_PREMISE_WATCH,
        },
        # §13.3.6 — judged over the published quality-gates declaration.
        "quality-gates-closed-list": {
            **quality_gates_clause(QUALITY_GATES_DECLARED),
            "basis": "declared",
        },
        # §13.3.7 — backward-finding categories and ADAPT statuses, measured.
        "closed-lists-backward-findings": {**bundle["clause_13_3_7"], "basis": "measured"},
        # §13.3.8 (v1.1) — vacuous while no BR class exists (renar_br_premise).
        "implements-edge-subsystem": {
            **implements_edge_clause(),
            "basis": "vacuous",
            "premise-watched-by": BR_PREMISE_WATCH,
        },
    }


BASIS_DISCLAIMER = (
    "What each confirmation above RESTS ON. `measured`: derived from this database, "
    "with a violating state turning it false. `declared`: judged over a declaration "
    "this manifest publishes. `machinery`: true because the running framework enforces "
    "it, the premise watched by the named repository test. `vacuous`: the obligation has "
    "no subject here, the arrival of one watched by the named ratchet. A constant is not "
    "a measurement, and this block is what keeps the two from reading alike."
)


def basis_section(clauses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The manifest's `mandatory-clauses-basis` block, one entry per clause."""
    out: dict[str, Any] = {"disclaimer": BASIS_DISCLAIMER}
    for name, c in clauses.items():
        entry: dict[str, Any] = {"basis": c["basis"]}
        if "premise-watched-by" in c:
            entry["premise-watched-by"] = c["premise-watched-by"]
        out[name] = entry
    return out


def basis_header_lines() -> str:
    """The manifest header's paragraph about bases — a constant is named as one."""
    return (
        "# A `true` under mandatory-clauses-confirmed is not always a MEASUREMENT:\n"
        "# `mandatory-clauses-basis` says, per clause, whether it was measured,\n"
        "# judged over a published declaration, holds by running machinery, or\n"
        "# is vacuous — and where the premise of each constant is watched.\n"
    )
