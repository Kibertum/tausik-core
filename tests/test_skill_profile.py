"""tests/skill_profile: variant overlay + unknown-profile fallback."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

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


def test_resolve_unknown_profile_returns_none_when_flat_layout_absent():
    """After B8-pre migration to variants/{ide,model}/, the legacy flat
    resolver returns None for _profile-demo (which moved to ide/ subdir)."""
    demo = REPO / "harness" / "skills" / "_profile-demo"
    if not (demo / "SKILL.md").is_file():
        return
    ov, slug = resolve_variant_overlay(str(demo), "totally-unknown-model-999")
    assert ov is None
    assert slug == ""


# --- Two-axis merge (B8-pre) -----------------------------------------------


def _make_skill(tmp_path, base="BASE\n", ide_overlay=None, model_overlay=None):
    """Build a skill dir with optional ide/model overlays under variants/."""
    skill = tmp_path / "s"
    skill.mkdir()
    (skill / "SKILL.md").write_text(base, encoding="utf-8")
    if ide_overlay is not None:
        (skill / "variants" / "ide").mkdir(parents=True)
        for name, content in ide_overlay.items():
            (skill / "variants" / "ide" / f"{name}.md").write_text(content, encoding="utf-8")
    if model_overlay is not None:
        (skill / "variants" / "model").mkdir(parents=True)
        for name, content in model_overlay.items():
            (skill / "variants" / "model" / f"{name}.md").write_text(content, encoding="utf-8")
    return str(skill)


def test_two_axis_base_plus_ide_plus_model(tmp_path):
    skill = _make_skill(
        tmp_path,
        ide_overlay={"claude": "IDE_CLAUDE\n"},
        model_overlay={"opus": "MODEL_OPUS\n"},
    )
    merged = merge_skill_markdown(skill, ide="claude", model="opus")
    assert "BASE" in merged
    assert "IDE_CLAUDE" in merged
    assert "MODEL_OPUS" in merged
    # IDE before model
    assert merged.index("IDE_CLAUDE") < merged.index("MODEL_OPUS")


def test_two_axis_base_plus_ide_only(tmp_path):
    skill = _make_skill(
        tmp_path,
        ide_overlay={"claude": "IDE_CLAUDE\n"},
        model_overlay={"opus": "MODEL_OPUS\n"},
    )
    merged = merge_skill_markdown(skill, ide="claude", model="haiku")
    assert "IDE_CLAUDE" in merged
    assert "MODEL_OPUS" not in merged
    assert "haiku" not in merged


def test_two_axis_base_plus_model_only(tmp_path):
    skill = _make_skill(
        tmp_path,
        ide_overlay={"claude": "IDE_CLAUDE\n"},
        model_overlay={"opus": "MODEL_OPUS\n"},
    )
    merged = merge_skill_markdown(skill, ide="cursor", model="opus")
    assert "MODEL_OPUS" in merged
    assert "IDE_CLAUDE" not in merged


def test_two_axis_both_unknown_returns_base(tmp_path):
    skill = _make_skill(
        tmp_path,
        ide_overlay={"claude": "IDE_CLAUDE\n"},
        model_overlay={"opus": "MODEL_OPUS\n"},
    )
    merged = merge_skill_markdown(skill, ide="cursor", model="haiku")
    assert "BASE" in merged
    assert "IDE_CLAUDE" not in merged
    assert "MODEL_OPUS" not in merged


def test_backward_compat_flat_layout_still_works(tmp_path):
    """Pass requested_profile (single slug) — legacy flat path resolves."""
    skill = tmp_path / "s"
    skill.mkdir()
    (skill / "SKILL.md").write_text("BASE\n", encoding="utf-8")
    (skill / "variants").mkdir()
    (skill / "variants" / "sonnet.md").write_text("FLAT_SONNET\n", encoding="utf-8")
    merged = merge_skill_markdown(str(skill), "sonnet")
    assert "FLAT_SONNET" in merged


@pytest.mark.parametrize("skill_name", ["plan", "task", "ship"])
@pytest.mark.parametrize("model_slug", ["gpt-4", "gpt-5", "gpt-5-5"])
def test_gpt_overlays_resolve_for_each_skill(skill_name: str, model_slug: str):
    """Each /plan, /task, /ship has variants/model/{gpt-4,gpt-5,gpt-5-5}.md
    that merge_skill_markdown picks up under the two-axis layout."""
    skill_dir = REPO / "harness" / "skills" / skill_name
    if not (skill_dir / "SKILL.md").is_file():
        pytest.skip(f"skill {skill_name} missing in this checkout")
    overlay = skill_dir / "variants" / "model" / f"{model_slug}.md"
    assert overlay.is_file(), f"missing {overlay}"
    merged = merge_skill_markdown(str(skill_dir), ide=None, model=model_slug)
    overlay_text = overlay.read_text(encoding="utf-8").strip()
    assert overlay_text in merged
    base = (skill_dir / "SKILL.md").read_text(encoding="utf-8").strip()
    base_first_line = base.splitlines()[0]
    assert base_first_line in merged


def test_unknown_gpt_profile_returns_base_only(tmp_path):
    """Unknown 'gpt-99' is silently no-op: base only, no exception."""
    skill_dir = REPO / "harness" / "skills" / "plan"
    if not (skill_dir / "SKILL.md").is_file():
        pytest.skip("plan skill missing")
    merged = merge_skill_markdown(str(skill_dir), ide=None, model="gpt-99")
    assert "gpt-99" not in merged
    base_first_line = (skill_dir / "SKILL.md").read_text(encoding="utf-8").splitlines()[0]
    assert base_first_line in merged


def test_gpt_5_5_dot_normalizes_to_hyphen():
    """`gpt-5.5` (with dot) normalizes to `gpt-5-5` and resolves the overlay."""
    skill_dir = REPO / "harness" / "skills" / "plan"
    if not (skill_dir / "SKILL.md").is_file():
        pytest.skip("plan skill missing")
    overlay = skill_dir / "variants" / "model" / "gpt-5-5.md"
    if not overlay.is_file():
        pytest.skip("gpt-5-5 overlay missing")
    merged = merge_skill_markdown(str(skill_dir), ide=None, model="gpt-5.5")
    assert overlay.read_text(encoding="utf-8").strip() in merged


def test_overlay_strip_is_idempotent(tmp_path):
    """Re-merging an already-merged SKILL.md does NOT accumulate overlays."""
    skill = _make_skill(
        tmp_path,
        ide_overlay={"claude": "IDE_CLAUDE\n"},
        model_overlay={"opus": "MODEL_OPUS\n"},
    )
    first = merge_skill_markdown(skill, ide="claude", model="opus")
    (open(f"{skill}/SKILL.md", "w", encoding="utf-8")).write(first)
    second = merge_skill_markdown(skill, ide="claude", model="opus")
    assert first == second
    assert second.count("IDE_CLAUDE") == 1
    assert second.count("MODEL_OPUS") == 1
