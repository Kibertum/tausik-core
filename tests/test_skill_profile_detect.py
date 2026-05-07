"""Tests for scripts/skill_profile_detect.py — IDE + model env detection."""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import skill_profile_detect as spd  # noqa: E402


# --- normalize_model_profile_slug ---------------------------------------


@pytest.mark.parametrize(
    "input_str,expected",
    [
        pytest.param("GPT-5", "gpt-5", id="basic_lowercase"),
        pytest.param("gpt-5.5", "gpt-5-5", id="dot_to_hyphen"),
        pytest.param("Claude  Sonnet  4.6", "claude-sonnet-4-6", id="collapses_runs"),
        pytest.param("--gpt-5--", "gpt-5", id="strips_edge_hyphens"),
    ],
)
def test_normalize_model_profile_slug(input_str, expected):
    assert spd.normalize_model_profile_slug(input_str) == expected


def test_normalize_empty():
    assert spd.normalize_model_profile_slug("") == ""
    assert spd.normalize_model_profile_slug("   ") == ""


def test_normalize_non_string():
    assert spd.normalize_model_profile_slug(None) == ""  # type: ignore[arg-type]
    assert spd.normalize_model_profile_slug(123) == ""  # type: ignore[arg-type]


# --- detect_ide ----------------------------------------------------------


@pytest.fixture
def clean_env(monkeypatch):
    """Strip every IDE/model env var so tests start from a known state."""
    for _, name in spd._IDE_ENV_MARKERS:
        monkeypatch.delenv(name, raising=False)
    for name in spd._MODEL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("TAUSIK_IDE_PROFILE", raising=False)
    monkeypatch.delenv("TAUSIK_MODEL_PROFILE", raising=False)


@pytest.mark.parametrize(
    "env_var,env_value,expected_ide",
    [
        pytest.param("CLAUDE_CODE_SSE_PORT", "8765", "claude", id="claude_via_sse_port"),
        pytest.param("CLAUDECODE", "1", "claude", id="claude_via_claudecode"),
        pytest.param("CURSOR_TRACE_ID", "abc", "cursor", id="cursor"),
        pytest.param("QWEN_CODE", "1", "qwen", id="qwen"),
        pytest.param("CODEX_SANDBOX_DIR", "/tmp/x", "codex", id="codex"),
    ],
)
def test_detect_ide_via_env(clean_env, monkeypatch, env_var, env_value, expected_ide):
    monkeypatch.setenv(env_var, env_value)
    assert spd.detect_ide() == expected_ide


def test_detect_ide_none_when_clean(clean_env):
    assert spd.detect_ide() is None


# --- detect_model --------------------------------------------------------


@pytest.mark.parametrize(
    "env_var,env_value,expected_model",
    [
        pytest.param("ANTHROPIC_MODEL", "claude-opus-4-7", "opus", id="anthropic_opus"),
        pytest.param("ANTHROPIC_MODEL", "claude-sonnet-4-6", "sonnet", id="anthropic_sonnet"),
        pytest.param("OPENAI_MODEL", "gpt-5", "gpt-5", id="openai_gpt5"),
        pytest.param("OPENAI_MODEL", "gpt-5.5", "gpt-5-5", id="openai_gpt55"),
        pytest.param("QWEN_MODEL", "Qwen2.5-Max", "qwen", id="qwen"),
    ],
)
def test_detect_model_via_env(clean_env, monkeypatch, env_var, env_value, expected_model):
    monkeypatch.setenv(env_var, env_value)
    assert spd.detect_model() == expected_model


def test_detect_model_tausik_override_wins(clean_env, monkeypatch):
    """TAUSIK_MODEL is highest priority among model env vars."""
    monkeypatch.setenv("TAUSIK_MODEL", "haiku")
    monkeypatch.setenv("ANTHROPIC_MODEL", "opus")
    assert spd.detect_model() == "haiku"


def test_detect_model_none_when_clean(clean_env):
    assert spd.detect_model() is None


def test_detect_model_unknown_string_returns_none(clean_env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "some-future-model-zzz")
    assert spd.detect_model() is None


def test_detect_model_empty_string_returns_none(clean_env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "")
    assert spd.detect_model() is None
