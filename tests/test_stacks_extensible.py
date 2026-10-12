"""VALID_STACKS extensibility — cfg.custom_stacks runtime merge."""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from project_types import DEFAULT_STACKS, VALID_STACKS, get_valid_stacks
from tausik_utils import ServiceError


def _make_service(db_path: str) -> ProjectService:
    return ProjectService(SQLiteBackend(db_path))


@pytest.fixture
def svc(tmp_path):
    s = _make_service(str(tmp_path / "ext.db"))
    s.epic_add("e", "Epic")
    s.story_add("e", "s", "Story")
    yield s
    s.be.close()


# === project_types: DEFAULT_STACKS + get_valid_stacks ===


class TestDefaultStacks:
    def test_default_stacks_unchanged(self):
        # Sanity: existing stacks remain in defaults
        for stack in (
            "python",
            "rust",
            "go",
            "ruby" not in DEFAULT_STACKS and "php",  # php is in, ruby is not
            "terraform",
        ):
            if stack:
                assert stack in DEFAULT_STACKS

    def test_valid_stacks_alias(self):
        # Backwards-compat alias
        assert VALID_STACKS == DEFAULT_STACKS

    def test_ruby_not_in_defaults(self):
        # Ruby should NOT be a default stack — it's the canonical "custom" example
        assert "ruby" not in DEFAULT_STACKS


class TestGetValidStacks:
    def test_no_cfg_returns_defaults(self):
        assert get_valid_stacks() == DEFAULT_STACKS
        assert get_valid_stacks(None) == DEFAULT_STACKS
        assert get_valid_stacks({}) == DEFAULT_STACKS

    def test_custom_stacks_added(self):
        cfg = {"custom_stacks": ["ruby", "elixir", "scala"]}
        out = get_valid_stacks(cfg)
        assert "ruby" in out
        assert "elixir" in out
        assert "scala" in out
        # Defaults still present
        assert "python" in out

    def test_malformed_custom_stacks_ignored(self):
        # Non-list value → skip silently
        assert get_valid_stacks({"custom_stacks": "ruby"}) == DEFAULT_STACKS
        assert get_valid_stacks({"custom_stacks": {"ruby": True}}) == DEFAULT_STACKS

    def test_empty_or_non_string_entries_dropped(self):
        cfg = {"custom_stacks": ["ruby", "", None, 42, "  ", "elixir"]}
        out = get_valid_stacks(cfg)
        assert "ruby" in out
        assert "elixir" in out
        # 4 garbage entries dropped → set size = defaults + 2 valid
        assert len(out) == len(DEFAULT_STACKS) + 2

    def test_custom_stacks_whitespace_stripped(self):
        cfg = {"custom_stacks": ["  ruby  ", "elixir\n"]}
        out = get_valid_stacks(cfg)
        assert "ruby" in out
        assert "elixir" in out


# === Service-layer validation honours custom stacks ===


def _patch_load_config(custom_stacks):
    """Patch project_config.load_config (where it's referenced from)."""
    return patch(
        "project_config.load_config",
        return_value={"custom_stacks": custom_stacks},
    )


class TestServiceTaskAdd:
    def test_default_stack_still_works(self, svc):
        svc.task_add("s", "t1", "Task", role="developer", stack="python")
        assert svc.be.task_get("t1")["stack"] == "python"

    def test_custom_stack_via_config(self, svc):
        with _patch_load_config(["ruby", "elixir"]):
            svc.task_add("s", "t1", "Task", role="developer", stack="ruby")
        assert svc.be.task_get("t1")["stack"] == "ruby"

    def test_unknown_stack_rejected_with_suggestion(self, svc):
        with _patch_load_config([]):
            with pytest.raises(ServiceError, match="Invalid stack 'rubby'"):
                svc.task_add("s", "t1", "Task", role="developer", stack="rubby")


class TestServiceTaskUpdate:
    def test_update_to_custom_stack(self, svc):
        # First create with a default
        svc.task_add("s", "t1", "Task", role="developer", stack="python")
        # Then update to custom (config-defined)
        with _patch_load_config(["ruby"]):
            svc.task_update("t1", stack="ruby")
        assert svc.be.task_get("t1")["stack"] == "ruby"

    def test_update_unknown_stack_rejected(self, svc):
        svc.task_add("s", "t1", "Task", role="developer", stack="python")
        with _patch_load_config([]):
            with pytest.raises(ServiceError, match="Invalid stack"):
                svc.task_update("t1", stack="zigzag")


# === stack_info / stack_list expose custom flag ===


class TestStackVisibility:
    def test_stack_list_marks_custom(self, svc):
        with _patch_load_config(["ruby", "scala"]):
            rows = svc.stack_list()
        by_stack = {r["stack"]: r for r in rows}
        assert by_stack["ruby"]["is_custom"] is True
        assert by_stack["scala"]["is_custom"] is True
        assert by_stack["python"]["is_custom"] is False

    def test_stack_info_accepts_custom(self, svc):
        with _patch_load_config(["ruby"]):
            info = svc.stack_info("ruby")
        # Custom stack has no stack-scoped gates by default — only universals
        names = [g["name"] for g in info["gates"]]
        assert "filesize" in names
        # No language-specific gates registered
        assert "pytest" not in names
        assert "go-test" not in names

    def test_stack_info_rejects_unknown(self, svc):
        with _patch_load_config(["ruby"]):
            with pytest.raises(ServiceError, match="Unknown stack 'zigzag'"):
                svc.stack_info("zigzag")


class TestCliStackOutput:
    def test_list_output_shows_custom_marker(self, svc, capsys):
        from argparse import Namespace
        from project_cli_stack import cmd_stack

        with _patch_load_config(["ruby"]):
            cmd_stack(svc, Namespace(stack_cmd="list"))
        out = capsys.readouterr().out
        assert "ruby" in out
        assert "(custom)" in out
        # Default stacks NOT marked custom
        for line in out.splitlines():
            if "python" in line:
                assert "(custom)" not in line


class TestDocsConsistency:
    def test_claude_md_no_stale_count(self):
        path = os.path.join(os.path.dirname(__file__), "..", "CLAUDE.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        # Old line "20 значений" should be gone
        assert "20 значений" not in text
        # New custom_stacks doc must be present
        assert "custom_stacks" in text
