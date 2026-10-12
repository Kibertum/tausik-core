"""Test skill frontmatter parsing and validation in bootstrap.

Run: pytest tests/test_bootstrap_frontmatter.py -v
"""

from __future__ import annotations

import os
import sys


# Add bootstrap dir to path
_bootstrap_dir = os.path.join(os.path.dirname(__file__), "..", "bootstrap")
sys.path.insert(0, _bootstrap_dir)

import pytest

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

    @pytest.mark.parametrize(
        "fields",
        [
            pytest.param({"context": "inline"}, id="valid_context_inline"),
            pytest.param({"context": "fork"}, id="valid_context_fork"),
            pytest.param({"paths": "src/**"}, id="valid_paths"),
        ],
    )
    def test_valid_fields_no_warnings(self, fields):
        assert validate_skill_frontmatter("s", fields) == []

    @pytest.mark.parametrize(
        "fields,expected_phrase",
        [
            pytest.param({"context": "parallel"}, "invalid context", id="invalid_context"),
            pytest.param({"effort": "turbo"}, "invalid effort", id="invalid_effort"),
            pytest.param({"paths": ""}, "empty", id="empty_paths_warning"),
        ],
    )
    def test_invalid_fields_warn(self, fields, expected_phrase):
        warnings = validate_skill_frontmatter("s", fields)
        assert len(warnings) == 1
        assert expected_phrase in warnings[0]

    def test_valid_efforts(self):
        for effort in ("fast", "medium", "slow"):
            assert validate_skill_frontmatter("s", {"effort": effort}) == []

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
