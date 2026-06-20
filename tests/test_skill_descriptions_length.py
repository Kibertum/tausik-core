"""Regression test for v14b-token-tier1-quick-wins T1.1.

Every harness/skills/*/SKILL.md description must be at most 60 characters
(target ~20 tokens). The cap saves ~760 tokens/turn across 14 skills
re-emitted on every model turn in the system prompt.

Trim further if needed, but never break trigger-phrase discoverability:
each description still mentions the skill name or a domain keyword so the
harness's natural-language matching keeps working.
"""

from __future__ import annotations

import os
import re

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SKILLS_DIR = os.path.join(_REPO_ROOT, "harness", "skills")
_DESC_RE = re.compile(r'^description:\s*"([^"]*)"\s*$', re.MULTILINE)
_MAX_CHARS = 60


def _all_skill_files() -> list[str]:
    paths = []
    for entry in os.listdir(_SKILLS_DIR):
        skill_path = os.path.join(_SKILLS_DIR, entry, "SKILL.md")
        if os.path.isfile(skill_path):
            paths.append(skill_path)
    return paths


def _extract_description(skill_md_path: str) -> str:
    with open(skill_md_path, "r", encoding="utf-8") as f:
        text = f.read()
    m = _DESC_RE.search(text)
    if not m:
        return ""
    return m.group(1)


@pytest.mark.parametrize("skill_path", _all_skill_files())
def test_skill_description_length(skill_path):
    desc = _extract_description(skill_path)
    assert desc, f"description missing or unparseable in {skill_path}"
    assert len(desc) <= _MAX_CHARS, (
        f"{os.path.basename(os.path.dirname(skill_path))}/SKILL.md description "
        f"is {len(desc)} chars; target ≤{_MAX_CHARS}. Current: {desc!r}"
    )


def test_at_least_one_skill_present():
    """Sanity check: parametrize fan-out must not silently skip everything."""
    files = _all_skill_files()
    assert len(files) >= 5, f"expected ≥5 skills under harness/skills/, found {len(files)}"


@pytest.mark.parametrize("skill_path", _all_skill_files())
def test_skill_description_contains_a_trigger_signal(skill_path):
    """NEGATIVE: trimmed descriptions must still carry SOME signal —
    skill name, command name, or a domain keyword. A description like
    "ok." would technically pass the length cap but break discoverability.
    """
    skill_name = os.path.basename(os.path.dirname(skill_path))
    desc = _extract_description(skill_path).lower()
    # The skill folder name is one trigger. Domain keywords are also OK
    # for skills with off-name folder slugs (none today, but defensive).
    domain_keywords = {
        "_profile-demo": ("variant", "reference", "skill"),
        "brain": ("brain", "knowledge"),
        "checkpoint": ("snapshot", "session", "handoff", "checkpoint"),
        "commit": ("commit", "git"),
        "debug": ("debug", "bug"),
        "end": ("session", "handoff", "end"),
        "explore": ("explore", "investigation", "senar"),
        "interview": ("q&a", "questions", "interview", "socratic"),
        "plan": ("plan", "task"),
        "review": ("review", "bugs"),
        "ship": ("ship", "review", "test", "commit"),
        "start": ("start", "session"),
        "task": ("task", "plan"),
        "test": ("test", "tests"),
    }
    expected = domain_keywords.get(skill_name, (skill_name,))
    assert any(word in desc for word in expected), (
        f"description for skill {skill_name!r} doesn't include any of "
        f"{expected!r} — discoverability may break. Current: {desc!r}"
    )
