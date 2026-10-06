"""Tests for the provider registry — IDE/runtime abstraction (Decision #119, axis-1)."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import providers
from providers.base import Provider


def test_available_lists_runtime_providers():
    avail = providers.available()
    assert avail == ["claude", "codex", "cursor", "kilo", "qwen"]


def test_zai_is_not_a_provider():
    # z.ai is a model vendor (model_profiles), NOT a runtime provider.
    assert "zai" not in providers.available()
    with pytest.raises(KeyError):
        providers.get("zai")


@pytest.mark.parametrize("slug", ["claude", "codex", "cursor", "kilo", "qwen"])
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


def test_kilo_reads_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # keep the repo's own runtime state out of the test
    monkeypatch.setenv("KILO_MODEL", "glm-4.6")
    assert providers.get("kilo").get_active_model() == "glm-4.6"


def test_kilo_reads_config_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KILO_MODEL", raising=False)
    cfg = tmp_path / "kilo.json"
    cfg.write_text('{"model": "glm-4.5-air"}', encoding="utf-8")
    monkeypatch.setenv("KILO_CONFIG", str(cfg))
    assert providers.get("kilo").get_active_model() == "glm-4.5-air"


def test_kilo_unknown_returns_none(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KILO_MODEL", raising=False)
    k = providers.get("kilo")
    # Stub config discovery so the real ~/.config/kilo can't make this flaky.
    monkeypatch.setattr(k, "_find_kilo_config", lambda: None)
    assert k.get_active_model() is None


def test_kilo_prefers_runtime_observation_over_everything(monkeypatch, tmp_path):
    """provider-agnostic-model-observation: the plugin's live observation is what
    the host is running RIGHT NOW — it outranks the env var and any config."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KILO_MODEL", "glm-4.6")
    runtime = tmp_path / ".tausik" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "active_model.json").write_text(
        json.dumps(
            {
                "provider_id": "zai-coding-plan",
                "model_id": "glm-4.7",
                "source": "kilo-plugin",
                "updated_at": "2026-10-06T17:30:00Z",
            }
        ),
        encoding="utf-8",
    )
    assert providers.get("kilo").get_active_model() == "glm-4.7"


@pytest.mark.parametrize(
    "payload",
    [
        "not json at all",
        '{"model_id": "glm 4.7 with spaces"}',  # not a token — sanitise refuses
        '{"model_id": "' + "x" * 200 + '"}',  # oversized
        '{"provider_id": "zai"}',  # no model_id key
        '["glm-4.7"]',  # wrong shape
    ],
)
def test_kilo_invalid_runtime_observation_is_absence_not_a_guess(monkeypatch, tmp_path, payload):
    """THE negative: a broken runtime file yields NO model — the chain falls
    through (here: to a None config) instead of promoting garbage or inventing
    a model from the host's name."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KILO_MODEL", raising=False)
    k = providers.get("kilo")
    monkeypatch.setattr(k, "_find_kilo_config", lambda: None)
    runtime = tmp_path / ".tausik" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "active_model.json").write_text(payload, encoding="utf-8")
    assert k.get_active_model() is None


def test_kilo_reads_project_jsonc_with_comments(monkeypatch, tmp_path):
    """The project config bootstrap writes is kilo.jsonc and MAY carry comments;
    the measured real global config is ~/.config/kilo/kilo.jsonc. Both go through
    the one shared JSONC reader."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KILO_MODEL", raising=False)
    kilo_dir = tmp_path / ".kilo"
    kilo_dir.mkdir()
    (kilo_dir / "kilo.jsonc").write_text(
        '{\n // chosen in UI\n "model": "glm-4.7", // trailing\n}', encoding="utf-8"
    )
    assert providers.get("kilo").get_active_model() == "glm-4.7"


def test_kilo_reads_global_jsonc(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KILO_MODEL", raising=False)
    fake_home = tmp_path / "home"
    (fake_home / ".config" / "kilo").mkdir(parents=True)
    (fake_home / ".config" / "kilo" / "kilo.jsonc").write_text(
        '{"model": "qwen3.8"}', encoding="utf-8"
    )
    import providers.kilo as kilo_mod

    monkeypatch.setattr(kilo_mod.os.path, "expanduser", lambda _: str(fake_home))
    assert providers.get("kilo").get_active_model() == "qwen3.8"


def test_reset_repopulates():
    providers.reset()
    assert providers.available() == ["claude", "codex", "cursor", "kilo", "qwen"]


def test_malformed_module_does_not_empty_registry(tmp_path):
    # A broken provider file must be skipped, not crash the whole registry.
    broken = os.path.join(os.path.dirname(providers.__file__), "_broken_test_tmp.py")
    with open(broken, "w", encoding="utf-8") as f:
        f.write("this is !!! not valid python\n")
    try:
        providers.reset()
        assert providers.available() == ["claude", "codex", "cursor", "kilo", "qwen"]
    finally:
        os.remove(broken)
        import shutil

        shutil.rmtree(
            os.path.join(os.path.dirname(providers.__file__), "__pycache__"), ignore_errors=True
        )
        providers.reset()
