"""Tests for IDE abstraction layer (ide_utils.py)."""

import pytest
from ide_utils import (
    DEFAULT_IDE,
    IDE_REGISTRY,
    SUPPORTED_IDES,
    detect_ide,
    get_agents_skills_dir,
    get_ide_config,
    get_ide_dir,
    get_rules_file,
    get_skills_dir,
)


class TestDetectIde:
    """Test IDE auto-detection."""

    def test_default_is_claude(self):
        assert detect_ide() == "claude"

    @pytest.mark.parametrize(
        "env_var,env_value,expected",
        [
            pytest.param("TAUSIK_IDE", "cursor", "cursor", id="explicit_tausik_ide_env"),
            pytest.param("TAUSIK_IDE", "windsurf", "windsurf", id="explicit_tausik_ide_windsurf"),
            pytest.param("CURSOR_DIR", "/some/path", "cursor", id="cursor_env_detected"),
        ],
    )
    def test_env_triggered_detection(self, monkeypatch, env_var, env_value, expected):
        monkeypatch.setenv(env_var, env_value)
        assert detect_ide() == expected

    def test_invalid_tausik_ide_raises(self, monkeypatch):
        monkeypatch.setenv("TAUSIK_IDE", "vscode")
        with pytest.raises(ValueError, match="Invalid TAUSIK_IDE"):
            detect_ide()

    def test_windsurf_env_detected(self, monkeypatch):
        monkeypatch.delenv("CURSOR_DIR", raising=False)
        monkeypatch.setenv("WINDSURF_DIR", "/some/path")
        assert detect_ide() == "windsurf"

    def test_codex_env_detected(self, monkeypatch):
        monkeypatch.delenv("CURSOR_DIR", raising=False)
        monkeypatch.delenv("WINDSURF_DIR", raising=False)
        monkeypatch.setenv("CODEX_SANDBOX_DIR", "/some/path")
        assert detect_ide() == "codex"

    def test_explicit_overrides_env(self, monkeypatch):
        monkeypatch.setenv("TAUSIK_IDE", "claude")
        monkeypatch.setenv("CURSOR_DIR", "/some/path")
        assert detect_ide() == "claude"

    def test_cursor_wins_over_windsurf(self, monkeypatch):
        monkeypatch.setenv("CURSOR_DIR", "/a")
        monkeypatch.setenv("WINDSURF_DIR", "/b")
        assert detect_ide() == "cursor"

    @pytest.mark.parametrize(
        "ide_dir,expected",
        [
            pytest.param(".cursor", "cursor", id="project_dir_detection_cursor"),
            pytest.param(".windsurf", "windsurf", id="project_dir_detection_windsurf"),
            pytest.param(".codex", "codex", id="project_dir_detection_codex"),
        ],
    )
    def test_project_dir_detection(self, tmp_path, ide_dir, expected):
        (tmp_path / ide_dir).mkdir()
        assert detect_ide(str(tmp_path)) == expected

    def test_project_dir_priority_cursor_wins(self, tmp_path):
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".windsurf").mkdir()
        assert detect_ide(str(tmp_path)) == "cursor"

    def test_project_dir_no_ide_dirs(self, tmp_path):
        assert detect_ide(str(tmp_path)) == "claude"


class TestGetIdeConfig:
    """Test IDE config retrieval."""

    def test_claude_config(self):
        cfg = get_ide_config("claude")
        assert cfg["config_dir"] == ".claude"
        assert cfg["rules_file"] == "CLAUDE.md"

    def test_cursor_config(self):
        cfg = get_ide_config("cursor")
        assert cfg["config_dir"] == ".cursor"
        assert cfg["rules_file"] == ".cursorrules"

    def test_windsurf_config(self):
        cfg = get_ide_config("windsurf")
        assert cfg["config_dir"] == ".windsurf"

    def test_unknown_ide_raises(self):
        with pytest.raises(ValueError, match="Unknown IDE"):
            get_ide_config("emacs")

    def test_none_defaults_to_claude(self):
        cfg = get_ide_config(None)
        assert cfg["config_dir"] == ".claude"


class TestPathHelpers:
    """Test path resolution functions."""

    def test_get_ide_dir(self, tmp_path):
        result = get_ide_dir(str(tmp_path), "claude")
        assert result.endswith(".claude")

    def test_get_ide_dir_codex(self, tmp_path):
        result = get_ide_dir(str(tmp_path), "codex")
        assert result.endswith(".codex")

    def test_get_skills_dir(self, tmp_path):
        result = get_skills_dir(str(tmp_path), "cursor")
        assert ".cursor" in result
        assert result.endswith("skills")

    def test_get_rules_file(self, tmp_path):
        assert get_rules_file(str(tmp_path), "claude").endswith("CLAUDE.md")
        assert get_rules_file(str(tmp_path), "cursor").endswith(".cursorrules")
        assert get_rules_file(str(tmp_path), "windsurf").endswith(".windsurfrules")
        assert get_rules_file(str(tmp_path), "codex").endswith("AGENTS.md")

    def test_get_agents_skills_dir_shared(self, tmp_path):
        """Shared harness/skills/ is preferred."""
        shared = tmp_path / "harness" / "skills"
        shared.mkdir(parents=True)
        result = get_agents_skills_dir(str(tmp_path), "windsurf")
        assert str(shared) == result

    def test_get_agents_skills_dir_ide_specific(self, tmp_path):
        """Falls back to IDE-specific if no shared dir."""
        ide_dir = tmp_path / "harness" / "cursor" / "skills"
        ide_dir.mkdir(parents=True)
        result = get_agents_skills_dir(str(tmp_path), "cursor")
        assert str(ide_dir) == result

    def test_get_agents_skills_dir_fallback(self, tmp_path):
        """Ultimate fallback to claude."""
        result = get_agents_skills_dir(str(tmp_path), "windsurf")
        assert "claude" in result


class TestRegistry:
    """Test IDE registry completeness."""

    def test_all_ides_have_required_keys(self):
        for ide, cfg in IDE_REGISTRY.items():
            assert "config_dir" in cfg, f"{ide} missing config_dir"
            assert "rules_file" in cfg, f"{ide} missing rules_file"
            assert "skills_subdir" in cfg, f"{ide} missing skills_subdir"

    def test_supported_ides_matches_registry(self):
        assert SUPPORTED_IDES == frozenset(IDE_REGISTRY.keys())

    def test_default_ide_is_supported(self):
        assert DEFAULT_IDE in SUPPORTED_IDES
