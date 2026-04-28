"""Tests for brain section in brain_config."""

import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import brain_config  # noqa: E402


def test_load_brain_defaults_when_cfg_empty():
    b = brain_config.load_brain({})
    assert b["enabled"] is False
    assert b["local_mirror_path"] == "~/.tausik-brain/brain.db"
    assert b["notion_integration_token_env"] == "NOTION_TAUSIK_TOKEN"
    assert b["database_ids"] == {
        "decisions": "",
        "web_cache": "",
        "patterns": "",
        "gotchas": "",
    }
    assert b["project_names"] == []
    assert b["ttl_web_cache_days"] == 30
    assert b["ttl_decisions_days"] is None
    assert b["private_url_patterns"] == []


def test_load_brain_merges_user_values():
    cfg = {
        "brain": {
            "enabled": True,
            "database_ids": {"decisions": "uuid-1"},
            "project_names": ["myproj"],
        }
    }
    b = brain_config.load_brain(cfg)
    assert b["enabled"] is True
    # merged, not replaced
    assert b["database_ids"]["decisions"] == "uuid-1"
    assert b["database_ids"]["web_cache"] == ""
    assert b["database_ids"]["patterns"] == ""
    assert b["project_names"] == ["myproj"]
    # unchanged defaults preserved
    assert b["ttl_web_cache_days"] == 30


def test_load_brain_does_not_mutate_defaults():
    cfg = {"brain": {"database_ids": {"decisions": "xxx"}}}
    _ = brain_config.load_brain(cfg)
    # Re-load on empty config must still give pristine defaults
    b2 = brain_config.load_brain({})
    assert b2["database_ids"] == {
        "decisions": "",
        "web_cache": "",
        "patterns": "",
        "gotchas": "",
    }


def test_is_brain_enabled_false_by_default():
    assert brain_config.is_brain_enabled({}) is False
    assert brain_config.is_brain_enabled({"brain": {"enabled": False}}) is False


def test_is_brain_enabled_true_when_flag_set():
    assert brain_config.is_brain_enabled({"brain": {"enabled": True}}) is True


def test_validate_brain_disabled_passes_with_empty_fields():
    """When brain is disabled, missing db_ids / token must NOT be errors."""
    assert brain_config.validate_brain({}) == []
    assert brain_config.validate_brain({"brain": {"enabled": False}}) == []


def test_validate_brain_enabled_reports_missing_database_ids():
    cfg = {
        "brain": {
            "enabled": True,
            "notion_integration_token_env": "SOME_ENV_VAR_THAT_EXISTS",
        }
    }
    errors = brain_config.validate_brain(cfg)
    categories_in_errors = [
        c
        for c in ("decisions", "web_cache", "patterns", "gotchas")
        if any(c in e for e in errors)
    ]
    assert len(categories_in_errors) == 4


def test_validate_brain_enabled_reports_missing_token_env_name(monkeypatch):
    """v1.3.2: with empty token_env, validate falls back to default
    'NOTION_TAUSIK_TOKEN' via resolve_brain_token cascade. If neither env nor
    .tausik/.env nor inline config provides a token, the error message points
    at the default name."""
    monkeypatch.delenv("NOTION_TAUSIK_TOKEN", raising=False)
    monkeypatch.chdir(monkeypatch.fixture("tmp_path") if False else "/tmp")
    cfg = {
        "brain": {
            "enabled": True,
            "notion_integration_token_env": "",
            "database_ids": {
                "decisions": "a",
                "web_cache": "b",
                "patterns": "c",
                "gotchas": "d",
            },
        }
    }
    errors = brain_config.validate_brain(cfg)
    assert any("Notion token not found" in e for e in errors)
    assert any("NOTION_TAUSIK_TOKEN" in e for e in errors)


def test_validate_brain_enabled_reports_unset_env_var(monkeypatch):
    monkeypatch.delenv("NOTION_TEST_TOKEN", raising=False)
    cfg = {
        "brain": {
            "enabled": True,
            "notion_integration_token_env": "NOTION_TEST_TOKEN",
            "database_ids": {
                "decisions": "a",
                "web_cache": "b",
                "patterns": "c",
                "gotchas": "d",
            },
        }
    }
    errors = brain_config.validate_brain(cfg)
    assert any("NOTION_TEST_TOKEN" in e for e in errors)


def test_validate_brain_passes_when_everything_configured(monkeypatch):
    monkeypatch.setenv("NOTION_TEST_TOKEN", "secret-xxx")
    cfg = {
        "brain": {
            "enabled": True,
            "notion_integration_token_env": "NOTION_TEST_TOKEN",
            "database_ids": {
                "decisions": "uuid-d",
                "web_cache": "uuid-w",
                "patterns": "uuid-p",
                "gotchas": "uuid-g",
            },
            "ttl_web_cache_days": 30,
        }
    }
    assert brain_config.validate_brain(cfg) == []


def test_validate_brain_reports_invalid_regex():
    cfg = {"brain": {"private_url_patterns": ["valid.*", "[unclosed"]}}
    errors = brain_config.validate_brain(cfg)
    assert any("[unclosed" in e for e in errors)


def test_validate_brain_reports_non_string_pattern():
    cfg = {"brain": {"private_url_patterns": [123]}}
    errors = brain_config.validate_brain(cfg)
    assert any("private_url_patterns" in e for e in errors)


def test_validate_brain_reports_invalid_ttl(monkeypatch):
    monkeypatch.setenv("NOTION_T", "x")
    cfg = {
        "brain": {
            "enabled": True,
            "notion_integration_token_env": "NOTION_T",
            "database_ids": {
                "decisions": "a",
                "web_cache": "b",
                "patterns": "c",
                "gotchas": "d",
            },
            "ttl_web_cache_days": -1,
            "ttl_decisions_days": "forever",
        }
    }
    errors = brain_config.validate_brain(cfg)
    assert any("ttl_web_cache_days" in e for e in errors)
    assert any("ttl_decisions_days" in e for e in errors)


def test_get_brain_mirror_path_expands_tilde():
    path = brain_config.get_brain_mirror_path({})
    assert "~" not in path
    assert os.path.isabs(path)
    assert path.endswith(os.path.join(".tausik-brain", "brain.db"))


def test_get_brain_mirror_path_expands_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_TEST_HOME", str(tmp_path))
    cfg = {"brain": {"local_mirror_path": "$BRAIN_TEST_HOME/brain.db"}}
    path = brain_config.get_brain_mirror_path(cfg)
    assert path == os.path.abspath(os.path.join(str(tmp_path), "brain.db"))


def test_compute_project_hash_deterministic():
    h1 = brain_config.compute_project_hash("My Project")
    h2 = brain_config.compute_project_hash("my-project")
    h3 = brain_config.compute_project_hash("  My   Project  ")
    # All three canonicalize to "my-project"
    assert h1 == h2 == h3


def test_compute_project_hash_length_and_charset():
    h = brain_config.compute_project_hash("anything")
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_project_hash_different_names_differ():
    h1 = brain_config.compute_project_hash("project-a")
    h2 = brain_config.compute_project_hash("project-b")
    assert h1 != h2


def test_compute_project_hash_matches_sha256_prefix():
    expected = hashlib.sha256(b"tausik").hexdigest()[:16]
    assert brain_config.compute_project_hash("TAUSIK") == expected


def test_compute_project_hash_rejects_empty():
    with pytest.raises(ValueError):
        brain_config.compute_project_hash("")
    with pytest.raises(ValueError):
        brain_config.compute_project_hash("   ")
