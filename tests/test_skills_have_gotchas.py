"""Lint: every SKILL.md must include a ## Gotchas section with real content.

Per memory #25 (Habr notes), every skill needs a "Подводные камни" section populated
from real experience. This lint prevents regression.
"""

from __future__ import annotations

import glob
import os


_SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "agents", "skills")


def _all_skill_files() -> list[str]:
    return sorted(glob.glob(os.path.join(_SKILLS_DIR, "*", "SKILL.md")))


def test_skills_directory_has_files():
    files = _all_skill_files()
    assert files, f"No SKILL.md files found under {_SKILLS_DIR}"


def test_every_skill_has_gotchas_section():
    missing = []
    for path in _all_skill_files():
        content = open(path, encoding="utf-8").read()
        if "\n## Gotchas" not in content and not content.startswith("## Gotchas"):
            missing.append(os.path.relpath(path, _SKILLS_DIR))
    assert not missing, f"SKILL.md files missing '## Gotchas' section: {missing}"


def test_gotchas_sections_are_not_empty():
    """A Gotchas section with no bullets is a smell — enforce real content."""
    empty = []
    for path in _all_skill_files():
        content = open(path, encoding="utf-8").read()
        idx = content.find("\n## Gotchas")
        if idx < 0:
            continue
        after = content[idx + len("\n## Gotchas") :].strip()
        # Must have at least one bullet or paragraph of content before next ## or EOF
        next_section = after.find("\n## ")
        section_body = after[
            : next_section if next_section >= 0 else len(after)
        ].strip()
        if len(section_body) < 30:
            empty.append(os.path.relpath(path, _SKILLS_DIR))
    assert not empty, f"SKILL.md files with too-thin '## Gotchas' (<30 chars): {empty}"
