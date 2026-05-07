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


def test_normalize_basic_lowercase():
    assert spd.normalize_model_profile_slug("GPT-5") == "gpt-5"


def test_normalize_dot_to_hyphen():
    assert spd.normalize_model_profile_slug("gpt-5.5") == "gpt-5-5"


def test_normalize_collapses_runs():
    assert spd.normalize_model_profile_slug("Claude  Sonnet  4.6") == "claude-sonnet-4-6"


def test_normalize_strips_edge_hyphens():
    assert spd.normalize_model_profile_slug("--gpt-5--") == "gpt-5"


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


def test_detect_ide_claude_via_sse_port(clean_env, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SSE_PORT", "8765")
    assert spd.detect_ide() == "claude"


def test_detect_ide_claude_via_claudecode(clean_env, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    assert spd.detect_ide() == "claude"


def test_detect_ide_cursor(clean_env, monkeypatch):
    monkeypatch.setenv("CURSOR_TRACE_ID", "abc")
    assert spd.detect_ide() == "cursor"


def test_detect_ide_qwen(clean_env, monkeypatch):
    monkeypatch.setenv("QWEN_CODE", "1")
    assert spd.detect_ide() == "qwen"


def test_detect_ide_codex(clean_env, monkeypatch):
    monkeypatch.setenv("CODEX_SANDBOX_DIR", "/tmp/x")
    assert spd.detect_ide() == "codex"


def test_detect_ide_none_when_clean(clean_env):
    assert spd.detect_ide() is None


# --- detect_model --------------------------------------------------------


def test_detect_model_anthropic_opus(clean_env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-7")
    assert spd.detect_model() == "opus"


def test_detect_model_anthropic_sonnet(clean_env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    assert spd.detect_model() == "sonnet"


def test_detect_model_openai_gpt5(clean_env, monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5")
    assert spd.detect_model() == "gpt-5"


def test_detect_model_openai_gpt55(clean_env, monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.5")
    assert spd.detect_model() == "gpt-5-5"


def test_detect_model_qwen(clean_env, monkeypatch):
    monkeypatch.setenv("QWEN_MODEL", "Qwen2.5-Max")
    assert spd.detect_model() == "qwen"


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
