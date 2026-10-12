"""The user tier lives in ~/.config/tausik, not in ~/.tausik (github#104).

user-tier-config-recreates-the-directory-18-removed: ~/.tausik/config.json put
back the ~/.tausik directory 1.8 moved the shared store out of — the directory
that makes a home folder look like a project. The legacy file is still read
when it is the only one, so no setting is lost; the new place wins when both exist.
"""

from __future__ import annotations

import os

import pytest

import config_trust
import project_config


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv(config_trust.USER_CONFIG_ENV, raising=False)
    return tmp_path


def _write(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{}")


def test_nothing_configured_points_at_the_new_place(home):
    assert config_trust.user_config_path() == str(home / ".config" / "tausik" / "config.json")


def test_a_legacy_only_setting_is_still_read(home):
    """NEGATIVE: moving the default does not take anyone's setting away."""
    _write(str(home / ".tausik" / "config.json"))
    assert config_trust.user_config_path() == config_trust.legacy_user_config_path()


def test_the_new_place_wins_when_both_exist(home):
    _write(str(home / ".tausik" / "config.json"))
    _write(config_trust.default_user_config_path())
    assert config_trust.user_config_path() == config_trust.default_user_config_path()


def test_a_home_tausik_with_only_a_config_is_not_a_project(home, monkeypatch):
    """NEGATIVE: the legacy directory never turns the home folder into a project."""
    monkeypatch.delenv("TAUSIK_DIR", raising=False)
    _write(str(home / ".tausik" / "config.json"))
    work = home / "work" / "somewhere"
    work.mkdir(parents=True)
    monkeypatch.chdir(work)
    assert project_config.find_tausik_dir() == str(work / ".tausik")
