"""Tests for model_profiles — vendor families x capability ranks as DATA (Decision #119)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pytest

import model_profiles as mp


def test_defaults_present():
    fams = mp.load_families(None)
    assert "claude" in fams and "glm" in fams
    assert fams["claude"]["opus"]["model"] == "claude-opus-4-8"
    assert fams["glm"]["haiku"]["model"] == "glm-4.5-air"
    # model-profiles-glm47-local: the strong GLM ranks ship the current flagship.
    assert fams["glm"]["sonnet"]["model"] == "glm-4.7"
    assert fams["glm"]["opus"]["model"] == "glm-4.7"
    assert fams["glm"]["fable"]["model"] == "glm-4.7"


def test_load_families_non_dict_returns_defaults():
    assert list(mp.load_families("not-a-dict").keys()) == ["claude", "glm", "openai"]
    assert list(mp.load_families(None).keys()) == ["claude", "glm", "openai"]


def test_load_families_merges_and_extends():
    cfg = {
        "model_profiles": {
            "families": {
                "glm": {"opus": {"model": "glm-5.2", "display": "GLM-5.2"}},
                "qwen": {"sonnet": {"model": "qwen-3-coder"}},  # display defaults to model
                # AC-2 (model-profiles-glm47-local): a LOCAL family is pure data —
                # an ollama lineup resolves ranks with zero code change.
                "ollama": {
                    "sonnet": {"model": "qwen3:14b", "display": "Qwen3 14B"},
                    "opus": {"model": "qwen3-coder:30b", "display": "Qwen3 Coder 30B"},
                },
            }
        }
    }
    fams = mp.load_families(cfg)
    assert fams["glm"]["opus"]["model"] == "glm-5.2"
    assert fams["glm"]["haiku"]["model"] == "glm-4.5-air"  # untouched default preserved
    assert fams["qwen"]["sonnet"] == {"model": "qwen-3-coder", "display": "qwen-3-coder"}
    assert mp.vendor_of("qwen3:14b", fams) == "ollama"
    assert mp.rank_of("qwen3:14b", fams) == "sonnet"
    assert mp.rank_of("qwen3-coder:30b", fams) == "opus"
    # A local id absent from the config lineup stays unknown — never a guessed rank.
    assert mp.rank_of("qwen3:1b", fams) is None


def test_load_families_skips_malformed_entries():
    cfg = {
        "model_profiles": {
            "families": {
                "glm": {
                    "opus": {"model": ""},  # empty model -> dropped
                    "bogus_rank": {"model": "x"},  # unknown rank -> dropped
                    "sonnet": "not-a-dict",  # -> dropped
                }
            }
        }
    }
    fams = mp.load_families(cfg)
    # opus stays at the default since the override was invalid.
    assert fams["glm"]["opus"]["model"] == "glm-4.7"


def test_vendor_of():
    fams = mp.load_families(None)
    assert mp.vendor_of("glm-4.7", fams) == "glm"
    assert mp.vendor_of("zai-coding-plan/glm-4.7", fams) == "glm"  # provider-scoped id
    assert mp.vendor_of("claude-opus-4-8", fams) == "claude"
    assert mp.vendor_of("claude-opus-4-9-future", fams) == "claude"  # token fallback
    assert mp.vendor_of("gpt-5.6-sol", fams) == "openai"
    assert mp.vendor_of(None, fams) is None
    assert mp.vendor_of("totally-unknown-xyz", fams) is None


@pytest.mark.parametrize(
    "model_id,expected_rank",
    [
        pytest.param("glm-4.7", "fable", id="bare_flagship"),
        pytest.param("GLM-4.7", "fable", id="case_insensitive"),
        pytest.param("zai-coding-plan/glm-4.7", "fable", id="provider_scoped_prefix"),
        pytest.param("glm-4.7 [200k]", "fable", id="context_window_suffix"),
        pytest.param("zai-coding-plan/glm-4.7 [200k]", "fable", id="prefix_and_suffix"),
        pytest.param("glm-4.5-air", "haiku", id="light_rank"),
        # NEGATIVE (model-profiles-glm47-local): a model dropped from the lineup
        # is UNKNOWN — never a stale rank that would fake a verdict.
        pytest.param("glm-4.6", None, id="dropped_from_lineup_is_unknown"),
        pytest.param("totally-unknown", None, id="unknown_id"),
        pytest.param("", None, id="empty"),
    ],
)
def test_rank_of_calibrated(model_id, expected_rank):
    # Every spelling a host may report lands on the same rank, and an unknown
    # id yields None (absence), not a false capability claim.
    fams = mp.load_families(None)
    assert mp.rank_of(model_id, fams) == expected_rank


def test_spec_for_fallback_to_claude():
    fams = mp.load_families(None)
    assert mp.spec_for("glm", "opus", fams)["model"] == "glm-4.7"
    # A family missing a rank falls back to claude's spec for that rank.
    fams2 = {"claude": fams["claude"], "partial": {"haiku": {"model": "p-lite", "display": "P"}}}
    assert mp.spec_for("partial", "opus", fams2)["model"] == "claude-opus-4-8"
    # Unknown family -> claude.
    assert mp.spec_for("nonexistent", "sonnet", fams)["model"] == "claude-sonnet-4-6"


def test_default_family():
    assert mp.default_family({"model_profiles": {"default_family": "glm"}}) == "glm"
    assert mp.default_family({"model_profiles": {}}) is None
    assert mp.default_family(None) is None
