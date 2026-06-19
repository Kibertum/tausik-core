"""Tests for the provider registry — IDE/runtime abstraction (Decision #119, axis-1)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import providers  # noqa: E402
from providers.base import Provider  # noqa: E402


def test_available_lists_runtime_providers():
    avail = providers.available()
    assert avail == ["claude", "cursor", "kilo", "qwen"]


def test_zai_is_not_a_provider():
    # z.ai is a model vendor (model_profiles), NOT a runtime provider.
    assert "zai" not in providers.available()
    with pytest.raises(KeyError):
        providers.get("zai")


@pytest.mark.parametrize("slug", ["claude", "cursor", "kilo", "qwen"])
def test_base_contract(slug):
    p = providers.get(slug)
    assert isinstance(p, Provider)
    assert p.name() == slug
    # Contract methods exist and never raise on a clean environment.
    assert p.get_transcript_path() is None or isinstance(p.get_transcript_path(), str)
    assert p.get_active_model() is None or isinstance(p.get_active_model(), str)


def test_claude_delegates_to_model_routing(monkeypatch):
    # ClaudeProvider must reuse the single-source parser, not duplicate it.
    import model_routing

    monkeypatch.setattr(model_routing, "_auto_find_transcript", lambda: "/tmp/fake.jsonl")
    monkeypatch.setattr(
        model_routing, "read_active_model_from_transcript", lambda p: "claude-opus-4-8"
    )
    assert providers.get("claude").get_active_model() == "claude-opus-4-8"


def test_kilo_reads_env(monkeypatch):
    monkeypatch.setenv("KILO_MODEL", "glm-4.6")
    assert providers.get("kilo").get_active_model() == "glm-4.6"


def test_kilo_reads_config_file(monkeypatch, tmp_path):
    monkeypatch.delenv("KILO_MODEL", raising=False)
    cfg = tmp_path / "kilo.json"
    cfg.write_text('{"model": "glm-4.5-air"}', encoding="utf-8")
    monkeypatch.setenv("KILO_CONFIG", str(cfg))
    assert providers.get("kilo").get_active_model() == "glm-4.5-air"


def test_kilo_unknown_returns_none(monkeypatch):
    monkeypatch.delenv("KILO_MODEL", raising=False)
    monkeypatch.delenv("KILO_CONFIG", raising=False)
    # No env, no config file on a temp cwd → unknown.
    k = providers.get("kilo")
    # _find_kilo_config may still hit a real ~/.config; only assert it never raises.
    assert k.get_active_model() is None or isinstance(k.get_active_model(), str)


def test_reset_repopulates():
    providers.reset()
    assert providers.available() == ["claude", "cursor", "kilo", "qwen"]


def test_malformed_module_does_not_empty_registry(tmp_path):
    # A broken provider file must be skipped, not crash the whole registry.
    broken = os.path.join(os.path.dirname(providers.__file__), "_broken_test_tmp.py")
    with open(broken, "w", encoding="utf-8") as f:
        f.write("this is !!! not valid python\n")
    try:
        providers.reset()
        assert providers.available() == ["claude", "cursor", "kilo", "qwen"]
    finally:
        os.remove(broken)
        import shutil

        shutil.rmtree(
            os.path.join(os.path.dirname(providers.__file__), "__pycache__"), ignore_errors=True
        )
        providers.reset()
