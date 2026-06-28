"""Tests for v1.3 config knobs (verify_cache_ttl, session_warn_threshold)."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))


@pytest.fixture
def chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write_cfg(tmp_path, body: dict) -> None:
    cfg_dir = tmp_path / ".tausik"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "config.json").write_text(json.dumps(body))


class TestVerifyCacheTTLConfig:
    def test_default_when_no_config(self, chdir_tmp):
        from project_config import load_config
        from service_verification import DEFAULT_CACHE_TTL_S

        cfg = load_config()
        ttl = cfg.get("verify_cache_ttl_seconds", DEFAULT_CACHE_TTL_S)
        assert ttl == DEFAULT_CACHE_TTL_S

    def test_override_via_config(self, chdir_tmp):
        from project_config import load_config
        from service_verification import DEFAULT_CACHE_TTL_S

        _write_cfg(chdir_tmp, {"verify_cache_ttl_seconds": 1800})
        ttl = load_config().get("verify_cache_ttl_seconds", DEFAULT_CACHE_TTL_S)
        assert ttl == 1800


class TestSessionWarnThreshold:
    def test_default_when_no_config(self, chdir_tmp):
        from session_cleanup_check import _session_warn_min

        assert _session_warn_min(str(chdir_tmp)) == 150

    def test_override_via_config(self, chdir_tmp):
        from session_cleanup_check import _session_warn_min

        _write_cfg(chdir_tmp, {"session_warn_threshold_minutes": 60})
        assert _session_warn_min(str(chdir_tmp)) == 60

    def test_malformed_config_falls_back(self, chdir_tmp):
        from session_cleanup_check import _session_warn_min

        (chdir_tmp / ".tausik").mkdir()
        (chdir_tmp / ".tausik" / "config.json").write_text("{not json")
        assert _session_warn_min(str(chdir_tmp)) == 150

    def test_non_numeric_value_falls_back(self, chdir_tmp):
        from session_cleanup_check import _session_warn_min

        _write_cfg(chdir_tmp, {"session_warn_threshold_minutes": "abc"})
        assert _session_warn_min(str(chdir_tmp)) == 150


class TestSessionIdleThreshold:
    def test_default_when_no_config(self, chdir_tmp):
        from service_session_metrics import resolve_idle_threshold

        assert resolve_idle_threshold(None) == 10

    def test_override_via_config(self, chdir_tmp):
        from service_session_metrics import resolve_idle_threshold

        _write_cfg(chdir_tmp, {"session_idle_threshold_minutes": 25})
        assert resolve_idle_threshold(None) == 25

    def test_explicit_arg_overrides_config(self, chdir_tmp):
        from service_session_metrics import resolve_idle_threshold

        _write_cfg(chdir_tmp, {"session_idle_threshold_minutes": 25})
        assert resolve_idle_threshold(5) == 5
