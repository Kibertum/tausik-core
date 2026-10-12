"""Every gate declares WHICH CHANGE does not happen while its verdict is negative.

SENAR 1.4 §8.6(a), SHALL on every configuration including Core: without it, a
claim of conformance to section 8 is invalid under §13.4. Our registry had
`description` — "Lint with ruff before commit" — which describes the MECHANISM,
not the effect. The two are not the same statement, and only one of them can be
checked against a proposed action.

WHAT THIS MODULE CAN AND CANNOT DO, said plainly because §13.7 says it plainly:
the applicability test for (a) needs a reader. A test can pin PRESENCE,
non-emptiness and the absence of the stock phrases the standard names; whether a
particular sentence actually answers "which change does not happen" is a review
question. Passing the first off as the second would be the same move this field
exists to end — so the mechanical half is asserted here and the human half is
named, not simulated.
"""

from __future__ import annotations

import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from gate_registry import GATE_REGISTRY  # noqa: E402
from gate_spec import PHASE_SCOPED, GateSpec  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/gate_registry_scoped.py", "scripts/gate_registry.py"]

#: The phrases §8.6(a) refuses by name, plus their obvious siblings. Each is
#: rejected for one reason: no proposed action can be checked against it. A
#: declaration that survives this list may still be empty of meaning — that is
#: what review is for — but these are the ones the standard settles in advance.
STOCK_PHRASES = (
    "ensures quality",
    "ensure quality",
    "checks correctness",
    "check correctness",
    "improves quality",
    "обеспечивает качество",
    "проверяет корректность",
)

#: A declaration shorter than this cannot name a change and its consequence. The
#: bound is deliberately generous: it exists to catch a placeholder, not to
#: enforce a house style.
MIN_LENGTH = 40


@pytest.mark.parametrize("name", sorted(GATE_REGISTRY))
def test_every_gate_declares_the_effect_it_prevents(name):
    """AC2: every gate in the registry, not the exemplary ones."""
    prevents = GATE_REGISTRY[name].prevents.strip()
    assert prevents, (
        f"gate '{name}' declares no prevented effect. §8.6(a) asks which change "
        "does NOT happen while the verdict is negative; `description` answers a "
        "different question (what the gate looks at)."
    )
    assert len(prevents) >= MIN_LENGTH, (
        f"gate '{name}' declares {len(prevents)} characters — too short to name "
        f"a change: {prevents!r}"
    )


@pytest.mark.parametrize("name", sorted(GATE_REGISTRY))
def test_no_gate_hides_behind_a_stock_phrase(name):
    """AC5: the formulations the standard refuses by name."""
    spec = GATE_REGISTRY[name]
    prevents = spec.prevents.strip().lower()
    hit = [p for p in STOCK_PHRASES if p in prevents]
    assert not hit, (
        f"gate '{name}' declares {hit} — a phrase no proposed action can be "
        "checked against, which is why §8.6(a) names it as not an effect"
    )
    assert prevents != name.lower(), f"gate '{name}' restates its own name"
    description = str(spec.default_config.get("description", "")).strip().lower()
    assert prevents != description, (
        f"gate '{name}' repeats its description — the mechanism, not the effect"
    )


def test_a_new_gate_without_a_declaration_is_caught():
    """AC4 NEGATIVE: the guard must redden on a gate that arrives without one.

    Driven on a GateSpec built here rather than by editing the registry: the
    subject is the RULE, and a rule that can only be exercised by breaking the
    real registry is a rule nobody will exercise.
    """
    undeclared = GateSpec(name="brand_new", phase=PHASE_SCOPED, default_config={}, impl="x:y")
    assert not undeclared.prevents.strip()
    with pytest.raises(AssertionError):
        _assert_declared(undeclared)


def test_a_stock_phrase_is_caught():
    """AC5 NEGATIVE, driven rather than assumed."""
    stock = GateSpec(
        name="brand_new",
        phase=PHASE_SCOPED,
        default_config={},
        impl="x:y",
        prevents="This gate ensures quality across the whole repository.",
    )
    with pytest.raises(AssertionError):
        _assert_no_stock_phrase(stock)


def _assert_declared(spec: GateSpec) -> None:
    assert spec.prevents.strip(), f"gate '{spec.name}' declares no prevented effect"


def _assert_no_stock_phrase(spec: GateSpec) -> None:
    lowered = spec.prevents.strip().lower()
    assert not [p for p in STOCK_PHRASES if p in lowered], (
        f"gate '{spec.name}' hides behind a stock phrase"
    )


class TestTheEffectReachesTheRecord:
    """AC6: §8.6(g) — the record must identify what the verdict held back."""

    @staticmethod
    def _conn():
        sys.path.insert(0, os.path.join(_ROOT, "tests"))
        from conftest import canonical_schema_db

        return canonical_schema_db()

    def test_the_column_exists_in_a_fresh_install(self):
        conn = self._conn()
        columns = {row[1] for row in conn.execute("PRAGMA table_info(gate_runs)")}
        assert "prevents" in columns, (
            "gate_runs carries no `prevents` column, so a recorded verdict "
            "cannot say what it prevented"
        )

    def test_a_recorded_run_carries_the_registry_declaration(self):
        from gate_run_record import record_gate_runs

        conn = self._conn()
        record_gate_runs(
            conn,
            verification_run_id=None,
            task_slug="t",
            trigger="commit",
            gate_results=[{"name": "filesize", "passed": True}],
        )
        stored = conn.execute("SELECT prevents FROM gate_runs").fetchone()[0]
        assert stored == GATE_REGISTRY["filesize"].prevents.strip()

    def test_an_unknown_gate_records_no_invented_effect(self):
        """A project's own command gate has no declaration; NULL, never a guess."""
        from gate_run_record import record_gate_runs

        conn = self._conn()
        record_gate_runs(
            conn,
            verification_run_id=None,
            task_slug="t",
            trigger="commit",
            gate_results=[{"name": "somebody-elses-gate", "passed": True}],
        )
        assert conn.execute("SELECT prevents FROM gate_runs").fetchone()[0] is None

    def test_the_row_keeps_the_wording_the_caller_carried(self):
        """A declaration edited later must not rewrite an old audit row."""
        from gate_run_record import record_gate_runs

        conn = self._conn()
        record_gate_runs(
            conn,
            verification_run_id=None,
            task_slug="t",
            trigger="commit",
            gate_results=[{"name": "filesize", "passed": True, "prevents": "as it read that day"}],
        )
        assert conn.execute("SELECT prevents FROM gate_runs").fetchone()[0] == "as it read that day"
