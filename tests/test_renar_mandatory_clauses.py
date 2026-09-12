"""Every mandatory clause carries a basis, and no constant is published as a measurement.

The measurement table of session #213 (task journal) showed five of seven
verdicts unable to go red on the violation their clause names. This file pins
the repair: the bases, the red branches of the verdicts that became measured or
declared, the ratchets watching the constants, and the artifact that says it.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
# `bootstrap/` too: the §13.3.1 machinery watch below reads the hook SOURCE. Only
# test_bootstrap_hooks_parity.py added this path, and it happens to sort before
# this file — so the watch passed in a full run and errored on import when this
# file ran alone. A test whose result depends on collection order is not a watch
# (found by review of this very change).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

import renar_conformance  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from renar_mandatory_clauses import (  # noqa: E402
    BASIS_KINDS,
    CLOSED_GATE_IDS,
    QUALITY_GATES_DECLARED,
    basis_header_lines,
    basis_section,
    eval_mandatory_clauses,
    quality_gates_clause,
)

MANIFEST = os.path.join(os.path.dirname(__file__), "..", "RENAR-CONFORMANCE.yaml")


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "mc.db")))
    yield s
    s.be.close()


def _clauses(svc):
    return eval_mandatory_clauses(renar_conformance.gather_signals(svc.be._conn))


# --- bases ---------------------------------------------------------------------


def test_every_clause_carries_a_basis_from_the_closed_list(svc):
    clauses = _clauses(svc)
    assert len(clauses) == 8, sorted(clauses)
    for name, c in clauses.items():
        assert c["basis"] in BASIS_KINDS, f"{name}: basis {c.get('basis')!r}"
        assert c["evidence"].strip(), f"{name}: evidence is empty"


def test_every_constant_names_where_its_premise_is_watched(svc):
    """A constant may be published only with the ratchet that would end it named."""
    for name, c in _clauses(svc).items():
        if c["basis"] in ("machinery", "vacuous"):
            assert c.get("premise-watched-by", "").strip(), f"{name}: no premise-watched-by"
        else:
            assert "premise-watched-by" not in c, f"{name}: a measured verdict needs no watch"


def test_the_vacuous_clause_names_every_watch_it_rests_on(svc):
    """NEGATIVE SCENARIO, found by external review #40: the basis block replaced
    a `measurer-caveats` entry that said MORE.

    v17's caveat named the ADR-013 guard test as a second, broader watch on the
    §13.3.5 premise and said it skips in CI; v18's first basis entry named only
    the live-database ratchet, so a reader of the artifact alone learned LESS
    about how the clause is defended than before — in the very change whose
    subject is publishing what a `true` rests on.
    """
    watch = _clauses(svc)["tc-pos-neg-pairing"]["premise-watched-by"]
    assert "classes_appeared" in watch
    assert "ADR-013" in watch, "the second watch on this premise must be named"
    assert "CI" in watch, "and so must the fact that it does not run there"


def test_the_named_watches_resolve_to_real_tests(svc):
    """The watch strings are addresses, not prose: every test path in them exists."""
    import re

    root = os.path.join(os.path.dirname(__file__), "..")
    for name, c in _clauses(svc).items():
        for path in re.findall(r"tests/[\w/]+\.py", c.get("premise-watched-by", "")):
            assert os.path.isfile(os.path.join(root, path)), (
                f"{name} names {path}, which is not there"
            )


def test_the_bases_are_what_the_measurement_table_decided(svc):
    bases = {n: c["basis"] for n, c in _clauses(svc).items()}
    assert bases == {
        "sot-inversion": "machinery",
        "substrate-v1-v6": "machinery",
        "adapt-per-tz": "measured",
        "spec-types-closed-list": "measured",
        "tc-pos-neg-pairing": "vacuous",
        "quality-gates-closed-list": "declared",
        "closed-lists-backward-findings": "measured",
        # v1.1, session #250: no BR class, no level column (renar_br_premise)
        "implements-edge-subsystem": "vacuous",
    }


def test_every_measured_verdict_has_a_reachable_red_branch(svc):
    """NEGATIVE SCENARIO, the property the whole task is about: a `measured`
    basis is a promise that SOME state turns the clause false. Each of the
    three is driven red here through the real generator, not the sub-module."""
    conn = svc.be._conn
    # spec types: a CHECK admitting a local type
    ddl = conn.execute("SELECT sql FROM sqlite_master WHERE name='specs'").fetchone()[0]
    conn.execute("DROP TABLE specs")
    conn.execute(ddl.replace("'DOC'", "'DOC', 'FOO'"))
    # closed lists: an eighth category
    ddl = conn.execute("SELECT sql FROM sqlite_master WHERE name='adapt_findings'").fetchone()[0]
    conn.execute("DROP TABLE adapt_findings")
    conn.execute(ddl.replace("'scope'", "'scope', 'vibes'"))
    conn.commit()
    clauses = _clauses(svc)
    assert clauses["spec-types-closed-list"]["confirmed"] is False
    assert clauses["closed-lists-backward-findings"]["confirmed"] is False
    assert clauses["adapt-per-tz"]["confirmed"] is False, "empty store: §13.3.3 red as before"


# --- §13.3.6 over the declaration ------------------------------------------------


def test_the_published_declaration_satisfies_the_clause():
    verdict = quality_gates_clause(QUALITY_GATES_DECLARED)
    assert verdict["confirmed"] is True, verdict
    assert set(QUALITY_GATES_DECLARED) == set(CLOSED_GATE_IDS)


@pytest.mark.parametrize(
    "mutation,failed",
    [
        ({"qg-5": "required"}, ["gate-ids-closed"]),
        ({"qg-0": "declared"}, ["core-gates-required"]),
        ({"qg-2": "absent"}, ["core-gates-required"]),
        ({"qg-3": "maybe"}, ["optional-gate-states-admitted"]),
    ],
    ids=["sixth-gate-id", "qg0-not-required", "qg2-absent", "optional-in-unknown-state"],
)
def test_a_declaration_the_standard_does_not_admit_reds_and_names_the_half(mutation, failed):
    """NEGATIVE SCENARIO from the measurement table: qg-5 and qg-0=absent left the
    old constant green; now each shape reddens the sub-check that owns it."""
    declared = {**QUALITY_GATES_DECLARED, **mutation}
    verdict = quality_gates_clause(declared)
    assert verdict["confirmed"] is False
    assert [s["check"] for s in verdict["subchecks"] if not s["ok"]] == failed


def test_a_missing_gate_id_reds():
    declared = {k: v for k, v in QUALITY_GATES_DECLARED.items() if k != "qg-4"}
    verdict = quality_gates_clause(declared)
    assert verdict["confirmed"] is False
    assert "qg-4" in verdict["subchecks"][0]["evidence"]


def test_the_manifest_publishes_the_same_declaration_the_clause_judges(svc):
    """One source: the block in the manifest IS the dict the clause read."""
    manifest, _ = renar_conformance.generate(svc.be._conn, "a", "2026-09-05")
    assert manifest["quality-gates"] == QUALITY_GATES_DECLARED
    assert (
        manifest["assessment-evidence"]["clause-13-3-6"]
        == (quality_gates_clause(QUALITY_GATES_DECLARED)["subchecks"])
    )


# --- the artifact ------------------------------------------------------------------


def test_the_generated_manifest_carries_a_basis_per_clause(svc):
    manifest, text = renar_conformance.generate(svc.be._conn, "a", "2026-09-05")
    section = manifest["mandatory-clauses-basis"]
    assert set(section) - {"disclaimer"} == set(manifest["mandatory-clauses-confirmed"])
    assert section["tc-pos-neg-pairing"]["basis"] == "vacuous"
    assert "classes_appeared" in section["tc-pos-neg-pairing"]["premise-watched-by"]
    assert "basis" not in section["adapt-per-tz"].get("premise-watched-by", "")
    assert basis_header_lines() in text, "the header must point the reader at the block"
    assert "mandatory-clauses-basis" in section["disclaimer"] or "RESTS ON" in section["disclaimer"]


def test_basis_section_is_a_pure_projection_of_the_clauses():
    clauses = {
        "a": {"confirmed": True, "evidence": "-", "basis": "measured"},
        "b": {"confirmed": True, "evidence": "-", "basis": "vacuous", "premise-watched-by": "x"},
    }
    section = basis_section(clauses)
    assert section["a"] == {"basis": "measured"}
    assert section["b"] == {"basis": "vacuous", "premise-watched-by": "x"}


def test_the_committed_manifest_carries_the_basis_block():
    """The live artifact, not the generator: the block reached the file."""
    yaml = pytest.importorskip("yaml")
    if not os.path.isfile(MANIFEST):
        pytest.skip("no manifest in this tree")
    with open(MANIFEST, encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)
    section = manifest["mandatory-clauses-basis"]
    assert set(section) - {"disclaimer"} == set(manifest["mandatory-clauses-confirmed"])
    for name, entry in section.items():
        if name == "disclaimer":
            continue
        assert entry["basis"] in BASIS_KINDS


# --- the machinery ratchet -----------------------------------------------------------


def test_the_machinery_sot_inversion_rests_on_is_switched_on():
    """§13.3.1 is `machinery`: task before code, verify before close. This is the
    watch the artifact names for it. It reads the SOURCE the deployment is
    generated from and the LIVE gate registry, so a switched-off gate or an
    unwired hook reddens here rather than leaving the constant standing."""
    from bootstrap_hooks import build_hooks_dict
    from gate_degeneracy import blocking_gates

    gates = blocking_gates()
    assert "verify_first" in gates, "verify-first is not a blocking gate in the live registry"
    assert gates["verify_first"].get("enabled"), "verify-first is switched off"

    hooks = build_hooks_dict(lambda script, suffix="": f"python /x/{script}{suffix}")
    wired = [
        h["matcher"]
        for h in hooks["PreToolUse"]
        if any("task_gate.py" in hook["command"] for hook in h["hooks"])
    ]
    assert wired, "task_gate.py is not wired as a PreToolUse hook"
    assert any("Write" in m and "Edit" in m for m in wired), (
        f"task_gate.py is wired, but not on the write tools: {wired}"
    )


def test_the_ratchet_is_not_a_tautology(monkeypatch):
    """NEGATIVE: deprive the registry of verify-first and the watch must red."""
    import gate_degeneracy

    live = gate_degeneracy.blocking_gates()
    without = {n: c for n, c in live.items() if n != "verify_first"}
    monkeypatch.setattr(gate_degeneracy, "blocking_gates", lambda gates=None: without)
    with pytest.raises(AssertionError, match="not a blocking gate"):
        test_the_machinery_sot_inversion_rests_on_is_switched_on()
