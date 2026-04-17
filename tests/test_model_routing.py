"""Test model routing suggestion."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from model_routing import format_suggestion, suggest_model


def test_simple_maps_to_haiku():
    r = suggest_model("simple")
    assert "haiku" in r["model"].lower()
    assert "Haiku" in r["display"]


def test_medium_maps_to_sonnet():
    r = suggest_model("medium")
    assert "sonnet" in r["model"].lower()


def test_complex_maps_to_opus():
    r = suggest_model("complex")
    assert "opus" in r["model"].lower()


def test_none_defaults_to_sonnet_with_hint():
    r = suggest_model(None)
    assert "sonnet" in r["model"].lower()
    assert (
        "not specified" in r["rationale"].lower()
        or "not set" in r["rationale"].lower()
        or "defaulting" in r["rationale"].lower()
    )


def test_unknown_falls_back_with_warning():
    r = suggest_model("gigantic")
    assert "sonnet" in r["model"].lower()
    assert "unknown" in r["rationale"].lower()


def test_case_insensitive():
    r = suggest_model("SIMPLE")
    assert "haiku" in r["model"].lower()


def test_whitespace_tolerated():
    r = suggest_model("  medium  ")
    assert "sonnet" in r["model"].lower()


def test_format_suggestion_is_one_line():
    s = format_suggestion("simple")
    assert "\n" not in s
    assert "Haiku" in s


def test_return_dict_has_stable_keys():
    r = suggest_model("simple")
    assert set(r.keys()) == {"model", "display", "rationale"}
