"""Unit tests for scripts/tausik_utils.py — pure stdlib helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from tausik_utils import tausik_config_path  # noqa: E402


def test_tausik_config_path_basic(tmp_path):
    expected = os.path.join(str(tmp_path), ".tausik", "config.json")
    assert tausik_config_path(str(tmp_path)) == expected


def test_tausik_config_path_idempotent(tmp_path):
    a = tausik_config_path(str(tmp_path))
    b = tausik_config_path(str(tmp_path))
    assert a == b


def test_tausik_config_path_relative_dir():
    out = tausik_config_path("some/relative/dir")
    assert out.endswith(os.path.join(".tausik", "config.json"))
    assert "some" in out and "relative" in out and "dir" in out


def test_no_inline_duplicates_in_production():
    """Regression guard: no production source should rebuild the config path
    inline. Only the helper itself, plus tests, may mention the literal.
    """
    import re

    pat = re.compile(r"""['\"]\.tausik['\"]\s*,\s*['\"]config\.json['\"]""")
    allow_dirs = {"tests", "_archive", "node_modules", ".git"}
    allow_files = {
        "tausik_utils.py",  # the helper definition
    }
    offenders: list[str] = []
    for base in ("scripts", "harness", "bootstrap"):
        root = ROOT / base
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            parts = set(p.parts)
            if parts & allow_dirs:
                continue
            if p.name in allow_files:
                continue
            if pat.search(p.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(p.relative_to(ROOT)))
    assert not offenders, (
        f"Inline `.tausik/config.json` rebuild found in production sources: "
        f"{offenders}. Use scripts/tausik_utils.tausik_config_path()."
    )


def test_start_skill_mentions_brain_ignored_filter():
    """v14b-review57-followups M1: the /start SKILL.md must keep the
    brain.ignored:<id> filter pointer so opt-in --brain primer skips
    suggestions the user already dismissed.
    """
    skill = ROOT / "harness" / "skills" / "start" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    assert "brain.ignored" in text, (
        "Filter pointer `brain.ignored:` missing from /start SKILL.md — "
        "agents will re-surface dismissed brain suggestions."
    )
