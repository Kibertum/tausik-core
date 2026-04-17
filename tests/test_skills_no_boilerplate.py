"""Lint: SKILL.md files must not duplicate CLAUDE.md boilerplate.

Post skills-redundancy-audit: content that already lives in the generated CLAUDE.md
(hard constraints, "respond in user's language", generic MCP-first reminder) should
not be repeated per-skill. Each duplication wastes tokens on every skill invocation.
"""

from __future__ import annotations

import glob
import os


_SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "agents", "skills")

REDUNDANT_PHRASES = (
    "always respond in the user's language",
    "always respond in the user's language.",
)


def test_no_redundant_language_instruction():
    """Remove 'Always respond in the user's language' from skills; CLAUDE.md covers it."""
    offenders = []
    for path in sorted(glob.glob(os.path.join(_SKILLS_DIR, "*", "SKILL.md"))):
        content = open(path, encoding="utf-8").read().lower()
        for phrase in REDUNDANT_PHRASES:
            if phrase in content:
                offenders.append(
                    f"{os.path.relpath(path, _SKILLS_DIR)}: contains '{phrase}'"
                )
                break
    assert not offenders, (
        "The following SKILL.md files duplicate CLAUDE.md language rule:\n"
        + "\n".join(offenders)
    )
