"""tests/skill_profile: variant overlay + unknown-profile fallback."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_SCRIPTS = REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from skill_profile import merge_skill_markdown, normalize_profile_slug, resolve_variant_overlay  # noqa: E402


def test_normalize_profile_slug():
    assert normalize_profile_slug("  Codex ") == "codex"
    assert normalize_profile_slug("gpt-5.1") == "gpt-5-1"


def test_unknown_profile_returns_base_only(tmp_path):
    skill = tmp_path / "s"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n\nBASE\n", encoding="utf-8")
    (skill / "variants").mkdir()
    (skill / "variants" / "claude.md").write_text("CLAUDE\n", encoding="utf-8")
    merged = merge_skill_markdown(str(skill), "nonexistent-profile-xyz")
    assert "BASE" in merged
    assert "CLAUDE" not in merged
    assert "tausik-profile" not in merged


def test_fallback_to_claude_overlay(tmp_path):
    skill = tmp_path / "s"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: x\ndescription: y\nprofile_fallback: claude\n---\n\nBASE\n",
        encoding="utf-8",
    )
    (skill / "variants").mkdir()
    (skill / "variants" / "claude.md").write_text("FALL_CLAUDE\n", encoding="utf-8")
    merged = merge_skill_markdown(str(skill), "gpt")
    assert "BASE" in merged
    assert "FALL_CLAUDE" in merged
    assert "tausik-profile:claude" in merged


def test_direct_variant_no_fallback_needed(tmp_path):
    skill = tmp_path / "s"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n\nBASE\n", encoding="utf-8")
    (skill / "variants").mkdir()
    (skill / "variants" / "codex.md").write_text("CODEX_ONLY\n", encoding="utf-8")
    merged = merge_skill_markdown(str(skill), "codex")
    assert "CODEX_ONLY" in merged
    assert "tausik-profile:codex" in merged


def test_resolve_unknown_profile_falls_back_without_crash():
    """Unknown slug uses ``profile_fallback`` variant when present — no exception."""
    demo = REPO / "harness" / "skills" / "_profile-demo"
    if not (demo / "SKILL.md").is_file():
        return
    ov, slug = resolve_variant_overlay(str(demo), "totally-unknown-model-999")
    assert ov is not None and "Claude" in ov
    assert slug == "claude"
