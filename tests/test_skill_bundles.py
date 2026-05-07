"""Tests for scripts/skill_bundles.py + skills-official/bundles.json
(v14b-skill-bundles-marketplace).

Pins:
- bundles.json schema validity + cross-ref to skills-official/<name>/
- registry.json no longer contains the 5 deprecated skills
- Service API: load, list, show, install (with mock), uninstall (with mock)
- Negative paths: missing manifest, unknown bundle, deprecated-skill skip,
  placeholder bundle no-op, install-error continuation
"""

from __future__ import annotations

import json
import os
import sys

import pytest

REPO = os.path.join(os.path.dirname(__file__), "..")
SKILLS_OFFICIAL = os.path.join(REPO, "skills-official")
BUNDLES_PATH = os.path.join(SKILLS_OFFICIAL, "bundles.json")
REGISTRY_PATH = os.path.join(SKILLS_OFFICIAL, "registry.json")

# skills-official/ lives in a separate repo (Kibertum/tausik-skills) and is in
# .gitignore here. CI clones tausik-core without it; only local dev with the
# vendored skills tree runs these checks. See docs/en/skill-bundles.md.
if not os.path.isfile(BUNDLES_PATH):
    pytest.skip(
        "skills-official/bundles.json absent — skill_bundles tests are local-only "
        "(skills-official/ is in .gitignore; clone github.com/Kibertum/tausik-skills "
        "into skills-official/ to run these locally)",
        allow_module_level=True,
    )

sys.path.insert(0, os.path.join(REPO, "scripts"))

import skill_bundles  # noqa: E402

DEPRECATED_NAMES = {"go", "next", "diff", "onboard", "init"}


# --- Real-manifest invariants ----------------------------------------------


def test_bundles_json_valid_and_present():
    assert os.path.isfile(BUNDLES_PATH)
    manifest = skill_bundles.load_bundles_manifest(SKILLS_OFFICIAL)
    assert manifest.get("version") == 1
    assert "bundles" in manifest


def test_six_bundles_with_expected_names():
    manifest = skill_bundles.load_bundles_manifest(SKILLS_OFFICIAL)
    expected = {
        "integrations",
        "data-formats",
        "quality-pro",
        "automation",
        "workflow-helpers",
        "ru-locale",
    }
    assert set(manifest["bundles"].keys()) == expected


def test_bundle_skills_reference_existing_dirs():
    """Every skill in any bundle must have a real skills-official/<name>/ dir."""
    manifest = skill_bundles.load_bundles_manifest(SKILLS_OFFICIAL)
    for bundle_name, body in manifest["bundles"].items():
        for skill in body.get("skills") or []:
            skill_dir = os.path.join(SKILLS_OFFICIAL, skill)
            assert os.path.isdir(skill_dir), (
                f"bundle {bundle_name!r} references missing skill dir {skill_dir}"
            )
            assert os.path.isfile(os.path.join(skill_dir, "SKILL.md"))


def test_ru_locale_is_placeholder():
    body = skill_bundles.bundle_show("ru-locale", SKILLS_OFFICIAL)
    assert body["placeholder"] is True
    assert body["skills"] == []


def test_registry_no_deprecated_entries():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        reg = json.load(f)
    for dep in DEPRECATED_NAMES:
        assert dep not in reg["skills"], f"deprecated skill {dep!r} still in registry.json"


def test_deprecated_skill_dirs_removed():
    for dep in DEPRECATED_NAMES:
        skill_dir = os.path.join(SKILLS_OFFICIAL, dep)
        assert not os.path.isdir(skill_dir), (
            f"deprecated skill dir {skill_dir} still exists — should be deleted"
        )


def test_bundle_skill_count_matches_registry_minus_deprecated():
    """Sum of skills across populated bundles equals non-deprecated registry count."""
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        reg = json.load(f)
    manifest = skill_bundles.load_bundles_manifest(SKILLS_OFFICIAL)
    bundle_skills = sum(len(b.get("skills") or []) for b in manifest["bundles"].values())
    assert bundle_skills == len(reg["skills"]), (
        f"bundles cover {bundle_skills} skills but registry has {len(reg['skills'])} "
        f"non-deprecated skills — drift between bundles.json and registry.json"
    )


def test_deprecation_messages_present():
    manifest = skill_bundles.load_bundles_manifest(SKILLS_OFFICIAL)
    dep = skill_bundles.deprecated_skills(manifest)
    for name in DEPRECATED_NAMES:
        assert name in dep
        assert isinstance(dep[name], str) and len(dep[name]) > 10


# --- Synthetic-manifest unit tests -----------------------------------------


@pytest.fixture
def fake_manifest_dir(tmp_path):
    """Build a tmp skills-official/ with a fake bundles.json."""
    body = {
        "version": 1,
        "bundles": {
            "alpha": {
                "title": "Alpha",
                "description": "two real skills",
                "skills": ["skill_a", "skill_b"],
            },
            "with-deprecated": {
                "title": "WD",
                "skills": ["skill_a", "old_skill"],
            },
            "empty-placeholder": {
                "title": "Empty",
                "skills": [],
                "placeholder": True,
            },
        },
        "deprecated": {
            "old_skill": "use the new flow instead.",
        },
    }
    (tmp_path / "bundles.json").write_text(json.dumps(body), encoding="utf-8")
    for name in ("skill_a", "skill_b"):
        d = tmp_path / name
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: " + name + "\n---\n", encoding="utf-8")
    return str(tmp_path)


def test_load_missing_manifest_raises_clean_error(tmp_path):
    with pytest.raises(skill_bundles.BundleError, match="No bundles manifest"):
        skill_bundles.load_bundles_manifest(str(tmp_path))


def test_load_malformed_json_raises(tmp_path):
    (tmp_path / "bundles.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(skill_bundles.BundleError, match="Cannot parse"):
        skill_bundles.load_bundles_manifest(str(tmp_path))


def test_load_missing_bundles_key_raises(tmp_path):
    (tmp_path / "bundles.json").write_text(json.dumps({"version": 1}), encoding="utf-8")
    with pytest.raises(skill_bundles.BundleError, match="bundles"):
        skill_bundles.load_bundles_manifest(str(tmp_path))


def test_show_unknown_bundle_raises(fake_manifest_dir):
    with pytest.raises(skill_bundles.BundleError, match="Unknown bundle"):
        skill_bundles.bundle_show("nope", fake_manifest_dir)


def test_install_routes_through_callback(fake_manifest_dir):
    calls: list[str] = []

    def install_one(name: str) -> str:
        calls.append(name)
        return f"installed {name}"

    results = skill_bundles.bundle_install("alpha", fake_manifest_dir, install_one)
    assert calls == ["skill_a", "skill_b"]
    assert all(r["status"] == "installed" for r in results)
    assert results[0]["skill"] == "skill_a"


def test_install_skips_deprecated_skill_with_message(fake_manifest_dir):
    calls: list[str] = []

    def install_one(name: str) -> str:
        calls.append(name)
        return "installed"

    results = skill_bundles.bundle_install("with-deprecated", fake_manifest_dir, install_one)
    # skill_a is installed, old_skill is skipped (in deprecated map).
    assert "old_skill" not in calls
    assert calls == ["skill_a"]
    statuses = [r["status"] for r in results]
    assert "installed" in statuses
    assert "deprecated_skipped" in statuses
    skipped = [r for r in results if r["status"] == "deprecated_skipped"][0]
    assert "use the new flow" in skipped["message"]


def test_install_continues_after_per_skill_error(fake_manifest_dir):
    def install_one(name: str) -> str:
        if name == "skill_b":
            raise RuntimeError("disk full")
        return "ok"

    results = skill_bundles.bundle_install("alpha", fake_manifest_dir, install_one)
    assert len(results) == 2
    assert results[0]["status"] == "installed"
    assert results[1]["status"] == "error"
    assert "disk full" in results[1]["message"]


def test_install_placeholder_returns_noop(fake_manifest_dir):
    def install_one(name: str) -> str:
        raise AssertionError("install_one must NOT be called for placeholder")

    results = skill_bundles.bundle_install("empty-placeholder", fake_manifest_dir, install_one)
    assert len(results) == 1
    assert results[0]["status"] == "placeholder"


def test_uninstall_routes_through_callback(fake_manifest_dir):
    calls: list[str] = []

    def uninstall_one(name: str) -> str:
        calls.append(name)
        return f"removed {name}"

    results = skill_bundles.bundle_uninstall("alpha", fake_manifest_dir, uninstall_one)
    assert calls == ["skill_a", "skill_b"]
    assert all(r["status"] == "uninstalled" for r in results)


def test_list_returns_summary_for_each_bundle(fake_manifest_dir):
    entries = skill_bundles.bundle_list(fake_manifest_dir)
    by_name = {e["name"]: e for e in entries}
    assert by_name["alpha"]["skill_count"] == 2
    assert by_name["alpha"]["placeholder"] is False
    assert by_name["empty-placeholder"]["placeholder"] is True
    assert by_name["empty-placeholder"]["skill_count"] == 0


def test_format_list_table_handles_empty():
    assert "No bundles configured." in skill_bundles.format_list_table([])


def test_format_show_renders_skills():
    body = {
        "name": "alpha",
        "title": "Alpha",
        "description": "desc",
        "skills": ["a", "b"],
        "placeholder": False,
    }
    text = skill_bundles.format_show(body)
    assert "Bundle: alpha" in text
    assert "  - a" in text
    assert "  - b" in text


def test_format_show_renders_placeholder():
    body = {
        "name": "x",
        "title": "X",
        "description": "",
        "skills": [],
        "placeholder": True,
    }
    text = skill_bundles.format_show(body)
    assert "(empty placeholder)" in text


def test_format_install_results_marks_skips_and_errors():
    rows = [
        {"skill": "a", "status": "installed", "message": "ok"},
        {"skill": "b", "status": "deprecated_skipped", "message": "use X"},
        {"skill": "c", "status": "error", "message": "boom"},
    ]
    text = skill_bundles.format_install_results(rows)
    assert "[OK] a" in text
    assert "[SKIP] b" in text
    assert "[ERR] c" in text
