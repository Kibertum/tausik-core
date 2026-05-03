"""Tests for optional model hints on task next / hud (config flag task_next.model_hint)."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "test.db"))
    s = ProjectService(be)
    yield s
    be.close()


@pytest.fixture
def chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write_cfg(tmp_path, body: dict) -> None:
    cfg_dir = tmp_path / ".tausik"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "config.json").write_text(json.dumps(body))


def _setup_hierarchy(svc):
    svc.epic_add("v1", "Version 1")
    svc.story_add("v1", "setup", "Setup")


class TestIsTaskNextModelHintEnabled:
    def test_false_when_missing(self):
        from project_config import is_task_next_model_hint_enabled

        assert is_task_next_model_hint_enabled({}) is False

    def test_true_when_set(self):
        from project_config import is_task_next_model_hint_enabled

        assert (
            is_task_next_model_hint_enabled({"task_next": {"model_hint": True}}) is True
        )

    def test_false_when_disabled(self):
        from project_config import is_task_next_model_hint_enabled

        assert (
            is_task_next_model_hint_enabled({"task_next": {"model_hint": False}})
            is False
        )

    def test_false_when_task_next_not_dict(self):
        from project_config import is_task_next_model_hint_enabled

        assert is_task_next_model_hint_enabled({"task_next": "x"}) is False


class TestTaskNextModelHint:
    def test_no_key_when_disabled(self, svc, monkeypatch):
        monkeypatch.setattr(
            "project_config.is_task_next_model_hint_enabled",
            lambda cfg=None: False,
        )
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1", complexity="simple")
        picked = svc.task_next()
        assert picked is not None
        assert "model_hint" not in picked

    def test_hint_when_enabled_simple(self, svc, monkeypatch):
        monkeypatch.setattr(
            "project_config.is_task_next_model_hint_enabled",
            lambda cfg=None: True,
        )
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1", complexity="simple")
        picked = svc.task_next()
        assert picked["model_hint"]["model"] == "claude-haiku-4-5"
        assert picked["model_hint"]["display"] == "Haiku 4.5"

    def test_hint_via_config_file(self, svc, chdir_tmp):
        _write_cfg(chdir_tmp, {"task_next": {"model_hint": True}})
        _setup_hierarchy(svc)
        svc.task_add("setup", "t1", "T1", complexity="complex")
        picked = svc.task_next()
        assert picked["model_hint"]["model"] == "claude-opus-4-7"
