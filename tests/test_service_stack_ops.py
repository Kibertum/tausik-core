"""Tests for service_stack_ops — stack show/lint/diff/scaffold."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import service_stack_ops as _ops


@pytest.fixture
def chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestStackShow:
    def test_known_builtin_returns_resolved_decl(self):
        out = _ops.stack_show("python")
        assert out["name"] == "python"
        assert out["source"] in ("builtin", "overridden")
        assert isinstance(out["detect"], list)
        assert isinstance(out["extensions"], list)
        assert isinstance(out["gates"], dict)

    def test_unknown_stack_raises_keyerror(self):
        with pytest.raises(KeyError):
            _ops.stack_show("totally-not-a-stack")


class TestStackLint:
    def test_no_user_dir_returns_empty(self, chdir_tmp):
        out = _ops.stack_lint()
        assert out == {"checked": 0, "failed": 0, "results": []}

    def test_valid_user_decl_passes(self, chdir_tmp):
        d = chdir_tmp / ".tausik" / "stacks" / "myrust"
        d.mkdir(parents=True)
        (d / "stack.json").write_text(
            json.dumps({"name": "myrust", "version": "0.1.0", "extensions": [".rs"]})
        )
        out = _ops.stack_lint()
        assert out["checked"] == 1
        assert out["failed"] == 0
        assert out["results"][0]["ok"] is True
        assert out["results"][0]["stack"] == "myrust"

    def test_invalid_json_marks_failed(self, chdir_tmp):
        d = chdir_tmp / ".tausik" / "stacks" / "broken"
        d.mkdir(parents=True)
        (d / "stack.json").write_text("{not json")
        out = _ops.stack_lint()
        assert out["checked"] == 1
        assert out["failed"] == 1
        assert out["results"][0]["ok"] is False

    def test_skips_dotfiles_and_underscored(self, chdir_tmp):
        root = chdir_tmp / ".tausik" / "stacks"
        (root / ".hidden").mkdir(parents=True)
        (root / "_template").mkdir(parents=True)
        (root / "_template" / "stack.json").write_text("{}")
        out = _ops.stack_lint()
        assert out["checked"] == 0


class TestStackDiff:
    def test_no_user_override_returns_empty_diff(self, chdir_tmp):
        out = _ops.stack_diff("python")
        assert out["stack"] == "python"
        assert out["has_builtin"] is True
        assert out["has_user"] is False
        assert out["diff"] == ""

    def test_user_override_produces_diff(self, chdir_tmp):
        d = chdir_tmp / ".tausik" / "stacks" / "python"
        d.mkdir(parents=True)
        (d / "stack.json").write_text(
            json.dumps({"name": "python", "version": "9.9.9"}, indent=2) + "\n"
        )
        out = _ops.stack_diff("python")
        assert out["has_user"] is True
        assert "9.9.9" in out["diff"]


class TestStackScaffold:
    def test_creates_skeleton_files(self, chdir_tmp):
        out = _ops.stack_scaffold("ruby")
        assert os.path.isfile(out["created"][0])
        assert os.path.isfile(out["created"][1])
        decl = json.loads(open(out["created"][0]).read())
        assert decl["name"] == "ruby"
        assert decl["version"] == "0.1.0"
        assert "extends" not in decl

    def test_extends_builtin_sets_field(self, chdir_tmp):
        out = _ops.stack_scaffold("myfast", extends_builtin="fastapi")
        decl = json.loads(open(out["created"][0]).read())
        assert decl["extends"] == "builtin:fastapi"

    def test_refuses_overwrite_without_force(self, chdir_tmp):
        _ops.stack_scaffold("once")
        with pytest.raises(FileExistsError):
            _ops.stack_scaffold("once")

    def test_force_overwrites(self, chdir_tmp):
        _ops.stack_scaffold("twice")
        out = _ops.stack_scaffold("twice", force=True)
        assert len(out["existed"]) == 2

    def test_guide_md_contains_stack_name(self, chdir_tmp):
        out = _ops.stack_scaffold("named")
        guide = open(out["created"][1]).read()
        assert "named" in guide
