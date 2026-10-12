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

from bootstrap_config import deployable_extension_skills, detect_extension_skills

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
        detected = set(detect_extension_skills(str(tmp_path)))
        assert "docs" in detected
        assert detected == {"docs"}

    @pytest.mark.parametrize(("available", "expected"), [(set(), []), ({"docs"}, ["docs"])])
    def test_detection_only_returns_deployable_skills(self, tmp_path, available, expected):
        (tmp_path / "docs").mkdir()
        assert detect_extension_skills(str(tmp_path), available_skills=available) == expected

    def test_official_skill_is_deployable_only_when_enabled(self, tmp_path):
        lib = tmp_path / "lib"
        store = lib / "skills-official"
        store.mkdir(parents=True)
        (store / "registry.json").write_text(
            json.dumps({"skills": {"docs": {"description": "Docs"}}}), encoding="utf-8"
        )
        assert "docs" not in deployable_extension_skills(str(lib))
        assert "docs" in deployable_extension_skills(str(lib), include_official=True)


@pytest.mark.parametrize(("active_manifest", "expected_syncs"), [(False, 0), (True, 1)])
def test_example_manifest_is_inert_until_explicitly_activated(
    tmp_path, monkeypatch, active_manifest, expected_syncs
):
    import bootstrap as subject

    lib = tmp_path / "lib"
    project = tmp_path / "project"
    lib.mkdir()
    project.mkdir()
    manifest = {"external_skills": {"sample": {"repo": "owner/repo", "ref": "v1"}}}
    (lib / "skills.example.json").write_text(json.dumps(manifest), encoding="utf-8")
    if active_manifest:
        (lib / "skills.json").write_text(json.dumps(manifest), encoding="utf-8")

    syncs = []
    monkeypatch.setattr(
        subject,
        "load_bootstrap_config",
        lambda *_args: ({"core_skills": [], "extension_skills": []}, {}),
    )
    monkeypatch.setattr(subject, "detect_stacks", lambda _project: [])
    monkeypatch.setattr(subject, "parse_strict_model_profile_env", lambda: None)
    monkeypatch.setattr(subject, "get_vendor_skill_dirs", lambda _vendor: {})
    monkeypatch.setattr(
        subject,
        "sync_deps",
        lambda *_args, **_kwargs: syncs.append(True) or {"sample": {"status": "synced"}},
    )

    class StopAfterVendorPolicy(Exception):
        pass

    monkeypatch.setattr(
        subject, "ensure_venv", lambda _tausik_dir: (_ for _ in ()).throw(StopAfterVendorPolicy)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bootstrap.py",
            "--lib-dir",
            str(lib),
            "--project-dir",
            str(project),
            "--ide",
            "claude",
            "--no-detect",
        ],
    )

    with pytest.raises(StopAfterVendorPolicy):
        subject.main()

    assert len(syncs) == expected_syncs
    assert (lib / "skills.json").exists() is active_manifest

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
        resolvable = _resolvable_skills()
        for skill in detect_extension_skills(str(tmp_path)):
            assert skill in resolvable, f"phantom skill recommended: {skill!r}"
