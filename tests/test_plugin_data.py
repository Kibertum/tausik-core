"""Test plugin-data directory resolution (CLAUDE_PLUGIN_DATA + fallback)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from plugin_data import get_plugin_data_dir


def test_env_var_takes_priority(tmp_path, monkeypatch):
    target = tmp_path / "plugin-state"
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(target))
    path = get_plugin_data_dir(project_dir=str(tmp_path / "other"))
    assert os.path.abspath(path) == os.path.abspath(str(target))
    assert os.path.isdir(path)


def test_fallback_when_env_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)
    path = get_plugin_data_dir(project_dir=str(tmp_path))
    assert path.endswith(os.path.join(".tausik", "plugin_data"))
    assert os.path.isdir(path)


def test_fallback_when_env_empty_string(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", "   ")
    path = get_plugin_data_dir(project_dir=str(tmp_path))
    assert ".tausik" in path
    assert os.path.isdir(path)


def test_returns_absolute_path(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)
    path = get_plugin_data_dir(project_dir=str(tmp_path))
    assert os.path.isabs(path)


def test_create_false_does_not_make_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "nope"))
    path = get_plugin_data_dir(create=False)
    assert not os.path.exists(path)


def test_makedirs_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "state"))
    p1 = get_plugin_data_dir()
    p2 = get_plugin_data_dir()
    assert p1 == p2
    assert os.path.isdir(p1)
