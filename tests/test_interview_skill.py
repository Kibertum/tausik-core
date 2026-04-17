"""Test /interview skill structure (Socratic Q&A, max 3 questions)."""

from __future__ import annotations

import os

_SKILL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "agents", "skills", "interview", "SKILL.md"
)


def test_skill_file_exists():
    assert os.path.exists(_SKILL_PATH), "interview SKILL.md must exist"


def test_skill_has_frontmatter():
    content = open(_SKILL_PATH, encoding="utf-8").read()
    assert content.startswith("---\n"), "frontmatter missing"
    assert "name: interview" in content


def test_max_3_questions_principle():
    content = open(_SKILL_PATH, encoding="utf-8").read().lower()
    # The max-3 principle must be literally stated
    assert "at most 3" in content or "max 3" in content or "maximum of 3" in content


def test_socratic_framing():
    content = open(_SKILL_PATH, encoding="utf-8").read().lower()
    assert "socratic" in content


def test_stop_condition_present():
    content = open(_SKILL_PATH, encoding="utf-8").read().lower()
    assert "when to skip" in content


def test_has_gotchas_section():
    content = open(_SKILL_PATH, encoding="utf-8").read()
    assert "## Gotchas" in content


def test_frontmatter_mentions_triggers():
    content = open(_SKILL_PATH, encoding="utf-8").read()
    # At least one Russian + English trigger
    assert "interview me" in content.lower()
    assert "уточни" in content or "задай вопрос" in content.lower()
