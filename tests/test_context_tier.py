"""v14-bootstrap-context-tier: context_tier drives bootstrap body size."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from project_config import resolve_context_tier

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "bootstrap"))


def test_resolve_context_tier_defaults():
    assert resolve_context_tier({}) == "standard"
    assert resolve_context_tier({"context_tier": None}) == "standard"


def test_resolve_context_tier_accepts_aliases_case():
    assert resolve_context_tier({"context_tier": "MINIMAL"}) == "minimal"


def test_resolve_context_tier_rejects_unknown():
    with pytest.raises(ValueError, match="Invalid context_tier"):
        resolve_context_tier({"context_tier": "xl"})


def test_minimal_body_omits_skills_section():
    from bootstrap_templates import build_full_body

    std = build_full_body(
        "p", ["python"], "agent", ".claude", ide=None, context_tier="standard"
    )
    small = build_full_body(
        "p", ["python"], "agent", ".claude", ide=None, context_tier="minimal"
    )
    assert "## Skills" in std
    assert "## Skills" not in small
    assert "Rule pack size" in small


def test_full_tier_inserts_deep_section():
    from bootstrap_templates import build_full_body

    std = build_full_body(
        "p", [], "agent", ".claude", ide=None, context_tier="standard"
    )
    full = build_full_body(
        "p", [], "agent", ".claude", ide=None, context_tier="full"
    )
    assert "Deep onboarding" not in std
    assert "Deep onboarding" in full


def test_invalid_tier_string_falls_back_in_build_full_body():
    from bootstrap_templates import build_full_body

    std = build_full_body(
        "p",
        [],
        "agent",
        ".claude",
        ide=None,
        context_tier="not-a-real-tier-should-act-like-standard",
    )
    assert "## Skills" in std
