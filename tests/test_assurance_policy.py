"""Behavioral contract for residual-assurance routing inputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from assurance_policy import (  # noqa: E402
    compose_declarations,
    evaluate_assurance,
    observed_capabilities,
    validate_impact,
)
from stack_registry import StackRegistry  # noqa: E402


LOW = {"level": "low", "blast_radius": "local", "reversibility": "reversible"}


@pytest.mark.parametrize(
    ("field", "value"),
    [("level", []), ("blast_radius", {}), ("reversibility", 1), ("data_change", True)],
)
def test_non_string_impact_enums_return_validation_errors(field, value):
    errors = validate_impact({field: value})
    assert len(errors) == 1
    assert errors[0].startswith(f"assurance_impact.{field} must be one of ")


def test_complete_low_declarative_evidence_selects_l1():
    result = evaluate_assurance(
        profiles=["declarative"],
        impact=LOW,
        observed_evidence=["behavior", "idempotence", "rollback", "postconditions"],
    )
    assert result["depth"] == "L1"
    assert result["residual_gaps"] == []


def test_syntax_and_schema_do_not_prove_declarative_behavior():
    observed = observed_capabilities(
        {
            "lint": ["syntax"],
            "validate": ["schema"],
            "not-run": ["behavior", "idempotence", "rollback", "postconditions"],
        },
        [
            {"name": "lint", "passed": True},
            {"name": "validate", "passed": True},
            {"name": "not-run", "passed": False},
        ],
    )
    result = evaluate_assurance(profiles=["declarative"], impact=LOW, observed_evidence=observed)
    assert observed == ["schema", "syntax"]
    assert result["depth"] == "L2"
    assert result["residual_gaps"] == [
        "behavior",
        "idempotence",
        "postconditions",
        "rollback",
    ]


@pytest.mark.parametrize(
    ("impact", "reason"),
    [
        ({"security_boundary": True}, "security boundary"),
        ({"governance_boundary": True}, "governance boundary"),
        ({"privileged": True}, "privileged state change"),
        ({"owner_escalation": True}, "owner escalation"),
        ({"reversibility": "irreversible"}, "irreversible state change"),
        ({"data_change": "destructive"}, "destructive data migration"),
    ],
)
def test_non_downgradable_l3_floors(impact, reason):
    result = evaluate_assurance(
        profiles=["declarative"],
        impact={**LOW, **impact},
        observed_evidence=["behavior", "idempotence", "rollback", "postconditions"],
    )
    assert result["depth"] == result["hard_floor"] == "L3"
    assert reason in result["reasons"][0]


@pytest.mark.parametrize(
    ("profiles", "impact"),
    [([], LOW), (["declarative"], {}), (None, None)],
)
def test_missing_declarations_fall_back_to_l2(profiles, impact):
    composed, merged, complete = compose_declarations([], profiles, {}, impact)
    result = evaluate_assurance(
        profiles=composed,
        impact=merged,
        observed_evidence=[],
        metadata_complete=complete,
    )
    assert result["depth"] == "L2"
    assert result["hard_floor"] is None


def test_custom_puppet_declaration_uses_the_same_policy_as_builtin_terraform(tmp_path):
    custom = tmp_path / "user" / "puppetish"
    custom.mkdir(parents=True)
    (custom / "stack.json").write_text(
        json.dumps(
            {
                "name": "puppetish",
                "assurance_profiles": ["declarative"],
                "gates": {"manifest-check": {"evidence_capabilities": ["syntax", "schema"]}},
            }
        ),
        encoding="utf-8",
    )
    registry = StackRegistry()
    registry.load_builtin(_ROOT / "stacks")
    registry.load_user(tmp_path / "user")
    terraform = registry.assurance_for("terraform")
    puppet = registry.assurance_for("puppetish")

    def decision(declaration):
        profiles, impact, complete = compose_declarations(
            declaration["profiles"], [], declaration["impact"], LOW
        )
        return evaluate_assurance(
            profiles=profiles,
            impact=impact,
            observed_evidence=["syntax", "schema"],
            metadata_complete=complete,
        )

    assert decision(terraform) == decision(puppet)
