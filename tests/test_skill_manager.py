"""Tests for skill_manager — repo management, skill install/uninstall."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from skill_manager import (
    MANIFEST_FORMAT,
    TAUSIK_MANIFEST,
    SkillManagerError,
    _repo_name_from_url,
    _validate_path_inside,
    _validate_url,
    clone_repo,
    copy_skill,
    detect_repo_format,
    find_skill_source,
    get_skill_info,
    install_skill,
    load_manifest,
    uninstall_skill,
)
from skill_repos import (
    repo_add,
    repo_list,
    repo_list_all_skills,
    repo_remove,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manifest(skills: dict | None = None) -> dict:
    return {
        "format": MANIFEST_FORMAT,
        "version": 1,
        "skills": skills or {},
    }


def _write_manifest(repo_dir: str, skills: dict | None = None) -> None:
    os.makedirs(repo_dir, exist_ok=True)
    with open(os.path.join(repo_dir, TAUSIK_MANIFEST), "w") as f:
        json.dump(_make_manifest(skills), f)


def _make_skill(repo_dir: str, name: str, content: str = "# Skill") -> str:
    skill_dir = os.path.join(repo_dir, name)
    os.makedirs(skill_dir, exist_ok=True)
    with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
        f.write(content)
    return skill_dir


# ---------------------------------------------------------------------------
# Tests: repo name extraction
# ---------------------------------------------------------------------------


class TestRepoNameFromUrl:
    def test_https_url(self):
        assert _repo_name_from_url("https://github.com/Org/my-skills") == "my-skills"

    def test_url_with_git_suffix(self):
        assert _repo_name_from_url("https://github.com/Org/repo.git") == "repo"

    def test_trailing_slash(self):
        assert _repo_name_from_url("https://github.com/Org/repo/") == "repo"


# ---------------------------------------------------------------------------
# Tests: format detection
# ---------------------------------------------------------------------------


class TestDetectRepoFormat:
    def test_tausik_native(self, tmp_path):
        repo = str(tmp_path / "repo")
        _write_manifest(repo, {"jira": {"path": "jira/", "description": "Jira"}})
        result = detect_repo_format(repo)
        assert result["format"] == "tausik-native"
        assert result["skills_count"] == 1
        assert "jira" in result["skill_names"]

    def test_no_manifest(self, tmp_path):
        repo = str(tmp_path / "repo")
        os.makedirs(repo)
        result = detect_repo_format(repo)
        assert result["format"] == "incompatible"

    def test_wrong_format(self, tmp_path):
        repo = str(tmp_path / "repo")
        os.makedirs(repo)
        with open(os.path.join(repo, TAUSIK_MANIFEST), "w") as f:
            json.dump({"format": "other"}, f)
        result = detect_repo_format(repo)
        assert result["format"] == "incompatible"


# ---------------------------------------------------------------------------
# Tests: manifest loading
# ---------------------------------------------------------------------------


class TestLoadManifest:
    def test_valid(self, tmp_path):
        repo = str(tmp_path / "repo")
        _write_manifest(repo, {"foo": {"path": "foo/"}})
        m = load_manifest(repo)
        assert "foo" in m["skills"]

    def test_missing(self, tmp_path):
        repo = str(tmp_path / "repo")
        os.makedirs(repo)
        with pytest.raises(SkillManagerError, match="not found"):
            load_manifest(repo)

    def test_wrong_format(self, tmp_path):
        repo = str(tmp_path / "repo")
        os.makedirs(repo)
        with open(os.path.join(repo, TAUSIK_MANIFEST), "w") as f:
            json.dump({"format": "wrong"}, f)
        with pytest.raises(SkillManagerError, match="wrong format"):
            load_manifest(repo)


class TestGetSkillInfo:
    def test_found(self):
        m = _make_manifest({"jira": {"description": "Jira"}})
        info = get_skill_info(m, "jira")
        assert info["description"] == "Jira"

    def test_not_found(self):
        m = _make_manifest({"jira": {}})
        with pytest.raises(SkillManagerError, match="not found"):
            get_skill_info(m, "nonexistent")


# ---------------------------------------------------------------------------
# Tests: find skill source
# ---------------------------------------------------------------------------


class TestFindSkillSource:
    def test_found(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        repo = os.path.join(vendor, "my-repo")
        _write_manifest(repo, {"jira": {"path": "jira/", "description": "Jira"}})
        _make_skill(repo, "jira")
        result = find_skill_source(vendor, "jira")
        assert result is not None
        assert result[1] == "my-repo"

    def test_not_found(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        os.makedirs(vendor)
        assert find_skill_source(vendor, "jira") is None

    def test_no_vendor_dir(self, tmp_path):
        assert find_skill_source(str(tmp_path / "nope"), "jira") is None


# ---------------------------------------------------------------------------
# Tests: copy skill
# ---------------------------------------------------------------------------


class TestCopySkill:
    def test_copies_skill_md(self, tmp_path):
        repo = str(tmp_path / "repo")
        skill_info = {"path": "jira/"}
        _make_skill(repo, "jira", "---\nname: jira\n---\n# Jira skill")
        dst_dir = str(tmp_path / "skills")
        os.makedirs(dst_dir)
        copy_skill(repo, skill_info, "jira", dst_dir)
        assert os.path.isfile(os.path.join(dst_dir, "jira", "SKILL.md"))

    def test_copies_references(self, tmp_path):
        repo = str(tmp_path / "repo")
        skill_dir = _make_skill(repo, "jira")
        refs = os.path.join(skill_dir, "references")
        os.makedirs(refs)
        with open(os.path.join(refs, "api.md"), "w") as f:
            f.write("# API")
        dst_dir = str(tmp_path / "skills")
        os.makedirs(dst_dir)
        copy_skill(repo, {"path": "jira/"}, "jira", dst_dir)
        assert os.path.isfile(os.path.join(dst_dir, "jira", "references", "api.md"))

    def test_skips_gitignore(self, tmp_path):
        repo = str(tmp_path / "repo")
        _make_skill(repo, "jira")
        with open(os.path.join(repo, "jira", ".gitignore"), "w") as f:
            f.write("*")
        dst_dir = str(tmp_path / "skills")
        os.makedirs(dst_dir)
        copy_skill(repo, {"path": "jira/"}, "jira", dst_dir)
        assert not os.path.exists(os.path.join(dst_dir, "jira", ".gitignore"))

    def test_missing_skill_md(self, tmp_path):
        repo = str(tmp_path / "repo")
        os.makedirs(os.path.join(repo, "jira"))
        dst_dir = str(tmp_path / "skills")
        os.makedirs(dst_dir)
        with pytest.raises(SkillManagerError, match="SKILL.md not found"):
            copy_skill(repo, {"path": "jira/"}, "jira", dst_dir)

    def test_replaces_existing(self, tmp_path):
        repo = str(tmp_path / "repo")
        _make_skill(repo, "jira", "NEW CONTENT")
        dst_dir = str(tmp_path / "skills")
        os.makedirs(os.path.join(dst_dir, "jira"))
        with open(os.path.join(dst_dir, "jira", "SKILL.md"), "w") as f:
            f.write("OLD")
        copy_skill(repo, {"path": "jira/"}, "jira", dst_dir)
        with open(os.path.join(dst_dir, "jira", "SKILL.md")) as f:
            assert "NEW CONTENT" in f.read()


# ---------------------------------------------------------------------------
# Tests: install / uninstall
# ---------------------------------------------------------------------------


class TestInstallUninstall:
    def test_install(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        repo = os.path.join(vendor, "test-repo")
        _write_manifest(repo, {"myskill": {"path": "myskill/", "description": "Test"}})
        _make_skill(repo, "myskill")
        skills_dst = str(tmp_path / "skills")
        os.makedirs(skills_dst)
        config = str(tmp_path / "config.json")
        tausik_dir = str(tmp_path / ".tausik")
        os.makedirs(tausik_dir)

        result = install_skill("myskill", vendor, skills_dst, config, tausik_dir)
        assert "installed" in result
        assert os.path.isfile(os.path.join(skills_dst, "myskill", "SKILL.md"))
        with open(config) as f:
            cfg = json.load(f)
        assert "myskill" in cfg["bootstrap"]["installed_skills"]

    def test_install_not_found(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        os.makedirs(vendor)
        with pytest.raises(SkillManagerError, match="not found"):
            install_skill(
                "nope", vendor, str(tmp_path), str(tmp_path / "c.json"), str(tmp_path)
            )

    def test_uninstall(self, tmp_path):
        skills_dst = str(tmp_path / "skills")
        skill_dir = os.path.join(skills_dst, "myskill")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("# test")
        config = str(tmp_path / "config.json")
        with open(config, "w") as f:
            json.dump({"bootstrap": {"installed_skills": ["myskill"]}}, f)

        result = uninstall_skill("myskill", skills_dst, config)
        assert "uninstalled" in result
        assert not os.path.exists(skill_dir)
        with open(config) as f:
            cfg = json.load(f)
        assert "myskill" not in cfg["bootstrap"]["installed_skills"]


# ---------------------------------------------------------------------------
# Tests: repo management
# ---------------------------------------------------------------------------


class TestRepoManagement:
    def test_repo_list_empty(self, tmp_path):
        config = str(tmp_path / "config.json")
        vendor = str(tmp_path / "vendor")
        result = repo_list(vendor, config)
        # Should include default repos
        assert any(r.get("default") for r in result)

    def test_repo_remove(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        repo_dir = os.path.join(vendor, "test-repo")
        os.makedirs(repo_dir)
        config = str(tmp_path / "config.json")
        with open(config, "w") as f:
            json.dump({"skill_repos": {"test-repo": {"url": "http://x"}}}, f)

        result = repo_remove("test-repo", vendor, config)
        assert "removed" in result
        assert not os.path.exists(repo_dir)

    def test_repo_list_all_skills(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        repo = os.path.join(vendor, "my-repo")
        _write_manifest(
            repo,
            {
                "jira": {"path": "jira/", "description": "Jira", "triggers": ["jira"]},
                "seo": {"path": "seo/", "description": "SEO"},
            },
        )
        result = repo_list_all_skills(vendor)
        names = [s["name"] for s in result]
        assert "jira" in names
        assert "seo" in names


# ---------------------------------------------------------------------------
# Tests: security validation
# ---------------------------------------------------------------------------


class TestUrlValidation:
    def test_https_allowed(self):
        _validate_url("https://github.com/Org/repo")

    def test_ssh_allowed(self):
        _validate_url("git@github.com:Org/repo.git")

    def test_ext_rejected(self):
        with pytest.raises(SkillManagerError, match="Unsupported URL"):
            _validate_url("ext::sh -c evil")

    def test_file_rejected(self):
        with pytest.raises(SkillManagerError, match="Unsupported URL"):
            _validate_url("file:///etc/passwd")


class TestPathValidation:
    def test_valid_child(self, tmp_path):
        parent = str(tmp_path / "parent")
        child = os.path.join(parent, "sub", "dir")
        os.makedirs(child)
        _validate_path_inside(child, parent)  # should not raise

    def test_traversal_blocked(self, tmp_path):
        parent = str(tmp_path / "parent")
        os.makedirs(parent)
        with pytest.raises(SkillManagerError, match="Path traversal"):
            _validate_path_inside(str(tmp_path / "outside"), parent)


class TestCopySkillPathTraversal:
    def test_rejects_path_escape(self, tmp_path):
        repo = str(tmp_path / "repo")
        os.makedirs(repo)
        _make_skill(repo, "legit")
        dst = str(tmp_path / "skills")
        os.makedirs(dst)
        with pytest.raises(SkillManagerError, match="Path traversal"):
            copy_skill(repo, {"path": "../../etc/"}, "evil", dst)


# ---------------------------------------------------------------------------
# Tests: clone_repo (mocked)
# ---------------------------------------------------------------------------


class TestCloneRepo:
    def test_clone_success(self, tmp_path, monkeypatch):
        vendor = str(tmp_path / "vendor")
        url = "https://github.com/Org/my-skills"

        def fake_run(cmd, **kwargs):
            # Simulate git clone by creating the dir
            repo_dir = cmd[-1]
            os.makedirs(repo_dir, exist_ok=True)
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(subprocess, "run", fake_run)
        repo_dir, name = clone_repo(url, vendor)
        assert name == "my-skills"
        assert os.path.isdir(repo_dir)

    def test_clone_git_not_found(self, tmp_path, monkeypatch):
        vendor = str(tmp_path / "vendor")

        def fake_run(cmd, **kwargs):
            raise FileNotFoundError("git")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(SkillManagerError, match="git not found"):
            clone_repo("https://github.com/Org/repo", vendor)

    def test_clone_ext_url_rejected(self, tmp_path):
        with pytest.raises(SkillManagerError, match="Unsupported URL"):
            clone_repo("ext::sh -c evil", str(tmp_path / "vendor"))

    def test_existing_repo_pulls(self, tmp_path, monkeypatch):
        vendor = str(tmp_path / "vendor")
        repo_dir = os.path.join(vendor, "my-repo")
        os.makedirs(os.path.join(repo_dir, ".git"))

        pull_called = []

        def fake_run(cmd, **kwargs):
            pull_called.append(cmd)
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(subprocess, "run", fake_run)
        result_dir, name = clone_repo("https://github.com/Org/my-repo", vendor)
        assert result_dir == repo_dir
        assert any("pull" in str(c) for c in pull_called)

    def test_clone_timeout(self, tmp_path, monkeypatch):
        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 120)

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(SkillManagerError, match="timed out"):
            clone_repo("https://github.com/Org/repo", str(tmp_path / "vendor"))

    def test_clone_nonzero_returncode(self, tmp_path, monkeypatch):
        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 128, stderr="fatal: repo not found")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(SkillManagerError, match="git clone failed"):
            clone_repo("https://github.com/Org/repo", str(tmp_path / "vendor"))


# ---------------------------------------------------------------------------
# Tests: repo_add (mocked clone)
# ---------------------------------------------------------------------------


class TestRepoAdd:
    def test_compatible_repo(self, tmp_path, monkeypatch):
        vendor = str(tmp_path / "vendor")
        config = str(tmp_path / "config.json")

        def fake_clone(url, vdir):
            repo_dir = os.path.join(vdir, "my-repo")
            _write_manifest(
                repo_dir,
                {
                    "jira": {"path": "jira/", "description": "Jira"},
                    "seo": {"path": "seo/", "description": "SEO"},
                },
            )
            return repo_dir, "my-repo"

        monkeypatch.setattr("skill_repos.clone_repo", fake_clone)
        result = repo_add("https://github.com/Org/my-repo", vendor, config)
        assert "2 skills" in result
        assert "jira" in result

    def test_incompatible_repo(self, tmp_path, monkeypatch):
        vendor = str(tmp_path / "vendor")
        config = str(tmp_path / "config.json")

        def fake_clone(url, vdir):
            repo_dir = os.path.join(vdir, "bad-repo")
            os.makedirs(repo_dir)
            return repo_dir, "bad-repo"

        monkeypatch.setattr("skill_repos.clone_repo", fake_clone)
        with pytest.raises(SkillManagerError, match="not TAUSIK-compatible"):
            repo_add("https://github.com/Org/bad-repo", vendor, config)

    def test_many_skills_truncated(self, tmp_path, monkeypatch):
        vendor = str(tmp_path / "vendor")
        config = str(tmp_path / "config.json")
        skills = {
            f"skill-{i}": {"path": f"s{i}/", "description": f"S{i}"} for i in range(15)
        }

        def fake_clone(url, vdir):
            repo_dir = os.path.join(vdir, "big-repo")
            _write_manifest(repo_dir, skills)
            return repo_dir, "big-repo"

        monkeypatch.setattr("skill_repos.clone_repo", fake_clone)
        result = repo_add("https://github.com/Org/big-repo", vendor, config)
        assert "15 skills" in result
        assert "+5 more" in result


# ---------------------------------------------------------------------------
# Tests: edge cases — corrupted JSON
# ---------------------------------------------------------------------------


class TestCorruptedJson:
    def test_detect_format_corrupted(self, tmp_path):
        repo = str(tmp_path / "repo")
        os.makedirs(repo)
        with open(os.path.join(repo, TAUSIK_MANIFEST), "w") as f:
            f.write("{invalid json")
        result = detect_repo_format(repo)
        assert result["format"] == "incompatible"

    def test_load_manifest_corrupted(self, tmp_path):
        repo = str(tmp_path / "repo")
        os.makedirs(repo)
        with open(os.path.join(repo, TAUSIK_MANIFEST), "w") as f:
            f.write("not json at all")
        with pytest.raises(SkillManagerError, match="Invalid"):
            load_manifest(repo)

    def test_find_skill_source_skips_corrupted(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        repo = os.path.join(vendor, "broken-repo")
        os.makedirs(repo)
        with open(os.path.join(repo, TAUSIK_MANIFEST), "w") as f:
            f.write("{bad")
        assert find_skill_source(vendor, "anything") is None


# ---------------------------------------------------------------------------
# Tests: copy_skill filters
# ---------------------------------------------------------------------------


class TestCopySkillFilters:
    def _setup_skill(self, tmp_path):
        repo = str(tmp_path / "repo")
        _make_skill(repo, "myskill", "# Skill content")
        skill_dir = os.path.join(repo, "myskill")
        # Add filtered items
        os.makedirs(os.path.join(skill_dir, ".claude-plugin"))
        with open(os.path.join(skill_dir, ".claude-plugin", "plugin.json"), "w") as f:
            f.write("{}")
        os.makedirs(os.path.join(skill_dir, "hooks"))
        with open(os.path.join(skill_dir, "hooks", "hook.py"), "w") as f:
            f.write("# hook")
        os.makedirs(os.path.join(skill_dir, "__pycache__"))
        with open(os.path.join(skill_dir, "__pycache__", "cache.pyc"), "w") as f:
            f.write("cache")
        with open(os.path.join(skill_dir, "CLAUDE.md"), "w") as f:
            f.write("# Claude")
        with open(os.path.join(skill_dir, ".gitmodules"), "w") as f:
            f.write("[sub]")
        # Add kept items
        os.makedirs(os.path.join(skill_dir, "scripts"))
        with open(os.path.join(skill_dir, "scripts", "run.py"), "w") as f:
            f.write("# script")
        dst = str(tmp_path / "skills")
        os.makedirs(dst)
        return repo, dst

    def test_skips_claude_plugin(self, tmp_path):
        repo, dst = self._setup_skill(tmp_path)
        copy_skill(repo, {"path": "myskill/"}, "myskill", dst)
        assert not os.path.exists(os.path.join(dst, "myskill", ".claude-plugin"))

    def test_skips_hooks(self, tmp_path):
        repo, dst = self._setup_skill(tmp_path)
        copy_skill(repo, {"path": "myskill/"}, "myskill", dst)
        assert not os.path.exists(os.path.join(dst, "myskill", "hooks"))

    def test_skips_pycache(self, tmp_path):
        repo, dst = self._setup_skill(tmp_path)
        copy_skill(repo, {"path": "myskill/"}, "myskill", dst)
        assert not os.path.exists(os.path.join(dst, "myskill", "__pycache__"))

    def test_skips_claude_md(self, tmp_path):
        repo, dst = self._setup_skill(tmp_path)
        copy_skill(repo, {"path": "myskill/"}, "myskill", dst)
        assert not os.path.exists(os.path.join(dst, "myskill", "CLAUDE.md"))

    def test_skips_gitmodules(self, tmp_path):
        repo, dst = self._setup_skill(tmp_path)
        copy_skill(repo, {"path": "myskill/"}, "myskill", dst)
        assert not os.path.exists(os.path.join(dst, "myskill", ".gitmodules"))

    def test_keeps_scripts(self, tmp_path):
        repo, dst = self._setup_skill(tmp_path)
        copy_skill(repo, {"path": "myskill/"}, "myskill", dst)
        assert os.path.isfile(os.path.join(dst, "myskill", "scripts", "run.py"))

    def test_nonexistent_skill_path(self, tmp_path):
        repo = str(tmp_path / "repo")
        os.makedirs(repo)
        dst = str(tmp_path / "skills")
        os.makedirs(dst)
        with pytest.raises(SkillManagerError, match="not found"):
            copy_skill(repo, {"path": "nonexistent/"}, "x", dst)


# ---------------------------------------------------------------------------
# Tests: install with deps / uninstall edge cases
# ---------------------------------------------------------------------------


class TestInstallWithDeps:
    def test_install_deps_fail_partial_message(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        repo = os.path.join(vendor, "test-repo")
        _write_manifest(
            repo,
            {
                "myskill": {
                    "path": "myskill/",
                    "description": "Test",
                    "requires": ["nonexistent-pkg"],
                }
            },
        )
        _make_skill(repo, "myskill")
        skills_dst = str(tmp_path / "skills")
        os.makedirs(skills_dst)
        config = str(tmp_path / "config.json")
        tausik_dir = str(tmp_path / ".tausik")
        os.makedirs(tausik_dir)
        # No venv → deps will fail
        result = install_skill("myskill", vendor, skills_dst, config, tausik_dir)
        assert "installed" in result
        assert "failed" in result


class TestUninstallEdgeCases:
    def test_uninstall_nonexistent_skill(self, tmp_path):
        skills_dst = str(tmp_path / "skills")
        os.makedirs(skills_dst)
        config = str(tmp_path / "config.json")
        with open(config, "w") as f:
            json.dump({}, f)
        result = uninstall_skill("nonexistent", skills_dst, config)
        assert "uninstalled" in result

    def test_uninstall_removes_from_vendor_activated(self, tmp_path):
        skills_dst = str(tmp_path / "skills")
        os.makedirs(os.path.join(skills_dst, "myskill"))
        with open(os.path.join(skills_dst, "myskill", "SKILL.md"), "w") as f:
            f.write("# test")
        config = str(tmp_path / "config.json")
        with open(config, "w") as f:
            json.dump({"bootstrap": {"vendor_activated": ["myskill"]}}, f)
        uninstall_skill("myskill", skills_dst, config)
        with open(config) as f:
            cfg = json.load(f)
        assert "myskill" not in cfg["bootstrap"].get("vendor_activated", [])


# ---------------------------------------------------------------------------
# Tests: repo_list with data
# ---------------------------------------------------------------------------


class TestRepoListWithData:
    def test_cloned_repo_with_skills(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        repo = os.path.join(vendor, "my-repo")
        _write_manifest(repo, {"jira": {"path": "jira/"}})
        config = str(tmp_path / "config.json")
        with open(config, "w") as f:
            json.dump({"skill_repos": {"my-repo": {"url": "https://x"}}}, f)
        result = repo_list(vendor, config)
        r = [x for x in result if x["name"] == "my-repo"][0]
        assert r["cloned"] is True
        assert "jira" in r["skills"]

    def test_string_url_format(self, tmp_path):
        """Config with plain string URL (legacy format)."""
        vendor = str(tmp_path / "vendor")
        config = str(tmp_path / "config.json")
        with open(config, "w") as f:
            json.dump({"skill_repos": {"old-repo": "https://old"}}, f)
        result = repo_list(vendor, config)
        r = [x for x in result if x["name"] == "old-repo"][0]
        assert r["url"] == "https://old"
        assert r["cloned"] is False
