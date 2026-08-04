"""Bundles resolve from the skill repos, not from a directory beside the core.

`skill-bundle-from-vendor-repo` / decision #200. Bundle composition belongs to
the store that ships the skills: `bundles.json` travels inside a
tausik-skills-format repo, next to its `tausik-skills.json`. Resolution used to
look only for `skills-official/` adjacent to the core checkout — a path that
exists while developing the framework and never in a bootstrapped project, so
`tausik skill bundle` was dead for every actual user.

The union rule below is not a convenience. Internal skills must never be named
in the public store's manifest (project convention: what is published cannot be
unpublished). Unioning by bundle name lets a private store add its skills to a
bundle the public store declared empty, with neither file naming the other's
contents.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import skill_bundles  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/"]


def _store(root, name: str, manifest: dict) -> str:
    """Lay out a cloned skill repo carrying a bundles.json."""
    d = root / name
    d.mkdir(parents=True)
    (d / "tausik-skills.json").write_text(
        json.dumps({"format": "tausik-skills", "version": 1, "skills": {}}), encoding="utf-8"
    )
    (d / "bundles.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def test_bundle_resolves_from_a_cloned_repo_with_no_core_checkout(tmp_path):
    """The regression: a bootstrapped project has no skills-official/ at all.

    Before the fix this raised BundleError with "No bundles manifest at
    .../skills-official/bundles.json" — the store's own bundles were invisible
    because nothing ever looked inside the store.
    """
    vendor = tmp_path / "vendor"
    _store(
        vendor,
        "tausik-skills",
        {"version": 1, "bundles": {"quality-pro": {"title": "Quality Pro", "skills": ["audit"]}}},
    )
    absent_core = str(tmp_path / "no-such-core" / "skills-official")

    # The old resolution, reproduced: look only beside the core checkout.
    with pytest.raises(skill_bundles.BundleError):
        skill_bundles.bundle_list(absent_core)

    dirs = skill_bundles.discover_manifest_dirs(str(vendor), absent_core)
    assert dirs, "a cloned repo carrying bundles.json must be discovered"

    entries = skill_bundles.bundle_list(dirs)
    assert [e["name"] for e in entries] == ["quality-pro"]
    assert skill_bundles.bundle_show("quality-pro", dirs)["skills"] == ["audit"]


def test_two_stores_union_into_one_bundle_without_naming_each_other(tmp_path):
    """A private store fills a bundle the public store declared empty.

    This is the publication boundary in test form: the public manifest never
    mentions the private skill, and the private manifest never has to restate
    the public bundle's contents.
    """
    vendor = tmp_path / "vendor"
    _store(
        vendor,
        "a-public",
        {
            "version": 1,
            "bundles": {
                "ru-locale": {
                    "title": "RU Locale (placeholder)",
                    "description": "Reserved.",
                    "skills": [],
                    "placeholder": True,
                }
            },
        },
    )
    _store(
        vendor,
        "b-private",
        {"version": 1, "bundles": {"ru-locale": {"skills": ["internal-only-skill"]}}},
    )

    dirs = skill_bundles.discover_manifest_dirs(str(vendor), None)
    shown = skill_bundles.bundle_show("ru-locale", dirs)

    assert shown["skills"] == ["internal-only-skill"]
    assert shown["placeholder"] is False, "a filled bundle is no longer a placeholder"
    assert shown["title"] == "RU Locale (placeholder)", "public metadata still describes it"

    public_manifest = (vendor / "a-public" / "bundles.json").read_text(encoding="utf-8")
    assert "internal-only-skill" not in public_manifest, (
        "the private skill leaked into the public manifest — this is the "
        "irreversible mistake the union rule exists to prevent"
    )


def test_duplicate_skill_across_stores_is_listed_once(tmp_path):
    vendor = tmp_path / "vendor"
    _store(vendor, "a", {"version": 1, "bundles": {"x": {"skills": ["dup", "one"]}}})
    _store(vendor, "b", {"version": 1, "bundles": {"x": {"skills": ["dup", "two"]}}})
    dirs = skill_bundles.discover_manifest_dirs(str(vendor), None)
    assert skill_bundles.bundle_show("x", dirs)["skills"] == ["dup", "one", "two"]


def test_install_walks_the_merged_bundle(tmp_path):
    vendor = tmp_path / "vendor"
    _store(vendor, "a", {"version": 1, "bundles": {"x": {"skills": ["s1"]}}})
    _store(vendor, "b", {"version": 1, "bundles": {"x": {"skills": ["s2"]}}})
    dirs = skill_bundles.discover_manifest_dirs(str(vendor), None)

    installed: list[str] = []

    def _install_one(name: str) -> str:
        installed.append(name)
        return f"installed {name}"

    results = skill_bundles.bundle_install("x", dirs, _install_one)
    assert installed == ["s1", "s2"]
    assert [r["status"] for r in results] == ["installed", "installed"]


# ---------- negative paths (AC4) ----------


def test_no_store_provides_bundles_says_so_instead_of_reporting_an_empty_bundle(tmp_path):
    """Silence would read as 'this store has no bundles' — a wrong fact."""
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    dirs = skill_bundles.discover_manifest_dirs(str(vendor), None)
    assert dirs == []
    with pytest.raises(skill_bundles.BundleError) as exc:
        skill_bundles.bundle_list(dirs)
    msg = str(exc.value)
    assert "skill repo" in msg and "repo add" in msg, (
        f"the error must say where bundles come from and what to do; got: {msg}"
    )


def test_corrupt_manifest_in_one_store_is_reported_not_swallowed(tmp_path):
    vendor = tmp_path / "vendor"
    good = _store(vendor, "a-good", {"version": 1, "bundles": {"x": {"skills": ["s"]}}})
    broken = vendor / "b-broken"
    broken.mkdir()
    (broken / "bundles.json").write_text("{ not json", encoding="utf-8")

    dirs = skill_bundles.discover_manifest_dirs(str(vendor), None)
    assert good in dirs and str(broken) in dirs
    with pytest.raises(skill_bundles.BundleError) as exc:
        skill_bundles.bundle_list(dirs)
    assert "b-broken" in str(exc.value), "the failing store must be named"


def test_manifest_with_wrong_root_type_is_rejected(tmp_path):
    vendor = tmp_path / "vendor"
    d = vendor / "a"
    d.mkdir(parents=True)
    (d / "bundles.json").write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    dirs = skill_bundles.discover_manifest_dirs(str(vendor), None)
    with pytest.raises(skill_bundles.BundleError):
        skill_bundles.bundle_list(dirs)


def test_single_directory_argument_still_works(tmp_path):
    """Back-compat: the framework's own checkout passes one directory."""
    d = _store(tmp_path, "solo", {"version": 1, "bundles": {"x": {"skills": ["s"]}}})
    assert [e["name"] for e in skill_bundles.bundle_list(d)] == ["x"]
