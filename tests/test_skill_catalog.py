"""Tests for `tausik skill catalog` discovery (B7).

Covers:
- repo_catalog scans cloned repos and reads tausik-skills.json manifests
- single-repo filter narrows results
- empty vendor dir returns [] (no exception)
- category falls back to '' when missing from manifest entry
- service rejects unknown repo with ServiceError
- empty repo_name == None semantics (lists everything)
- repo_list_all_skills delegates to repo_catalog
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from skill_repos import repo_catalog, repo_list_all_skills  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


MANIFEST = "tausik-skills.json"


def _write_manifest(repo_dir: Path, skills: dict) -> None:
    repo_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / MANIFEST).write_text(
        json.dumps({"format": "tausik-skills/v1", "skills": skills}),
        encoding="utf-8",
    )


@pytest.fixture
def vendor(tmp_path):
    return tmp_path / "vendor"


@pytest.fixture
def cfg_path(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{}", encoding="utf-8")
    return p


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "tausik.db"))
    s = ProjectService(be)
    yield s
    be.close()


class TestRepoCatalogPure:
    def test_lists_all_repos(self, vendor):
        _write_manifest(
            vendor / "tausik-skills",
            {"audit": {"description": "Audit", "category": "review"}},
        )
        _write_manifest(
            vendor / "tausik-skills-pro",
            {"daily": {"description": "Daily standup notes"}},
        )
        rows = repo_catalog(str(vendor))
        names = {(r["name"], r["repo"]) for r in rows}
        assert ("audit", "tausik-skills") in names
        assert ("daily", "tausik-skills-pro") in names

    def test_single_repo_filter(self, vendor):
        _write_manifest(
            vendor / "repo-a",
            {"x": {"description": "X"}},
        )
        _write_manifest(
            vendor / "repo-b",
            {"y": {"description": "Y"}},
        )
        rows = repo_catalog(str(vendor), repo_name="repo-a")
        assert {r["name"] for r in rows} == {"x"}

    def test_empty_vendor_dir(self, tmp_path):
        assert repo_catalog(str(tmp_path / "missing")) == []

    def test_category_falls_back_empty(self, vendor):
        _write_manifest(
            vendor / "r",
            {"unsorted": {"description": "no category here"}},
        )
        rows = repo_catalog(str(vendor))
        assert rows[0]["category"] == ""

    def test_unknown_repo_returns_empty(self, vendor):
        vendor.mkdir(parents=True, exist_ok=True)
        assert repo_catalog(str(vendor), repo_name="nonexistent") == []

    def test_repo_list_all_skills_delegates(self, vendor):
        _write_manifest(
            vendor / "r",
            {"s": {"description": "Demo", "category": "demo"}},
        )
        rows = repo_list_all_skills(str(vendor))
        assert len(rows) == 1
        assert rows[0]["category"] == "demo"


class TestSkillCatalogService:
    def test_unknown_repo_raises(self, svc, vendor, cfg_path):
        vendor.mkdir(parents=True, exist_ok=True)
        with pytest.raises(ServiceError, match="not configured and not cloned"):
            svc.skill_catalog(str(vendor), repo_name="nope", config_path=str(cfg_path))

    def test_known_repo_via_clone_passes(self, svc, vendor, cfg_path):
        _write_manifest(
            vendor / "tausik-skills",
            {"alpha": {"description": "Alpha", "category": "demo"}},
        )
        rows = svc.skill_catalog(str(vendor), repo_name="tausik-skills", config_path=str(cfg_path))
        assert rows[0]["name"] == "alpha"

    def test_known_repo_via_config_only_passes(self, svc, vendor, cfg_path):
        """Configured-but-not-cloned repo must not raise — return empty list."""
        vendor.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(
            json.dumps({"skill_repos": {"tausik-skills": {"url": "https://example/x"}}}),
            encoding="utf-8",
        )
        rows = svc.skill_catalog(str(vendor), repo_name="tausik-skills", config_path=str(cfg_path))
        assert rows == []

    def test_no_repo_name_lists_all(self, svc, vendor, cfg_path):
        _write_manifest(vendor / "a", {"x": {"description": "X"}})
        _write_manifest(vendor / "b", {"y": {"description": "Y"}})
        rows = svc.skill_catalog(str(vendor), repo_name=None, config_path=str(cfg_path))
        assert {r["name"] for r in rows} == {"x", "y"}
