"""Tests for scripts/skill_profile_session.py — session state + resolution."""

from __future__ import annotations

import json
import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import skill_profile_detect as spd  # noqa: E402
import skill_profile_session as sps  # noqa: E402


@pytest.fixture
def clean_env(monkeypatch):
    for _, name in spd._IDE_ENV_MARKERS:
        monkeypatch.delenv(name, raising=False)
    for name in spd._MODEL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("TAUSIK_IDE_PROFILE", raising=False)
    monkeypatch.delenv("TAUSIK_MODEL_PROFILE", raising=False)


# --- load/save roundtrip --------------------------------------------------


def test_load_missing_returns_defaults(tmp_path):
    state = sps.load_session_state(str(tmp_path))
    assert state == {
        "schema_version": 1,
        "ide": None,
        "model": None,
        "last_rebuild_at": None,
        "source": "unknown",
    }


def test_save_then_load_roundtrip(tmp_path):
    saved = {
        "ide": "claude",
        "model": "opus",
        "source": "auto",
        "last_rebuild_at": "2026-05-07T10:00:00Z",
    }
    sps.save_session_state(str(tmp_path), saved)
    state = sps.load_session_state(str(tmp_path))
    assert state["ide"] == "claude"
    assert state["model"] == "opus"
    assert state["source"] == "auto"
    assert state["last_rebuild_at"] == "2026-05-07T10:00:00Z"
    assert state["schema_version"] == 1


def test_load_malformed_returns_defaults(tmp_path):
    path = os.path.join(str(tmp_path), ".session.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write("{not valid json")
    state = sps.load_session_state(str(tmp_path))
    assert state["ide"] is None
    assert state["source"] == "unknown"


def test_load_wrong_type_returns_defaults(tmp_path):
    path = os.path.join(str(tmp_path), ".session.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write('"not a dict"')
    state = sps.load_session_state(str(tmp_path))
    assert state["source"] == "unknown"


def test_save_creates_dir_if_missing(tmp_path):
    nested = os.path.join(str(tmp_path), "deeply", "nested", "tausik")
    sps.save_session_state(nested, {"ide": "cursor"})
    assert os.path.isfile(os.path.join(nested, ".session.json"))


# --- resolve precedence --------------------------------------------------


def test_resolve_env_wins_over_config(clean_env, monkeypatch):
    monkeypatch.setenv("TAUSIK_IDE_PROFILE", "cursor")
    monkeypatch.setenv("TAUSIK_MODEL_PROFILE", "gpt-5")
    cfg = {"ide_profile": "claude", "model_profile": "opus"}
    ide, model, source = sps.resolve_profile(cfg)
    assert ide == "cursor"
    assert model == "gpt-5"
    assert source == "env"


def test_resolve_config_wins_over_auto(clean_env, monkeypatch):
    """Config takes precedence over auto-detect."""
    monkeypatch.setenv("CLAUDECODE", "1")  # auto would say "claude"
    cfg = {"ide_profile": "cursor", "model_profile": "opus"}
    ide, model, source = sps.resolve_profile(cfg)
    assert ide == "cursor"
    assert model == "opus"
    assert source == "config"


def test_resolve_auto_when_no_overrides(clean_env, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    ide, model, source = sps.resolve_profile({})
    assert ide == "claude"
    assert model == "sonnet"
    assert source == "auto"


def test_resolve_unknown_when_nothing_resolves(clean_env):
    ide, model, source = sps.resolve_profile({})
    assert ide is None
    assert model is None
    assert source == "unknown"


def test_resolve_invalid_env_value_falls_through_to_auto(clean_env, monkeypatch):
    """Garbage env value is rejected — falls through to auto-detect (None here)."""
    monkeypatch.setenv("TAUSIK_IDE_PROFILE", "not-a-real-ide")
    ide, _, source = sps.resolve_profile({})
    # env value rejected → no fallback → ide stays None
    assert ide is None
    assert source == "unknown"


def test_resolve_mixed_sources_reports_weakest(clean_env, monkeypatch):
    """When env supplies ide and config supplies model, source = weakest = config."""
    monkeypatch.setenv("TAUSIK_IDE_PROFILE", "claude")
    cfg = {"model_profile": "opus"}
    ide, model, source = sps.resolve_profile(cfg)
    assert ide == "claude"
    assert model == "opus"
    assert source == "config"


def test_save_atomic_no_tmp_left(tmp_path):
    sps.save_session_state(str(tmp_path), {"ide": "claude"})
    assert not os.path.exists(os.path.join(str(tmp_path), ".session.json.tmp"))


def test_save_persists_schema_version(tmp_path):
    sps.save_session_state(str(tmp_path), {"ide": "claude"})
    with open(os.path.join(str(tmp_path), ".session.json"), encoding="utf-8") as f:
        data = json.load(f)
    assert data["schema_version"] == 1
