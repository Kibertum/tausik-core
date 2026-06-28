"""Tests for model_profiles — vendor families × capability ranks as DATA (Decision #119)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import model_profiles as mp  # noqa: E402


def test_defaults_present():
    fams = mp.load_families(None)
    assert "claude" in fams and "glm" in fams
    assert fams["claude"]["opus"]["model"] == "claude-opus-4-8"
    assert fams["glm"]["haiku"]["model"] == "glm-4.5-air"


def test_load_families_non_dict_returns_defaults():
    assert list(mp.load_families("not-a-dict").keys()) == ["claude", "glm"]
    assert list(mp.load_families(None).keys()) == ["claude", "glm"]


def test_load_families_merges_and_extends():
    cfg = {
        "model_profiles": {
            "families": {
                "glm": {"opus": {"model": "glm-5.2", "display": "GLM-5.2"}},
                "qwen": {"sonnet": {"model": "qwen-3-coder"}},  # display defaults to model
            }
        }
    }
    fams = mp.load_families(cfg)
    assert fams["glm"]["opus"]["model"] == "glm-5.2"
    assert fams["glm"]["haiku"]["model"] == "glm-4.5-air"  # untouched default preserved
    assert fams["qwen"]["sonnet"] == {"model": "qwen-3-coder", "display": "qwen-3-coder"}


def test_load_families_skips_malformed_entries():
    cfg = {
        "model_profiles": {
            "families": {
                "glm": {
                    "opus": {"model": ""},  # empty model → dropped
                    "bogus_rank": {"model": "x"},  # unknown rank → dropped
                    "sonnet": "not-a-dict",  # → dropped
                }
            }
        }
    }
    fams = mp.load_families(cfg)
    # opus stays at the default since the override was invalid.
    assert fams["glm"]["opus"]["model"] == "glm-4.6"


def test_vendor_of():
    fams = mp.load_families(None)
    assert mp.vendor_of("glm-4.6", fams) == "glm"
    assert mp.vendor_of("claude-opus-4-8", fams) == "claude"
    assert mp.vendor_of("claude-opus-4-9-future", fams) == "claude"  # token fallback
    assert mp.vendor_of(None, fams) is None
    assert mp.vendor_of("totally-unknown-xyz", fams) is None


def test_rank_of_highest_wins():
    fams = mp.load_families(None)
    # glm-4.6 fills sonnet+opus+fable → highest (fable) wins.
    assert mp.rank_of("glm-4.6", fams) == "fable"
    assert mp.rank_of("glm-4.5-air", fams) == "haiku"
    assert mp.rank_of("", fams) is None
    assert mp.rank_of("unknown", fams) is None


def test_spec_for_fallback_to_claude():
    fams = mp.load_families(None)
    assert mp.spec_for("glm", "opus", fams)["model"] == "glm-4.6"
    # A family missing a rank falls back to claude's spec for that rank.
    fams2 = {"claude": fams["claude"], "partial": {"haiku": {"model": "p-lite", "display": "P"}}}
    assert mp.spec_for("partial", "opus", fams2)["model"] == "claude-opus-4-8"
    # Unknown family → claude.
    assert mp.spec_for("nonexistent", "sonnet", fams)["model"] == "claude-sonnet-4-6"


def test_default_family():
    assert mp.default_family({"model_profiles": {"default_family": "glm"}}) == "glm"
    assert mp.default_family({"model_profiles": {}}) is None
    assert mp.default_family(None) is None
