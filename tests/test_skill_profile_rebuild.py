"""Tests for scripts/skill_profile_rebuild.py — disk pre-merge with sha256 cache."""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import skill_profile_rebuild as spr  # noqa: E402


@pytest.fixture
def skills_root(tmp_path):
    """Build a fake skills root with one skill having ide+model overlays."""
    root = tmp_path / "skills"
    sa = root / "alpha"
    (sa / "variants" / "ide").mkdir(parents=True)
    (sa / "variants" / "model").mkdir(parents=True)
    (sa / "SKILL.md").write_text("# alpha base\n", encoding="utf-8")
    (sa / "variants" / "ide" / "claude.md").write_text("## ide-claude\n", encoding="utf-8")
    (sa / "variants" / "model" / "opus.md").write_text("## model-opus\n", encoding="utf-8")
    sb = root / "bravo"
    sb.mkdir()
    (sb / "SKILL.md").write_text("# bravo base only\n", encoding="utf-8")
    return str(root)


def test_rebuild_writes_when_overlay_present(skills_root):
    result = spr.rebuild_skills(skills_root, ide="claude", model="opus")
    assert "alpha" in result["rebuilt"]
    assert "bravo" in result["skipped"]
    assert result["errors"] == {}


def test_rebuild_idempotent_when_content_unchanged(skills_root):
    spr.rebuild_skills(skills_root, ide="claude", model="opus")
    result = spr.rebuild_skills(skills_root, ide="claude", model="opus")
    assert result["rebuilt"] == []
    assert sorted(result["skipped"]) == ["alpha", "bravo"]


def test_rebuild_force_always_rewrites(skills_root):
    spr.rebuild_skills(skills_root, ide="claude", model="opus")
    result = spr.rebuild_skills(skills_root, ide="claude", model="opus", force=True)
    assert "alpha" in result["rebuilt"]


def test_rebuild_missing_model_overlay_only_ide(skills_root):
    result = spr.rebuild_skills(skills_root, ide="claude", model="haiku")
    assert "alpha" in result["rebuilt"]
    merged = (open(os.path.join(skills_root, "alpha", "SKILL.md"), encoding="utf-8")).read()
    assert "ide-claude" in merged
    assert "model-opus" not in merged
    assert "model-haiku" not in merged


def test_rebuild_missing_ide_overlay_only_model(skills_root):
    result = spr.rebuild_skills(skills_root, ide="cursor", model="opus")
    assert "alpha" in result["rebuilt"]
    merged = (open(os.path.join(skills_root, "alpha", "SKILL.md"), encoding="utf-8")).read()
    assert "model-opus" in merged
    assert "ide-claude" not in merged
    assert "ide-cursor" not in merged


def test_rebuild_both_missing_keeps_base(skills_root):
    result = spr.rebuild_skills(skills_root, ide="cursor", model="haiku")
    # alpha base differs from existing (no overlays match), but in this case
    # base is "# alpha base\n" and merged with no overlays is "# alpha base\n"
    # — so should be skipped (idempotent).
    assert "alpha" in result["skipped"]


def test_rebuild_both_none_keeps_base(skills_root):
    result = spr.rebuild_skills(skills_root, ide=None, model=None)
    assert sorted(result["skipped"]) == ["alpha", "bravo"]
    assert result["rebuilt"] == []


def test_rebuild_empty_root_returns_empty(tmp_path):
    result = spr.rebuild_skills(str(tmp_path / "missing"), ide="claude", model="opus")
    assert result == {"rebuilt": [], "skipped": [], "errors": {}}


def test_rebuild_ignores_non_skill_directories(tmp_path):
    """A subdirectory without SKILL.md must be silently skipped, not crash."""
    root = tmp_path / "skills"
    (root / "fake").mkdir(parents=True)
    (root / "real").mkdir()
    (root / "real" / "SKILL.md").write_text("# real\n", encoding="utf-8")
    result = spr.rebuild_skills(str(root), ide=None, model=None)
    assert "fake" not in result["rebuilt"] + result["skipped"]
    assert "real" in result["skipped"]


def test_rebuild_handles_unreadable_skill_md(tmp_path, monkeypatch):
    """If reading existing SKILL.md fails, error is recorded; other skills proceed."""
    root = tmp_path / "skills"
    sa = root / "broken"
    sa.mkdir(parents=True)
    target = sa / "SKILL.md"
    target.write_text("# broken\n", encoding="utf-8")

    sb = root / "good"
    sb.mkdir()
    (sb / "SKILL.md").write_text("# good\n", encoding="utf-8")

    real_open = open

    def faulty_open(path, *a, **kw):
        if str(path).endswith(os.path.join("broken", "SKILL.md")) and "r" in (
            kw.get("mode") or "r"
        ):
            raise OSError("simulated read failure")
        return real_open(path, *a, **kw)

    monkeypatch.setattr("builtins.open", faulty_open)
    result = spr.rebuild_skills(str(root), ide=None, model=None)
    assert "broken" in result["errors"] or "broken" in result["skipped"]
    assert "good" in result["skipped"] or "good" in result["rebuilt"]


def test_rebuild_atomic_write(skills_root):
    """No .tmp file left behind after successful rebuild."""
    spr.rebuild_skills(skills_root, ide="claude", model="opus")
    assert not os.path.exists(os.path.join(skills_root, "alpha", "SKILL.md.tmp"))
