"""Tests for scripts/skill_spec_conformance.py (l26-skill-spec-conformance).

AC coverage:
  2. every shipped skill conforms to the agentskills.io name/description canon.
  3. the gate FAILS on a deliberately broken skill and is silent on valid ones
     (fails-then-passes), and is inert when no SKILL.md changed.
  + the validator is git-independent and never raises on a malformed skill.
"""

from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from skill_spec_conformance import (  # noqa: E402
    is_publishable_skill_dir,
    run_skill_conformance_gate,
    scan_skills,
    validate_skill,
    validate_skill_fields,
)

_SKILLS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "harness", "skills"))


def _write_skill(tmp_path, dir_name, name, description, extra=""):
    d = tmp_path / dir_name
    d.mkdir()
    fm = f"---\nname: {name}\ndescription: {description}\n{extra}---\n\n# body\n"
    (d / "SKILL.md").write_text(fm, encoding="utf-8")
    return str(d)


# ----------------------------------------------- AC2: shipped skills conform ---


def test_all_shipped_skills_conform():
    report = scan_skills(_SKILLS_ROOT)
    assert report, "no skills discovered — path wrong?"
    offenders = {name: probs for name, probs in report.items() if probs}
    assert not offenders, f"non-conformant skills: {offenders}"


def test_scaffold_dirs_are_skipped():
    # _profile-demo has name 'profile-demo' != its '_' dir, but is a non-deployed
    # reference and must be excluded rather than flagged.
    assert not is_publishable_skill_dir(os.path.join(_SKILLS_ROOT, "_profile-demo"))
    assert "_profile-demo" not in scan_skills(_SKILLS_ROOT)


# --------------------------------------------------- pure field rules ---


class TestFieldRules:
    def test_valid_triple_is_clean(self):
        assert validate_skill_fields("plan", "Plan a task.", "plan") == []

    def test_name_must_match_dir(self):
        probs = validate_skill_fields("plan", "d", "planning")
        assert any("must equal parent directory" in p for p in probs)

    def test_uppercase_and_underscore_rejected(self):
        assert validate_skill_fields("Plan", "d", "Plan")  # uppercase
        assert validate_skill_fields("my_skill", "d", "my_skill")  # underscore

    def test_doubled_and_edge_hyphens_rejected(self):
        assert any("doubled hyphen" in p for p in validate_skill_fields("a--b", "d", "a--b"))
        assert validate_skill_fields("-lead", "d", "-lead")
        assert validate_skill_fields("trail-", "d", "trail-")

    def test_length_bounds(self):
        assert validate_skill_fields("a" * 65, "d", "a" * 65)  # name too long
        assert validate_skill_fields("ok", "", "ok")  # empty description
        assert validate_skill_fields("ok", "x" * 1025, "ok")  # description too long

    def test_boundary_lengths_are_ok(self):
        assert validate_skill_fields("a" * 64, "x" * 1024, "a" * 64) == []


# ----------------------------------------- validator on disk (never raises) ---


class TestValidateSkill:
    def test_valid_skill_dir_clean(self, tmp_path):
        d = _write_skill(tmp_path, "good-skill", "good-skill", '"A good skill."')
        assert validate_skill(d) == []

    def test_name_dir_mismatch_flagged(self, tmp_path):
        d = _write_skill(tmp_path, "dirname", "othername", "d")
        assert any("must equal parent directory" in p for p in validate_skill(d))

    def test_malformed_frontmatter_does_not_raise(self, tmp_path):
        d = tmp_path / "weird"
        d.mkdir()
        (d / "SKILL.md").write_text("no frontmatter here\njust text\n", encoding="utf-8")
        probs = validate_skill(str(d))  # must not raise
        assert any("name" in p for p in probs)  # missing name reported


# ----------------------------------------------------------- AC3: the gate ---


class TestGate:
    def test_gate_fails_on_broken_skill(self, tmp_path):
        d = _write_skill(tmp_path, "Bad_Name", "Bad_Name", "d")
        ok, msg = run_skill_conformance_gate({}, [os.path.join(d, "SKILL.md")])
        assert ok is False
        assert "violation" in msg.lower()

    def test_gate_passes_on_valid_skill(self, tmp_path):
        d = _write_skill(tmp_path, "fine-skill", "fine-skill", '"ok"')
        ok, msg = run_skill_conformance_gate({}, [os.path.join(d, "SKILL.md")])
        assert ok is True
        assert "conform" in msg.lower()

    def test_gate_inert_when_no_skill_changed(self):
        ok, msg = run_skill_conformance_gate({}, ["scripts/foo.py", "docs/x.md"])
        assert ok is True
        assert "skipped" in msg.lower()

    def test_gate_recognises_backslash_paths(self, tmp_path):
        d = _write_skill(tmp_path, "win-skill", "win-skill", "d")
        winpath = os.path.join(d, "SKILL.md").replace("/", "\\")
        ok, _ = run_skill_conformance_gate({}, [winpath])
        assert ok is True

    def test_gate_validates_the_right_dir_from_a_backslash_path(self, tmp_path):
        """Review fix (HIGH): dirname must come from the NORMALIZED path. On POSIX,
        a backslash path used to collapse to '.', validating the wrong directory.
        A broken skill via a backslash path must fail with the NAME violation
        (proving its real dir was read), not an 'unreadable' one."""
        d = _write_skill(tmp_path, "dirname", "othername", "d")
        winpath = os.path.join(d, "SKILL.md").replace("/", "\\")
        ok, msg = run_skill_conformance_gate({}, [winpath])
        assert ok is False
        assert "parent directory" in msg
