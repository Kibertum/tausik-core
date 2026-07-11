"""Regression tests for bootstrap extension-skill detection.

Guards against phantom skills — a detector recommending a skill that has no
source in the official registry or built-in set (the 'skills not found: diff'
defect, v15p-fix-bootstrap-diff-skill-warn).
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

from bootstrap_config import detect_extension_skills  # noqa: E402

_REPO = os.path.join(os.path.dirname(__file__), "..")


def _resolvable_skills() -> set[str]:
    """Official-registry skills ∪ built-in harness/skills/ directories."""
    names: set[str] = set()
    reg = os.path.join(_REPO, "skills-official", "registry.json")
    if os.path.isfile(reg):
        with open(reg, encoding="utf-8") as f:
            names |= set(json.load(f).get("skills", {}))
    builtin = os.path.join(_REPO, "harness", "skills")
    if os.path.isdir(builtin):
        names |= {
            d
            for d in os.listdir(builtin)
            if os.path.isdir(os.path.join(builtin, d)) and not d.startswith((".", "_"))
        }
    return names


class TestDetectExtensionSkills:
    def test_git_repo_does_not_recommend_diff(self, tmp_path):
        # The defect: a .git repo triggered a phantom 'diff' recommendation.
        (tmp_path / ".git").mkdir()
        assert "diff" not in detect_extension_skills(str(tmp_path))

    def test_detects_real_skills(self, tmp_path):
        (tmp_path / "docs").mkdir()
        (tmp_path / ".env").write_text("X=1", encoding="utf-8")
        detected = set(detect_extension_skills(str(tmp_path)))
        assert "docs" in detected
        assert "security" in detected

    def test_no_recommendation_is_a_phantom(self, tmp_path):
        # Every skill the detector can output MUST resolve to a real source,
        # else bootstrap warns 'skills not found'. This is the regression guard.
        #
        # It can only be evaluated where the official registry exists.
        # `skills-official/` is gitignored (.gitignore:44), so a fresh clone — a
        # CI checkout, for instance — has only `harness/skills/`, and the detector's
        # perfectly legitimate 'docs' recommendation looks like a phantom. Skipping
        # is honest; asserting against half the sources is not.
        if not os.path.isfile(os.path.join(_REPO, "skills-official", "registry.json")):
            pytest.skip("skills-official/ is gitignored and absent; resolvable set is partial")
        (tmp_path / ".git").mkdir()
        (tmp_path / "docs").mkdir()
        (tmp_path / ".env").write_text("X=1", encoding="utf-8")
        resolvable = _resolvable_skills()
        for skill in detect_extension_skills(str(tmp_path)):
            assert skill in resolvable, f"phantom skill recommended: {skill!r}"
