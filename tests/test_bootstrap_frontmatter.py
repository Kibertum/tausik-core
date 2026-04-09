"""Test skill frontmatter parsing and validation in bootstrap.

Run: pytest tests/test_bootstrap_frontmatter.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

# Add bootstrap dir to path
_bootstrap_dir = os.path.join(os.path.dirname(__file__), "..", "bootstrap")
sys.path.insert(0, _bootstrap_dir)

from bootstrap_copy import parse_skill_frontmatter, validate_skill_frontmatter


class TestParseFrontmatter:
    """Test YAML frontmatter parsing from SKILL.md files."""

    def test_basic_frontmatter(self, tmp_path):
        md = tmp_path / "SKILL.md"
        md.write_text('---\nname: test\ndescription: "A test skill"\n---\n# Body\n')
        fields = parse_skill_frontmatter(str(md))
        assert fields is not None
        assert fields["name"] == "test"
        assert fields["description"] == "A test skill"

    def test_new_fields_parsed(self, tmp_path):
        md = tmp_path / "SKILL.md"
        md.write_text(
            '---\nname: review\ndescription: "Review"\n'
            'context: fork\neffort: slow\npaths: "src/**,tests/**"\n---\n'
        )
        fields = parse_skill_frontmatter(str(md))
        assert fields is not None
        assert fields["context"] == "fork"
        assert fields["effort"] == "slow"
        assert fields["paths"] == "src/**,tests/**"

    def test_no_frontmatter(self, tmp_path):
        md = tmp_path / "SKILL.md"
        md.write_text("# Just a heading\nNo frontmatter here.\n")
        assert parse_skill_frontmatter(str(md)) is None

    def test_missing_file(self, tmp_path):
        assert parse_skill_frontmatter(str(tmp_path / "nonexistent.md")) is None

    def test_backward_compatible_no_new_fields(self, tmp_path):
        """Skills without new fields parse correctly (backward compat)."""
        md = tmp_path / "SKILL.md"
        md.write_text('---\nname: old-skill\ndescription: "Old"\n---\n')
        fields = parse_skill_frontmatter(str(md))
        assert fields is not None
        assert "context" not in fields
        assert "effort" not in fields
        assert "paths" not in fields


class TestValidateFrontmatter:
    """Test frontmatter validation warnings."""

    def test_valid_context_inline(self):
        assert validate_skill_frontmatter("s", {"context": "inline"}) == []

    def test_valid_context_fork(self):
        assert validate_skill_frontmatter("s", {"context": "fork"}) == []

    def test_invalid_context(self):
        warnings = validate_skill_frontmatter("s", {"context": "parallel"})
        assert len(warnings) == 1
        assert "invalid context" in warnings[0]

    def test_valid_efforts(self):
        for effort in ("fast", "medium", "slow"):
            assert validate_skill_frontmatter("s", {"effort": effort}) == []

    def test_invalid_effort(self):
        warnings = validate_skill_frontmatter("s", {"effort": "turbo"})
        assert len(warnings) == 1
        assert "invalid effort" in warnings[0]

    def test_empty_paths_warning(self):
        warnings = validate_skill_frontmatter("s", {"paths": ""})
        assert len(warnings) == 1
        assert "empty" in warnings[0]

    def test_valid_paths(self):
        assert validate_skill_frontmatter("s", {"paths": "src/**"}) == []

    def test_no_new_fields_no_warnings(self):
        """Old-style frontmatter with only name/description produces no warnings."""
        assert validate_skill_frontmatter("s", {"name": "x", "description": "y"}) == []

    def test_multiple_invalid_fields(self):
        warnings = validate_skill_frontmatter(
            "s",
            {
                "context": "bad",
                "effort": "bad",
                "paths": "",
            },
        )
        assert len(warnings) == 3
