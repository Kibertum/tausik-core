"""Tests for bootstrap_copy.copy_aidd_templates — AIDD template bundling."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from bootstrap_copy import copy_aidd_templates  # noqa: E402


def _make_lib(tmp_path):
    src = tmp_path / "lib" / "harness" / "aidd-templates"
    src.mkdir(parents=True)
    for f in ("idea.md", "vision.md", "conventions.md"):
        (src / f).write_text(f"# {f}\n", encoding="utf-8")
    return str(tmp_path / "lib")


class TestCopyAiddTemplates:
    def test_copies_all_templates(self, tmp_path):
        lib = _make_lib(tmp_path)
        target = str(tmp_path / "target")
        n = copy_aidd_templates(lib, target)
        assert n == 3
        dst = os.path.join(target, "harness", "aidd-templates")
        for f in ("idea.md", "vision.md", "conventions.md"):
            assert os.path.isfile(os.path.join(dst, f))

    def test_missing_source_returns_zero(self, tmp_path):
        empty_lib = str(tmp_path / "empty")
        os.makedirs(empty_lib)
        assert copy_aidd_templates(empty_lib, str(tmp_path / "target")) == 0
