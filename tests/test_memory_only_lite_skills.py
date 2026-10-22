"""memory-only Cursor lite skills: tausik-memory in, SENAR session rituals out."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bootstrap"))
sys.path.insert(0, str(ROOT / "scripts"))

from bootstrap_copy import MEMORY_ONLY_EXCLUDED_SKILLS, copy_skills  # noqa: E402


@pytest.fixture()
def lib_dir(tmp_path: Path) -> Path:
    """Minimal harness/skills tree: rituals + playbook + one keepable skill."""
    skills = tmp_path / "harness" / "skills"
    for name in ("start", "end", "checkpoint", "tausik-memory", "explore"):
        d = skills / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: test\n---\n# {name}\n",
            encoding="utf-8",
        )
    return tmp_path


def test_memory_only_deploys_playbook_and_drops_session_rituals(lib_dir: Path, tmp_path: Path):
    target = tmp_path / ".cursor"
    target.mkdir()
    n = copy_skills(
        str(lib_dir),
        str(target),
        {},
        "cursor",
        governance_profile="memory-only",
    )
    deployed = {p.name for p in (target / "skills").iterdir() if p.is_dir()}
    assert n >= 2
    assert "tausik-memory" in deployed
    assert (target / "skills" / "tausik-memory" / "SKILL.md").is_file()
    assert MEMORY_ONLY_EXCLUDED_SKILLS.isdisjoint(deployed)
    assert "explore" in deployed


def test_full_profile_still_gets_session_rituals(lib_dir: Path, tmp_path: Path):
    target = tmp_path / ".cursor"
    target.mkdir()
    copy_skills(str(lib_dir), str(target), {}, "cursor", governance_profile="full")
    deployed = {p.name for p in (target / "skills").iterdir() if p.is_dir()}
    assert MEMORY_ONLY_EXCLUDED_SKILLS.issubset(deployed)
    assert "tausik-memory" in deployed


def test_status_memory_only_never_nudges_full_skill_bootstrap(tmp_path: Path):
    from status_view import render_status_cli

    view = {
        "governance_profile": "memory-only",
        "data": {"task_counts": {"done": 1, "planning": 0}},
        "epics_count": 0,
        "skill_warning": (
            "Skills: 20 deployed (v1.4 default = 12 core + 1 conditional). "
            "Re-bootstrap to shrink: `python bootstrap/bootstrap.py --ide claude`"
        ),
    }
    text = render_status_cli(view)
    assert "canon B" in text
    assert "Re-bootstrap" not in text
    assert "bootstrap.py" not in text
