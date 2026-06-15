"""Test model routing suggestion — phase x complexity matrix (v15mr-phase-matrix)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from model_routing import VALID_PHASES, format_suggestion, suggest_model


# --- Back-compat: single-arg call defaults to phase=implement -----------------


def test_default_phase_is_implement():
    # No phase arg must equal an explicit implement phase (AC2).
    assert suggest_model("medium") == suggest_model("medium", "implement")


def test_implement_simple_maps_to_sonnet():
    # Deliberate v1.5 change (Decision #112): implement floor is Sonnet, not Haiku.
    r = suggest_model("simple")
    assert "sonnet" in r["model"].lower()
    assert "Sonnet" in r["display"]


@pytest.mark.parametrize(
    "complexity,expected_model",
    [
        pytest.param("simple", "sonnet", id="implement_simple_sonnet"),
        pytest.param("medium", "sonnet", id="implement_medium_sonnet"),
        pytest.param("complex", "opus", id="implement_complex_opus"),
        pytest.param("SIMPLE", "sonnet", id="case_insensitive"),
        pytest.param("  medium  ", "sonnet", id="whitespace_tolerated"),
    ],
)
def test_implement_mapping(complexity, expected_model):
    r = suggest_model(complexity)
    assert expected_model in r["model"].lower()


# --- AC1: matrix cells match the ТЗ ------------------------------------------


@pytest.mark.parametrize(
    "phase,complexity,expected_model",
    [
        # planning: complexity-independent -> fable
        pytest.param("planning", "simple", "fable", id="planning_simple_fable"),
        pytest.param("planning", "medium", "fable", id="planning_medium_fable"),
        pytest.param("planning", "complex", "fable", id="planning_complex_fable"),
        # implement
        pytest.param("implement", "simple", "sonnet", id="implement_simple"),
        pytest.param("implement", "complex", "opus", id="implement_complex"),
        # research: simple=haiku (its new home), deep=sonnet
        pytest.param("research", "simple", "haiku", id="research_simple_haiku"),
        pytest.param("research", "medium", "sonnet", id="research_medium_sonnet"),
        pytest.param("research", "complex", "sonnet", id="research_complex_sonnet"),
    ],
)
def test_matrix_cells(phase, complexity, expected_model):
    r = suggest_model(complexity, phase)
    assert expected_model in r["model"].lower()


def test_phase_is_case_insensitive():
    assert suggest_model("simple", "RESEARCH") == suggest_model("simple", "research")


# --- AC3: negative — unknown phase raises with the valid list -----------------


def test_unknown_phase_raises_valueerror():
    with pytest.raises(ValueError) as exc:
        suggest_model("medium", "deployment")
    msg = str(exc.value)
    for ph in VALID_PHASES:
        assert ph in msg


# --- Complexity fallbacks (preserved behaviour) ------------------------------


def test_none_defaults_to_medium_with_hint():
    r = suggest_model(None)  # implement/medium -> sonnet
    assert "sonnet" in r["model"].lower()
    assert (
        "not specified" in r["rationale"].lower()
        or "not set" in r["rationale"].lower()
        or "defaulting" in r["rationale"].lower()
    )


def test_unknown_complexity_falls_back_with_warning():
    r = suggest_model("gigantic")  # implement/medium -> sonnet
    assert "sonnet" in r["model"].lower()
    assert "unknown" in r["rationale"].lower()


def test_none_complexity_in_research_phase():
    r = suggest_model(None, "research")  # research/medium -> sonnet
    assert "sonnet" in r["model"].lower()


# --- AC4: config override ----------------------------------------------------


def test_config_override_per_tier():
    cfg = {"model_routing": {"implement": {"complex": "claude-fable-5"}}}
    r = suggest_model("complex", "implement", config=cfg)
    assert r["model"] == "claude-fable-5"
    assert "Fable" in r["display"]
    assert "override" in r["rationale"].lower()


def test_config_override_whole_phase_string():
    cfg = {"model_routing": {"planning": "claude-opus-4-8"}}
    r = suggest_model("simple", "planning", config=cfg)
    assert r["model"] == "claude-opus-4-8"
    assert "Opus" in r["display"]


def test_config_override_unknown_model_id_used_as_display():
    cfg = {"model_routing": {"implement": {"medium": "gpt-some-overlay"}}}
    r = suggest_model("medium", "implement", config=cfg)
    assert r["model"] == "gpt-some-overlay"
    assert r["display"] == "gpt-some-overlay"  # unknown family -> id verbatim


def test_malformed_override_ignored_base_matrix_wins():
    for bad in ({"model_routing": "nope"}, {"model_routing": {"implement": 123}}, {}):
        r = suggest_model("complex", "implement", config=bad)
        assert "opus" in r["model"].lower()  # base matrix cell, no raise


def test_no_config_means_no_override():
    # config=None must NOT auto-load / apply any override (pure call).
    r = suggest_model("complex", "implement")
    assert "opus" in r["model"].lower()


# --- format_suggestion -------------------------------------------------------


def test_format_suggestion_is_one_line():
    # config={} keeps the test hermetic — no read of the real .tausik/config.json (H1).
    s = format_suggestion("simple", config={})
    assert "\n" not in s
    assert "Sonnet" in s


def test_format_suggestion_honours_phase_and_config():
    s = format_suggestion("simple", "research", config={"model_routing": {}})
    assert "Haiku" in s


def test_return_dict_has_stable_keys():
    r = suggest_model("simple")
    assert set(r.keys()) == {"model", "display", "rationale"}


# --- Review-fix guards (v15mr-review-fixes, Decision #112 follow-up) ----------


def test_multi_token_model_id_is_ambiguous_none():
    from model_routing import _model_family

    # >1 family token -> ambiguous -> None (M1), never a silent first-match guess.
    assert _model_family("claude-sonnet-opus-x") is None
    assert _model_family("claude-opus-4-8") == "opus"  # single token still resolves


def test_override_future_pointrelease_keeps_honest_display():
    # H2: a same-family but unregistered version must show its own id, not lie.
    cfg = {"model_routing": {"implement": {"complex": "claude-opus-4-9"}}}
    r = suggest_model("complex", "implement", config=cfg)
    assert r["model"] == "claude-opus-4-9"
    assert r["display"] == "claude-opus-4-9"
    assert r["display"] != "Opus 4.8"


def test_valid_phases_derived_from_matrix():
    # M2: VALID_PHASES is the matrix's own keys (single source of truth).
    assert set(VALID_PHASES) == {"planning", "implement", "research"}
