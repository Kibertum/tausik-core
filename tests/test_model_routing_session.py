"""Tests for scripts/model_routing_session — task-recommendation persistence.

Covers the record/read/clear roundtrip, env-disable knob, malformed-file
handling, idempotency, and isolation from skill_profile_session keys.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import model_routing_session as mrs  # noqa: E402


@pytest.fixture
def tausik_dir(tmp_path, monkeypatch):
    # The env-disable knob is on by default in some CI envs; force-clear it
    # so each test sees the production code path unless it opts in.
    monkeypatch.delenv("TAUSIK_DISABLE_TASK_RECOMMENDATION", raising=False)
    d = tmp_path / ".tausik"
    d.mkdir()
    return str(d)


# --- record + read roundtrip -----------------------------------------------


def test_record_simple_persists_haiku(tausik_dir):
    payload = mrs.record_active_task_recommendation(tausik_dir, "fix-bug", "simple")
    assert payload is not None
    assert payload["slug"] == "fix-bug"
    assert payload["complexity"] == "simple"
    assert payload["model"] == "claude-haiku-4-5"
    assert payload["display"] == "Haiku 4.5"
    assert payload["recorded_at"].endswith("Z")
    # Read sees the same payload.
    got = mrs.read_active_task_recommendation(tausik_dir)
    assert got is not None
    assert got["model"] == "claude-haiku-4-5"
    assert got["slug"] == "fix-bug"


def test_record_complex_persists_opus(tausik_dir):
    payload = mrs.record_active_task_recommendation(tausik_dir, "big-refactor", "complex")
    assert payload is not None
    assert payload["model"] == "claude-opus-4-7"


def test_record_unknown_complexity_normalized_to_none(tausik_dir):
    # Banner falls back to Sonnet for unknown complexity; we should record
    # complexity as None rather than echoing the bogus string back.
    payload = mrs.record_active_task_recommendation(tausik_dir, "weird", "epic")
    assert payload is not None
    assert payload["complexity"] is None
    # Default Sonnet still wins.
    assert payload["model"] == "claude-sonnet-4-6"


def test_record_no_slug_returns_none(tausik_dir):
    # Empty / non-string slug is rejected — never write a useless entry.
    assert mrs.record_active_task_recommendation(tausik_dir, "", "simple") is None
    assert mrs.read_active_task_recommendation(tausik_dir) is None


# --- clear -----------------------------------------------------------------


def test_clear_removes_file(tausik_dir):
    mrs.record_active_task_recommendation(tausik_dir, "x", "simple")
    assert mrs.read_active_task_recommendation(tausik_dir) is not None
    assert mrs.clear_active_task_recommendation(tausik_dir) is True
    assert mrs.read_active_task_recommendation(tausik_dir) is None
    # Second clear is a no-op (idempotent).
    assert mrs.clear_active_task_recommendation(tausik_dir) is False


# --- env disable -----------------------------------------------------------


def test_env_disable_makes_record_a_noop(tausik_dir, monkeypatch):
    monkeypatch.setenv("TAUSIK_DISABLE_TASK_RECOMMENDATION", "1")
    assert mrs.record_active_task_recommendation(tausik_dir, "x", "simple") is None
    # Nothing written.
    assert not os.path.isfile(os.path.join(tausik_dir, ".task_recommendation.json"))


def test_env_disable_makes_read_return_none_even_with_existing_file(tausik_dir, monkeypatch):
    # Pre-populate while disable is off.
    mrs.record_active_task_recommendation(tausik_dir, "x", "simple")
    assert mrs.read_active_task_recommendation(tausik_dir) is not None
    monkeypatch.setenv("TAUSIK_DISABLE_TASK_RECOMMENDATION", "1")
    assert mrs.read_active_task_recommendation(tausik_dir) is None


def test_env_disable_makes_clear_a_noop(tausik_dir, monkeypatch):
    mrs.record_active_task_recommendation(tausik_dir, "x", "simple")
    monkeypatch.setenv("TAUSIK_DISABLE_TASK_RECOMMENDATION", "1")
    assert mrs.clear_active_task_recommendation(tausik_dir) is False
    # File still exists — we did NOT delete it under disable.
    assert os.path.isfile(os.path.join(tausik_dir, ".task_recommendation.json"))


# --- malformed file --------------------------------------------------------


def test_read_malformed_json_returns_none(tausik_dir):
    path = os.path.join(tausik_dir, ".task_recommendation.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write("{not valid json}")
    assert mrs.read_active_task_recommendation(tausik_dir) is None


def test_read_partial_json_returns_none(tausik_dir):
    # Hand-edited file missing required fields — treat as missing.
    path = os.path.join(tausik_dir, ".task_recommendation.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"slug": "x"}, f)  # no model/display/recorded_at
    assert mrs.read_active_task_recommendation(tausik_dir) is None


def test_read_non_object_returns_none(tausik_dir):
    path = os.path.join(tausik_dir, ".task_recommendation.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump([1, 2, 3], f)
    assert mrs.read_active_task_recommendation(tausik_dir) is None


# --- isolation from skill_profile_session ---------------------------------


def test_record_does_not_touch_session_json(tausik_dir):
    """`.session.json` (skill profile) and `.task_recommendation.json` are
    different files; recording one must NOT clobber the other.
    """
    session_path = os.path.join(tausik_dir, ".session.json")
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "schema_version": 1,
                "ide": "claude",
                "model": "opus",
                "source": "config",
                "last_rebuild_at": None,
            },
            f,
        )
    mrs.record_active_task_recommendation(tausik_dir, "x", "complex")
    # session.json untouched.
    with open(session_path, encoding="utf-8") as f:
        sess = json.load(f)
    assert sess["model"] == "opus"
    assert sess["ide"] == "claude"


def test_record_overwrites_previous_recommendation(tausik_dir):
    """Each task_start replaces the prior recording — no append/history."""
    mrs.record_active_task_recommendation(tausik_dir, "first", "simple")
    second = mrs.record_active_task_recommendation(tausik_dir, "second", "complex")
    assert second is not None
    got = mrs.read_active_task_recommendation(tausik_dir)
    assert got is not None
    assert got["slug"] == "second"
    assert got["model"] == "claude-opus-4-7"


# --- atomic write ---------------------------------------------------------


def test_atomic_write_no_tmp_leftover(tausik_dir):
    mrs.record_active_task_recommendation(tausik_dir, "x", "simple")
    # The .tmp file should be renamed away — never linger after a successful write.
    leftover = os.path.join(tausik_dir, ".task_recommendation.json.tmp")
    assert not os.path.isfile(leftover)
