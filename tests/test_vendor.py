"""Tests for bootstrap_vendor — external skill dependency management."""

from __future__ import annotations

import io
import json
import os
import tarfile
import tempfile

import pytest

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

from bootstrap_vendor import (
    _extract_skill_dirs,
    _read_lock,
    _write_lock,
    get_vendor_skill_dirs,
    load_skills_json,
)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def _make_tarball(
    files: dict[str, str],
    root_prefix: str = "repo-v1.0.0",
    symlinks: dict[str, str] | None = None,
) -> bytes:
    """Create a tarball in memory with given files and optional symlinks."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # Add root dir
        info = tarfile.TarInfo(name=root_prefix + "/")
        info.type = tarfile.DIRTYPE
        tar.addfile(info)
        for rel_path, content in files.items():
            full_path = f"{root_prefix}/{rel_path}"
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=full_path)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        if symlinks:
            for sym_path, sym_target in symlinks.items():
                info = tarfile.TarInfo(name=f"{root_prefix}/{sym_path}")
                info.type = tarfile.SYMTYPE
                info.linkname = sym_target
                tar.addfile(info)
    return buf.getvalue()


class TestLoadSkillsJson:
    def test_missing_file_returns_empty(self, tmp_dir):
        result = load_skills_json(tmp_dir)
        assert result == {"external_skills": {}}

    def test_loads_valid_file(self, tmp_dir):
        manifest = {"external_skills": {"seo": {"repo": "user/repo", "ref": "v1.0"}}}
        with open(os.path.join(tmp_dir, "skills.json"), "w") as f:
            json.dump(manifest, f)
        result = load_skills_json(tmp_dir)
        assert result["external_skills"]["seo"]["repo"] == "user/repo"


class TestLockFile:
    def test_write_and_read(self, tmp_dir):
        _write_lock(tmp_dir, "seo", "v1.5.0", "abc123")
        lock = _read_lock(tmp_dir, "seo")
        assert lock is not None
        assert lock["ref"] == "v1.5.0"
        assert lock["sha"] == "abc123"
        assert "synced_at" in lock

    def test_read_missing_returns_none(self, tmp_dir):
        assert _read_lock(tmp_dir, "nonexistent") is None


class TestExtractSkillDirs:
    def test_extracts_skill_directory(self, tmp_dir):
        tarball = _make_tarball(
            {
                "seo/SKILL.md": "# SEO Skill",
                "seo/config.json": "{}",
                "other/README.md": "# Other",
            }
        )
        vendor_dir = os.path.join(tmp_dir, "seo")
        counts = _extract_skill_dirs(tarball, vendor_dir, ["seo"])
        assert counts["skills"] == 2
        assert os.path.exists(os.path.join(vendor_dir, "seo", "SKILL.md"))
        assert os.path.exists(os.path.join(vendor_dir, "seo", "config.json"))
        # "other" should not be extracted
        assert not os.path.exists(os.path.join(vendor_dir, "other"))

    def test_extracts_nested_skill_dirs(self, tmp_dir):
        tarball = _make_tarball(
            {
                "skills/seo-audit/SKILL.md": "# Audit",
                "skills/seo-page/SKILL.md": "# Page",
                "skills/unrelated/SKILL.md": "# Unrelated",
            }
        )
        vendor_dir = os.path.join(tmp_dir, "seo")
        counts = _extract_skill_dirs(
            tarball, vendor_dir, ["skills/seo-audit", "skills/seo-page"]
        )
        assert counts["skills"] == 2
        assert os.path.exists(os.path.join(vendor_dir, "seo-audit", "SKILL.md"))
        assert os.path.exists(os.path.join(vendor_dir, "seo-page", "SKILL.md"))
        assert not os.path.exists(os.path.join(vendor_dir, "unrelated"))

    def test_extracts_scripts(self, tmp_dir):
        tarball = _make_tarball(
            {
                "seo/SKILL.md": "# SEO",
                "scripts/fetch.py": "print('fetch')",
                "scripts/parse.py": "print('parse')",
            }
        )
        vendor_dir = os.path.join(tmp_dir, "seo")
        counts = _extract_skill_dirs(
            tarball, vendor_dir, ["seo"], scripts_dir="scripts"
        )
        assert counts["scripts"] == 2
        assert os.path.exists(os.path.join(vendor_dir, "scripts", "fetch.py"))

    def test_extracts_agents(self, tmp_dir):
        tarball = _make_tarball(
            {
                "seo/SKILL.md": "# SEO",
                "agents/seo-technical.md": "# Agent",
            }
        )
        vendor_dir = os.path.join(tmp_dir, "seo")
        counts = _extract_skill_dirs(tarball, vendor_dir, ["seo"], agents_dir="agents")
        assert counts["agents"] == 1

    def test_preserves_lock_on_re_extract(self, tmp_dir):
        vendor_dir = os.path.join(tmp_dir, "seo")
        _write_lock(tmp_dir, "seo", "v1.0", "old")
        tarball = _make_tarball({"seo/SKILL.md": "# Updated"})
        _extract_skill_dirs(tarball, vendor_dir, ["seo"])
        # Lock should still be there
        lock = _read_lock(tmp_dir, "seo")
        assert lock is not None
        assert lock["ref"] == "v1.0"

    def test_extracts_data_dirs(self, tmp_dir):
        """data_dirs extracts additional directories into skill subdir."""
        tarball = _make_tarball(
            {
                ".claude/skills/myskill/SKILL.md": "# My Skill",
                "src/myskill/data/styles.csv": "name,value\nminimal,true",
                "src/myskill/data/colors.csv": "hex,name\n#fff,white",
                "src/myskill/scripts/search.py": "print('search')",
            }
        )
        vendor_dir = os.path.join(tmp_dir, "myskill")
        data_dirs = {
            "src/myskill/data": "data",
            "src/myskill/scripts": "scripts",
        }
        counts = _extract_skill_dirs(
            tarball,
            vendor_dir,
            [".claude/skills/myskill"],
            data_dirs=data_dirs,
        )
        assert counts["skills"] == 1  # SKILL.md
        assert counts["data"] == 3  # 2 csv + 1 py
        assert os.path.exists(os.path.join(vendor_dir, "myskill", "SKILL.md"))
        assert os.path.exists(os.path.join(vendor_dir, "myskill", "data", "styles.csv"))
        assert os.path.exists(os.path.join(vendor_dir, "myskill", "data", "colors.csv"))
        assert os.path.exists(
            os.path.join(vendor_dir, "myskill", "scripts", "search.py")
        )

    def test_symlink_resolution(self, tmp_dir):
        """Symlinks in skill_dirs are resolved to their target files."""
        tarball = _make_tarball(
            files={
                ".claude/skills/myskill/SKILL.md": "# Skill",
                "src/myskill/data/db.csv": "id,name\n1,test",
            },
            symlinks={
                # 3 levels up: .claude/skills/myskill/ -> repo root
                ".claude/skills/myskill/data": "../../../src/myskill/data",
            },
        )
        vendor_dir = os.path.join(tmp_dir, "myskill")
        counts = _extract_skill_dirs(tarball, vendor_dir, [".claude/skills/myskill"])
        assert counts["skills"] == 1  # SKILL.md
        assert counts["data"] >= 1  # symlink-resolved file
        assert os.path.exists(os.path.join(vendor_dir, "myskill", "SKILL.md"))
        assert os.path.exists(os.path.join(vendor_dir, "myskill", "data", "db.csv"))

    def test_symlink_escape_rejected(self, tmp_dir):
        """Symlinks that resolve outside repo root are ignored."""
        tarball = _make_tarball(
            files={
                ".claude/skills/myskill/SKILL.md": "# Skill",
                "etc/passwd": "root:x:0:0",
            },
            symlinks={
                ".claude/skills/myskill/evil": "../../../../etc",
            },
        )
        vendor_dir = os.path.join(tmp_dir, "myskill")
        _extract_skill_dirs(tarball, vendor_dir, [".claude/skills/myskill"])
        # SKILL.md should be extracted, but evil symlink should be rejected
        assert os.path.exists(os.path.join(vendor_dir, "myskill", "SKILL.md"))
        assert not os.path.exists(os.path.join(vendor_dir, "myskill", "evil"))

    def test_backward_compat_no_data_dirs(self, tmp_dir):
        """Skills without data_dirs continue to work as before."""
        tarball = _make_tarball(
            {
                "seo/SKILL.md": "# SEO Skill",
                "seo/config.json": "{}",
            }
        )
        vendor_dir = os.path.join(tmp_dir, "seo")
        counts = _extract_skill_dirs(tarball, vendor_dir, ["seo"])
        assert counts["skills"] == 2
        assert counts.get("data", 0) == 0
        assert os.path.exists(os.path.join(vendor_dir, "seo", "SKILL.md"))

    def test_path_traversal_blocked(self, tmp_dir):
        """Ensure path traversal attempts are blocked."""
        tarball = _make_tarball(
            {
                "seo/SKILL.md": "# SEO",
                "seo/../../etc/passwd": "evil",
            }
        )
        vendor_dir = os.path.join(tmp_dir, "seo")
        _extract_skill_dirs(tarball, vendor_dir, ["seo"])
        # Evil file should NOT exist outside vendor_dir
        assert not os.path.exists(os.path.join(tmp_dir, "etc", "passwd"))


class TestPluginJson:
    """Test .claude-plugin/plugin.json reading."""

    def test_reads_plugin_json(self):
        from bootstrap_vendor import _read_plugin_json

        tarball = _make_tarball(
            {
                ".claude-plugin/plugin.json": json.dumps(
                    {
                        "name": "ui-ux-pro-max",
                        "version": "2.5.0",
                        "description": "UI/UX design intelligence",
                    }
                ),
                ".claude/skills/ui-ux-pro-max/SKILL.md": "# Skill",
            }
        )
        meta = _read_plugin_json(tarball)
        assert meta is not None
        assert meta["name"] == "ui-ux-pro-max"
        assert meta["version"] == "2.5.0"

    def test_returns_none_when_no_plugin_json(self):
        from bootstrap_vendor import _read_plugin_json

        tarball = _make_tarball({"seo/SKILL.md": "# SEO"})
        assert _read_plugin_json(tarball) is None


class TestCopySkillsWithVendor:
    """Integration: copy_skills uses vendor as fallback."""

    def test_vendor_skill_copied_when_not_in_library(self, tmp_dir):
        from bootstrap_copy import copy_skills

        lib_dir = os.path.join(tmp_dir, "lib")
        os.makedirs(os.path.join(lib_dir, "agents", "skills", "start"))
        with open(
            os.path.join(lib_dir, "agents", "skills", "start", "SKILL.md"),
            "w",
        ) as f:
            f.write("# Start")

        target_dir = os.path.join(tmp_dir, "target")
        os.makedirs(target_dir)

        # Vendor skill
        vendor_skill_dir = os.path.join(tmp_dir, "vendor_seo")
        os.makedirs(vendor_skill_dir)
        with open(os.path.join(vendor_skill_dir, "SKILL.md"), "w") as f:
            f.write("# SEO Vendor Skill")

        config = {
            "core_skills": ["start"],
            "extension_skills": ["seo"],
            "installed_skills": ["seo"],
        }
        vendor_map = {"seo": vendor_skill_dir}

        count = copy_skills(lib_dir, target_dir, config, "claude", vendor_map)
        assert count == 2  # start + seo
        assert os.path.exists(os.path.join(target_dir, "skills", "start", "SKILL.md"))
        assert os.path.exists(os.path.join(target_dir, "skills", "seo", "SKILL.md"))

    def test_library_skill_takes_precedence_over_vendor(self, tmp_dir):
        from bootstrap_copy import copy_skills

        lib_dir = os.path.join(tmp_dir, "lib")
        skill_dir = os.path.join(lib_dir, "agents", "skills", "review")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("# Library Review")

        target_dir = os.path.join(tmp_dir, "target")
        os.makedirs(target_dir)

        vendor_skill_dir = os.path.join(tmp_dir, "vendor_review")
        os.makedirs(vendor_skill_dir)
        with open(os.path.join(vendor_skill_dir, "SKILL.md"), "w") as f:
            f.write("# Vendor Review (should NOT be used)")

        config = {"core_skills": [], "extension_skills": ["review"]}
        vendor_map = {"review": vendor_skill_dir}

        copy_skills(lib_dir, target_dir, config, "claude", vendor_map)
        with open(os.path.join(target_dir, "skills", "review", "SKILL.md")) as f:
            content = f.read()
        assert "Library Review" in content  # Library wins


class TestSkillCatalogGeneration:
    """Test that skill catalog is generated correctly."""

    def test_generates_catalog_with_installed_and_available(self, tmp_dir):
        from bootstrap_catalog import generate_skill_catalog

        manifest = {
            "external_skills": {
                "seo": {
                    "repo": "user/seo",
                    "ref": "v1.0",
                    "description": "SEO analysis",
                    "triggers": ["SEO", "audit"],
                },
                "analytics": {
                    "repo": "user/analytics",
                    "ref": "v2.0",
                    "description": "Analytics dashboard",
                    "triggers": ["analytics", "metrics"],
                },
            }
        }
        target_dir = os.path.join(tmp_dir, ".claude")
        os.makedirs(target_dir)
        generate_skill_catalog(target_dir, manifest, installed_skills=["seo"])

        catalog_path = os.path.join(target_dir, "references", "skill-catalog.md")
        assert os.path.exists(catalog_path)
        with open(catalog_path) as f:
            content = f.read()
        assert "[ACTIVE]" in content
        assert "[AVAILABLE]" in content
        assert "SEO analysis" in content
        assert "Analytics dashboard" in content
        assert "Install:" in content  # only for non-installed

    def test_empty_manifest_no_catalog(self, tmp_dir):
        from bootstrap_catalog import generate_skill_catalog

        target_dir = os.path.join(tmp_dir, ".claude")
        os.makedirs(target_dir)
        generate_skill_catalog(target_dir, {}, installed_skills=[])
        assert not os.path.exists(
            os.path.join(target_dir, "references", "skill-catalog.md")
        )


class TestSkillCLI:
    """Test skill activate/deactivate/list service logic."""

    def test_find_vendor_skill(self, tmp_dir):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
        from project_service import ProjectService

        # Create vendor structure
        seo_dir = os.path.join(tmp_dir, "seo", "seo-audit")
        os.makedirs(seo_dir)
        with open(os.path.join(seo_dir, "SKILL.md"), "w") as f:
            f.write("# SEO Audit")

        result = ProjectService._find_vendor_skill(tmp_dir, "seo-audit")
        assert result is not None
        assert result.endswith("seo-audit")

    def test_find_vendor_skill_missing(self, tmp_dir):
        from project_service import ProjectService

        assert ProjectService._find_vendor_skill(tmp_dir, "nonexistent") is None

    def test_find_vendor_skill_no_dir(self):
        from project_service import ProjectService

        assert ProjectService._find_vendor_skill("/nonexistent", "anything") is None


class TestSkillActivatePersistence:
    """Test that skill activate/deactivate persists to config.json."""

    def _setup_vendor(self, tmp_dir):
        """Create vendor + skills_dst + config for testing."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
        vendor_dir = os.path.join(tmp_dir, "vendor")
        skill_src = os.path.join(vendor_dir, "ui-ux", "ui-ux-pro-max")
        os.makedirs(skill_src)
        with open(os.path.join(skill_src, "SKILL.md"), "w") as f:
            f.write("# UI UX Pro Max")
        skills_dst = os.path.join(tmp_dir, ".claude", "skills")
        os.makedirs(skills_dst)
        lib_skills = os.path.join(tmp_dir, "agents", "claude", "skills")
        os.makedirs(lib_skills)
        config_path = os.path.join(tmp_dir, ".tausik", "config.json")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(
                {"bootstrap": {"core_skills": ["start"], "extension_skills": []}}, f
            )
        return vendor_dir, skills_dst, lib_skills, config_path

    def test_activate_writes_to_config(self, tmp_dir):
        from project_service import ProjectService

        vendor_dir, skills_dst, lib_skills, config_path = self._setup_vendor(tmp_dir)
        ProjectService.skill_activate(
            "ui-ux-pro-max", vendor_dir, skills_dst, lib_skills, config_path
        )
        with open(config_path) as f:
            cfg = json.load(f)
        assert "ui-ux-pro-max" in cfg["bootstrap"]["installed_skills"]

    def test_activate_copies_skill(self, tmp_dir):
        from project_service import ProjectService

        vendor_dir, skills_dst, lib_skills, config_path = self._setup_vendor(tmp_dir)
        ProjectService.skill_activate(
            "ui-ux-pro-max", vendor_dir, skills_dst, lib_skills, config_path
        )
        assert os.path.exists(os.path.join(skills_dst, "ui-ux-pro-max", "SKILL.md"))

    def test_activate_idempotent(self, tmp_dir):
        from project_service import ProjectService

        vendor_dir, skills_dst, lib_skills, config_path = self._setup_vendor(tmp_dir)
        ProjectService.skill_activate(
            "ui-ux-pro-max", vendor_dir, skills_dst, lib_skills, config_path
        )
        result = ProjectService.skill_activate(
            "ui-ux-pro-max", vendor_dir, skills_dst, lib_skills, config_path
        )
        assert "already active" in result

    def test_deactivate_removes_from_config(self, tmp_dir):
        from project_service import ProjectService

        vendor_dir, skills_dst, lib_skills, config_path = self._setup_vendor(tmp_dir)
        ProjectService.skill_activate(
            "ui-ux-pro-max", vendor_dir, skills_dst, lib_skills, config_path
        )
        ProjectService.skill_deactivate(
            "ui-ux-pro-max", skills_dst, lib_skills, config_path
        )
        with open(config_path) as f:
            cfg = json.load(f)
        assert "ui-ux-pro-max" not in cfg["bootstrap"].get("vendor_activated", [])
        assert not os.path.exists(os.path.join(skills_dst, "ui-ux-pro-max"))

    def test_deactivate_without_config_still_works(self, tmp_dir):
        """Backward compat: deactivate without config_path just removes files."""
        from project_service import ProjectService

        vendor_dir, skills_dst, lib_skills, config_path = self._setup_vendor(tmp_dir)
        ProjectService.skill_activate(
            "ui-ux-pro-max", vendor_dir, skills_dst, lib_skills, config_path
        )
        result = ProjectService.skill_deactivate(
            "ui-ux-pro-max", skills_dst, lib_skills
        )
        assert "deactivated" in result.lower()


class TestBootstrapPreservesVendorSkills:
    """Test that bootstrap cleanup preserves vendor-activated skills."""

    def test_vendor_activated_survives_bootstrap(self, tmp_dir):
        from bootstrap_copy import copy_skills

        lib_dir = os.path.join(tmp_dir, "lib")
        start_dir = os.path.join(lib_dir, "agents", "skills", "start")
        os.makedirs(start_dir)
        with open(os.path.join(start_dir, "SKILL.md"), "w") as f:
            f.write("# Start")

        target_dir = os.path.join(tmp_dir, "target")
        os.makedirs(target_dir)

        # Pre-create a vendor-activated skill in target
        vendor_skill = os.path.join(target_dir, "skills", "ui-ux-pro-max")
        os.makedirs(vendor_skill)
        with open(os.path.join(vendor_skill, "SKILL.md"), "w") as f:
            f.write("# UI UX")

        # Vendor map for re-copy
        vendor_src = os.path.join(tmp_dir, "vendor_src")
        os.makedirs(vendor_src)
        with open(os.path.join(vendor_src, "SKILL.md"), "w") as f:
            f.write("# UI UX from vendor")

        config = {
            "core_skills": ["start"],
            "extension_skills": [],
            "vendor_activated": ["ui-ux-pro-max"],
        }
        vendor_map = {"ui-ux-pro-max": vendor_src}

        copy_skills(lib_dir, target_dir, config, "claude", vendor_map)
        # Vendor skill should survive
        assert os.path.exists(
            os.path.join(target_dir, "skills", "ui-ux-pro-max", "SKILL.md")
        )

    def test_non_vendor_skill_cleaned_up(self, tmp_dir):
        from bootstrap_copy import copy_skills

        lib_dir = os.path.join(tmp_dir, "lib")
        start_dir = os.path.join(lib_dir, "agents", "skills", "start")
        os.makedirs(start_dir)
        with open(os.path.join(start_dir, "SKILL.md"), "w") as f:
            f.write("# Start")

        target_dir = os.path.join(tmp_dir, "target")
        # Pre-create an orphan skill
        orphan = os.path.join(target_dir, "skills", "orphan-skill")
        os.makedirs(orphan)
        with open(os.path.join(orphan, "SKILL.md"), "w") as f:
            f.write("# Orphan")

        config = {
            "core_skills": ["start"],
            "extension_skills": [],
            "vendor_activated": [],
        }
        copy_skills(lib_dir, target_dir, config, "claude")
        # Orphan should be cleaned up
        assert not os.path.exists(os.path.join(target_dir, "skills", "orphan-skill"))

    def test_repeated_bootstrap_preserves_vendor(self, tmp_dir):
        """Simulate two bootstrap runs — vendor skill should survive both."""
        from bootstrap_copy import copy_skills

        lib_dir = os.path.join(tmp_dir, "lib")
        start_dir = os.path.join(lib_dir, "agents", "skills", "start")
        os.makedirs(start_dir)
        with open(os.path.join(start_dir, "SKILL.md"), "w") as f:
            f.write("# Start")

        target_dir = os.path.join(tmp_dir, "target")
        vendor_src = os.path.join(tmp_dir, "vendor_src")
        os.makedirs(vendor_src)
        with open(os.path.join(vendor_src, "SKILL.md"), "w") as f:
            f.write("# UI UX")

        config = {
            "core_skills": ["start"],
            "extension_skills": [],
            "vendor_activated": ["ui-ux-pro-max"],
        }
        vendor_map = {"ui-ux-pro-max": vendor_src}

        # Run 1
        copy_skills(lib_dir, target_dir, config, "claude", vendor_map)
        assert os.path.exists(
            os.path.join(target_dir, "skills", "ui-ux-pro-max", "SKILL.md")
        )

        # Run 2
        copy_skills(lib_dir, target_dir, config, "claude", vendor_map)
        assert os.path.exists(
            os.path.join(target_dir, "skills", "ui-ux-pro-max", "SKILL.md")
        )


class TestGetVendorSkillDirs:
    def test_returns_skill_dirs_with_skill_md(self, tmp_dir):
        # Create vendor structure
        seo_dir = os.path.join(tmp_dir, "seo", "seo")
        os.makedirs(seo_dir)
        with open(os.path.join(seo_dir, "SKILL.md"), "w") as f:
            f.write("# SEO")

        audit_dir = os.path.join(tmp_dir, "seo", "seo-audit")
        os.makedirs(audit_dir)
        with open(os.path.join(audit_dir, "SKILL.md"), "w") as f:
            f.write("# Audit")

        # Scripts dir should be excluded
        scripts_dir = os.path.join(tmp_dir, "seo", "scripts")
        os.makedirs(scripts_dir)

        result = get_vendor_skill_dirs(tmp_dir)
        assert "seo" in result
        assert "seo-audit" in result
        assert "scripts" not in result

    def test_empty_vendor_dir(self, tmp_dir):
        assert get_vendor_skill_dirs(tmp_dir) == {}

    def test_nonexistent_vendor_dir(self):
        assert get_vendor_skill_dirs("/nonexistent/path") == {}
