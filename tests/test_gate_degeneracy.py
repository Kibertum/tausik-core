"""The degeneracy measure for our own blocking gates.

The task that opened this file carries a criterion most test files do not: the
check introduced here is FORBIDDEN from becoming the defect it was written
against. A check that answers "yes, every gate has a measure" on every input is
exactly the tautology the three findings of session #191 were instances of, and
accepting it would be the task failing rather than passing.

So the live assertion is one test among many, and the rest are the negative
half: each deprives the measure of something and requires it to go red AND to
NAME the gate. `test_the_measure_is_not_a_tautology` states that requirement
directly rather than leaving it implied by the others.
"""

from __future__ import annotations

import os

import pytest

from gate_degeneracy import Debt, audit, blocking_gates, declared_red_proofs, node_resolves

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _kinds(result) -> set[str]:
    return {d.kind for d in result.debts}


def _named(result, kind: str) -> set[str]:
    return {d.gate for d in result.debts if d.kind == kind}


# --- AC1: the live state of this repository ---------------------------------


def test_every_blocking_gate_in_force_has_a_resolving_red_proof():
    """The load-bearing assertion, and the one that must never be the ONLY one."""
    result = audit()
    assert result.ok, result.report()
    assert result.proven, "no gate was judged proven — the measure examined nothing"


def test_the_registry_covers_the_live_gate_table_not_a_frozen_copy():
    """A hardcoded gate list is the shape this measure exists to prevent: it goes
    on reporting 'all proven' for gates added after it was written. The proofs
    are keyed off `load_gates`, so adding a blocking gate must break this."""
    in_force = {n for n, c in blocking_gates().items() if c.get("enabled")}
    assert in_force, "the live registry reported no blocking gate in force"
    assert in_force <= set(declared_red_proofs()), (
        "a blocking gate is in force with no red_proofs entry: "
        f"{sorted(in_force - set(declared_red_proofs()))}"
    )


@pytest.mark.parametrize("gate,entry", sorted(declared_red_proofs().items()))
def test_each_declared_proof_names_both_a_test_and_the_violation_it_feeds(gate, entry):
    """ "Covered by tests" is not an answer. The entry has to say what violation is
    handed to the gate, because that sentence is what a reader checks the test
    against."""
    assert entry.get("test"), f"{gate}: no test node"
    assert entry.get("violation"), f"{gate}: no violation described"
    resolved, why = node_resolves(entry["test"], REPO_ROOT)
    assert resolved, f"{gate}: {why}"


# --- AC4: the measure must be able to say NO, and name the gate -------------


def test_the_measure_is_not_a_tautology():
    """Stated as its own requirement, not left implied. A measure that cannot be
    made to fail measures nothing, so this asserts the existence of at least one
    input on which it refuses — and that the refusal carries the gate's name."""
    proofs = dict(declared_red_proofs())
    victim = sorted(n for n, c in blocking_gates().items() if c.get("enabled"))[0]
    proofs.pop(victim)
    result = audit(proofs=proofs)
    assert not result.ok
    assert victim in _named(result, "NO_PROOF"), result.report()


def test_removing_one_gates_proof_reds_and_names_that_gate_only():
    proofs = dict(declared_red_proofs())
    proofs.pop("verify_first")
    result = audit(proofs=proofs)
    assert _named(result, "NO_PROOF") == {"verify_first"}
    assert "verify_first" in result.report()
    assert "verify_first" not in result.proven


def test_an_entry_with_no_test_node_is_not_a_proof():
    proofs = dict(declared_red_proofs())
    proofs["changelog"] = {"violation": "described but never demonstrated"}
    result = audit(proofs=proofs)
    assert _named(result, "NO_PROOF") == {"changelog"}


@pytest.mark.parametrize(
    "node,because",
    [
        pytest.param("tests/test_does_not_exist.py::test_x", "no such test file", id="file"),
        pytest.param(
            "tests/test_gate_degeneracy.py::test_never_written",
            "no function named",
            id="function_never_existed",
        ),
        pytest.param(
            "tests/test_gate_degeneracy.py::NoSuchClass::test_x",
            "no class named",
            id="class_never_existed",
        ),
        pytest.param("tests/test_gate_degeneracy.py", "malformed node id", id="not_a_node_id"),
    ],
)
def test_a_citation_that_resolves_to_nothing_is_refused_with_the_reason(node, because):
    """The teeth. Without resolution the registry would be a list of strings
    anyone could satisfy by typing one — and the session #196 audit already
    counted that cost: 19 rotted and 25 never-existent test citations across 1258
    closed tasks (memory #463)."""
    proofs = dict(declared_red_proofs())
    proofs["filesize"] = {"test": node, "violation": "irrelevant"}
    result = audit(proofs=proofs)
    assert _named(result, "UNRESOLVABLE_PROOF") == {"filesize"}
    assert because in result.report()


def test_a_parametrised_node_id_still_resolves():
    """Ids like `file::test_x[case]` are ordinary citations; rejecting them would
    push authors toward a less precise reference."""
    ok, why = node_resolves(
        "tests/test_gate_degeneracy.py::test_a_parametrised_node_id_still_resolves[case]",
        REPO_ROOT,
    )
    assert ok, why


# --- AC2: declared blocking and switched OFF, reported first ----------------


def test_a_universal_blocking_gate_that_is_off_is_reported_first_and_named():
    """`bootstrap_drift` stood exactly here when this task was opened. The state
    is worse than degeneracy and is ordered ahead of everything else for that
    reason."""
    gates = {n: dict(c) for n, c in blocking_gates().items()}
    gates["memory_route"]["enabled"] = False
    result = audit(gates=gates)
    assert not result.ok
    assert result.debts[0].kind == "DISABLED", result.report()
    assert result.debts[0].gate == "memory_route"
    assert "worse than degeneracy" in result.debts[0].detail.lower()


def test_the_disabled_row_says_why_it_is_worse_than_a_degenerate_one():
    """The distinction has to travel with the finding, not live only in a
    docstring: a degenerate gate still executes and still occupies a line in the
    receipt, so a reader can catch it. A gate that is off emits nothing, and
    nothing is indistinguishable from 'ran and found no problem'."""
    gates = {n: dict(c) for n, c in blocking_gates().items()}
    gates["changelog"]["enabled"] = False
    detail = audit(gates=gates).debts[0].detail
    assert "no row" in detail.lower()
    assert "found nothing" in detail.lower()


def test_a_dormant_stack_gate_is_scoping_not_silence():
    """`tsc` is off because this project is not TypeScript. Reporting that as
    debt would flood the measure with noise and teach people to ignore it — the
    failure mode that kills a check more reliably than a bug."""
    result = audit()
    assert "tsc" in result.dormant
    assert "tsc" not in {d.gate for d in result.debts}


def test_a_stack_gate_that_is_in_force_is_not_exempt():
    """Dormancy is about being OFF, not about being stack-scoped. `pytest` is a
    stack gate and it runs here, so it owes a proof like everything else."""
    assert "pytest" in audit().proven


# --- Stale entries ----------------------------------------------------------


def test_an_entry_for_a_gate_the_registry_no_longer_blocks_on_is_reported():
    """A rename or a downgrade to `warn` leaves evidence behind. Silence here
    would let the registry describe a world that no longer exists."""
    proofs = dict(declared_red_proofs())
    proofs["gate_that_was_removed"] = {
        "test": "tests/test_gate_degeneracy.py::test_x",
        "violation": "x",
    }
    result = audit(proofs=proofs)
    assert _named(result, "STALE_ENTRY") == {"gate_that_was_removed"}


def test_an_empty_registry_reports_every_gate_rather_than_going_quiet():
    """Direction of degradation. A measure of this kind must never degrade toward
    'everything is fine' — an unreadable registry has to be loud."""
    result = audit(proofs={})
    assert not result.ok
    in_force = {n for n, c in blocking_gates().items() if c.get("enabled")}
    assert _named(result, "NO_PROOF") == in_force


def test_debt_describes_itself_with_kind_gate_and_detail():
    d = Debt("x", "NO_PROOF", "why")
    assert d.describe() == "NO_PROOF x: why"
