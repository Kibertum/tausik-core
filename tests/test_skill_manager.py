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
    @pytest.mark.parametrize(
        "url,expected",
        [
            pytest.param("https://github.com/Org/my-skills", "my-skills", id="https_url"),
            pytest.param("https://github.com/Org/repo.git", "repo", id="url_with_git_suffix"),
            pytest.param("https://github.com/Org/repo/", "repo", id="trailing_slash"),
        ],
    )
    def test_repo_name(self, url, expected):
        assert _repo_name_from_url(url) == expected


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
            install_skill("nope", vendor, str(tmp_path), str(tmp_path / "c.json"), str(tmp_path))

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
    @pytest.mark.parametrize(
        "url",
        [
            pytest.param("https://github.com/Org/repo", id="https_allowed"),
            pytest.param("git@github.com:Org/repo.git", id="ssh_allowed"),
        ],
    )
    def test_allowed_urls(self, url):
        _validate_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            pytest.param("ext::sh -c evil", id="ext_rejected"),
            pytest.param("file:///etc/passwd", id="file_rejected"),
        ],
    )
    def test_rejected_urls(self, url):
        with pytest.raises(SkillManagerError, match="Unsupported URL"):
            _validate_url(url)


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
        """An EOL-pinned checkout is updated in place, not re-cloned.

        Assert on argv[1], not on `"pull" in str(cmd)`: pytest names tmp_path
        after the test, so the repo path itself contains the substring "pull"
        and the old assertion passed no matter which git subcommand ran.
        """
        vendor = str(tmp_path / "vendor")
        repo_dir = os.path.join(vendor, "my-repo")
        os.makedirs(os.path.join(repo_dir, ".git"))

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(list(cmd))
            if "--get" in cmd:  # _eol_is_pinned: report the clone as pinned
                return subprocess.CompletedProcess(cmd, 0, stdout="false\n")
            return subprocess.CompletedProcess(cmd, 0, stdout="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        result_dir, name = clone_repo("https://github.com/Org/my-repo", vendor)
        assert result_dir == repo_dir
        subcommands = [c[1] for c in calls]
        assert "pull" in subcommands
        assert "clone" not in subcommands

    def test_existing_unpinned_repo_is_recloned_not_pulled(self, tmp_path, monkeypatch):
        """The mirror image: a checkout without the EOL pin must not be pulled."""
        vendor = str(tmp_path / "vendor")
        repo_dir = os.path.join(vendor, "my-repo")
        os.makedirs(os.path.join(repo_dir, ".git"))

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 0, stdout="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        clone_repo("https://github.com/Org/my-repo", vendor)
        flat = [tok for c in calls for tok in c]
        assert "clone" in flat
        assert "pull" not in flat

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
        result = repo_add("https://github.com/Org/my-repo", vendor, config, force=True)
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
            repo_add("https://github.com/Org/bad-repo", vendor, config, force=True)

    def test_many_skills_truncated(self, tmp_path, monkeypatch):
        vendor = str(tmp_path / "vendor")
        config = str(tmp_path / "config.json")
        skills = {f"skill-{i}": {"path": f"s{i}/", "description": f"S{i}"} for i in range(15)}

        def fake_clone(url, vdir):
            repo_dir = os.path.join(vdir, "big-repo")
            _write_manifest(repo_dir, skills)
            return repo_dir, "big-repo"

        monkeypatch.setattr("skill_repos.clone_repo", fake_clone)
        result = repo_add("https://github.com/Org/big-repo", vendor, config, force=True)
        assert "15 skills" in result
        assert "+5 more" in result

    def test_repo_add_third_party_requires_force(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        config = str(tmp_path / "config.json")
        with pytest.raises(SkillManagerError, match="Untrusted skill repository"):
            repo_add("https://github.com/Org/my-repo", vendor, config)

    def test_repo_add_builtin_skills_no_force_ok(self, tmp_path, monkeypatch):
        vendor = str(tmp_path / "vendor")
        config = str(tmp_path / "config.json")

        def fake_clone(url, vdir):
            repo_dir = os.path.join(vdir, "tausik-skills")
            _write_manifest(
                repo_dir,
                {"jira": {"path": "jira/", "description": "Jira"}},
            )
            return repo_dir, "tausik-skills"

        monkeypatch.setattr("skill_repos.clone_repo", fake_clone)
        result = repo_add("https://github.com/Kibertum/tausik-skills", vendor, config)
        assert "1 skill" in result


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

    @pytest.mark.parametrize(
        "skipped_path",
        [
            pytest.param(".claude-plugin", id="skips_claude_plugin"),
            pytest.param("hooks", id="skips_hooks"),
            pytest.param("__pycache__", id="skips_pycache"),
            pytest.param("CLAUDE.md", id="skips_claude_md"),
            pytest.param(".gitmodules", id="skips_gitmodules"),
        ],
    )
    def test_skips_filtered_path(self, tmp_path, skipped_path):
        repo, dst = self._setup_skill(tmp_path)
        copy_skill(repo, {"path": "myskill/"}, "myskill", dst)
        assert not os.path.exists(os.path.join(dst, "myskill", skipped_path))

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
        # No venv → deps will fail. The old contract returned the string
        # "Skill 'myskill' installed ... but dependency installation failed",
        # i.e. it said "installed" and exited 0. A caller reading the exit code
        # could not tell that the skill cannot run. Fail closed instead.
        with pytest.raises(SkillManagerError) as exc:
            install_skill("myskill", vendor, skills_dst, config, tausik_dir)
        message = str(exc.value)
        assert "NOT installed" in message
        assert "nonexistent-pkg" in message
        assert "pip install" in message, "tell the user how to recover"


class TestVenvResolution:
    """A bootstrapped project gets only `scripts/`, not `bootstrap/`.

    The old code imported `bootstrap_venv` from a sibling `bootstrap/` and
    swallowed the ImportError, so `requires` silently installed nothing in
    every real project. Every test here ran from the core checkout, where that
    sibling exists — which is exactly why none of them saw it.
    """

    def _hide_bootstrap(self, monkeypatch):
        import skill_manager

        real_isdir = os.path.isdir
        monkeypatch.setattr(
            skill_manager.os.path,
            "isdir",
            lambda path: False if "bootstrap" in str(path) else real_isdir(path),
        )

    def _fake_venv(self, tausik_dir: str) -> str:
        import sys as _sys

        sub, exe = ("Scripts", "python.exe") if _sys.platform == "win32" else ("bin", "python3")
        d = os.path.join(tausik_dir, "venv", sub)
        os.makedirs(d, exist_ok=True)
        py = os.path.join(d, exe)
        with open(py, "w") as f:
            f.write("")
        return py

    def test_resolves_venv_without_bootstrap_on_path(self, tmp_path, monkeypatch):
        from skill_manager import _resolve_venv_python

        self._hide_bootstrap(monkeypatch)
        tausik_dir = str(tmp_path / ".tausik")
        expected = self._fake_venv(tausik_dir)
        assert _resolve_venv_python(tausik_dir) == expected

    def test_missing_venv_returns_none(self, tmp_path, monkeypatch):
        from skill_manager import _resolve_venv_python

        self._hide_bootstrap(monkeypatch)
        assert _resolve_venv_python(str(tmp_path / ".tausik")) is None

    def test_deps_failure_keeps_signature_verdict(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        repo = os.path.join(vendor, "test-repo")
        _write_manifest(
            repo,
            {"myskill": {"path": "myskill/", "description": "T", "requires": ["nonexistent-pkg"]}},
        )
        _make_skill(repo, "myskill")
        skills_dst = str(tmp_path / "skills")
        os.makedirs(skills_dst)
        tausik_dir = str(tmp_path / ".tausik")
        os.makedirs(tausik_dir)
        config = str(tmp_path / "config.json")
        # Fail closed: a skill whose declared deps are missing is not installed.
        # This used to return a string and exit 0, so CI and MCP read it as success.
        with pytest.raises(SkillManagerError) as exc:
            install_skill("myskill", vendor, skills_dst, config, tausik_dir)
        message = str(exc.value)
        assert "NOT installed" in message
        assert "nonexistent-pkg" in message
        # An unsigned skill whose deps failed must still say it is unsigned.
        assert "UNSIGNED" in message or "WARNING" in message

    def test_deps_failure_leaves_no_half_install(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        repo = os.path.join(vendor, "test-repo")
        _write_manifest(
            repo,
            {"myskill": {"path": "myskill/", "description": "T", "requires": ["nonexistent-pkg"]}},
        )
        _make_skill(repo, "myskill")
        skills_dst = str(tmp_path / "skills")
        os.makedirs(skills_dst)
        tausik_dir = str(tmp_path / ".tausik")
        os.makedirs(tausik_dir)
        config = str(tmp_path / "config.json")

        with pytest.raises(SkillManagerError):
            install_skill("myskill", vendor, skills_dst, config, tausik_dir)

        assert not os.path.exists(os.path.join(skills_dst, "myskill")), (
            "copied files must not survive a failed install"
        )
        if os.path.exists(config):
            with open(config) as f:
                installed = json.load(f).get("bootstrap", {}).get("installed_skills", [])
            assert "myskill" not in installed

    def test_skill_without_requires_still_installs(self, tmp_path):
        """The fail-closed path must not touch the ordinary case."""
        vendor = str(tmp_path / "vendor")
        repo = os.path.join(vendor, "test-repo")
        _write_manifest(repo, {"plain": {"path": "plain/", "description": "T"}})
        _make_skill(repo, "plain")
        skills_dst = str(tmp_path / "skills")
        os.makedirs(skills_dst)
        tausik_dir = str(tmp_path / ".tausik")
        os.makedirs(tausik_dir)
        result = install_skill(
            "plain", vendor, skills_dst, str(tmp_path / "config.json"), tausik_dir
        )
        assert "installed" in result.lower()
        assert os.path.isfile(os.path.join(skills_dst, "plain", "SKILL.md"))


class TestPipFlagsAreRealFlags:
    """Every flag we hand pip must be accepted by a real pip, not just by a mock.

    v1.3.4 hardened `install_skill_deps` with `--no-config`, a flag no pip has
    ever had. `TestInstallDepsEnvHardening` asserted its presence while mocking
    `subprocess.run`, so it stayed green for releases while every `requires`
    install died on `no such option: --no-config` (rc=2).

    `pip install <flag> --help` parses options before printing, so it validates
    a flag offline: rc=0 when the flag exists, rc=2 when it does not.
    """

    def _pip_accepts(self, *flags: str) -> int:
        return subprocess.run(
            [sys.executable, "-m", "pip", "install", *flags, "--help"],
            capture_output=True,
            text=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
        ).returncode

    def test_probe_rejects_a_nonexistent_flag(self):
        """Guard the probe itself: it must be able to say no."""
        assert self._pip_accepts("--no-config") == 2, (
            "--no-config does not exist in any pip; if this passes, the probe is broken"
        )

    def test_every_flag_we_pass_is_accepted_by_real_pip(self, tmp_path, monkeypatch):
        from skill_manager import DEFAULT_PIP_INDEX_URL

        cmd = _capture_pip_cmd(tmp_path, monkeypatch)
        # Drop argv[0..3] (python -m pip install), the `--` separator and the pkgs.
        flags = cmd[4 : cmd.index("--")]
        assert "--isolated" in flags
        assert "--index-url" in flags
        assert DEFAULT_PIP_INDEX_URL in flags
        assert "--no-config" not in flags
        assert self._pip_accepts(*flags) == 0, f"real pip rejected {flags}"


def _capture_pip_cmd(tmp_path, monkeypatch) -> list:
    """Run install_skill_deps with subprocess mocked, return the argv it built."""
    from skill_manager import install_skill_deps

    fake_venv_py = str(tmp_path / "venv-py")
    with open(fake_venv_py, "w") as f:
        f.write("")

    bootstrap_dir = os.path.join(os.path.dirname(__file__), "..", "bootstrap")
    if bootstrap_dir not in sys.path:
        sys.path.insert(0, bootstrap_dir)
    import bootstrap_venv

    monkeypatch.setattr(bootstrap_venv, "get_venv_python", lambda _td: fake_venv_py)

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    install_skill_deps(
        repo_dir=str(tmp_path / "repo"),
        skill_info={"requires": ["requests"]},
        tausik_dir=str(tmp_path / ".tausik"),
    )
    return captured["cmd"]


class TestInstallDepsEnvHardening:
    """pip subprocess must run with --isolated + an explicit --index-url AND with
    PIP_INDEX_URL/PIP_EXTRA_INDEX_URL/PIP_TRUSTED_HOST stripped from its env, so a
    hostile parent env or pip.conf cannot redirect installs."""

    def _setup_install_skill_deps(self, tmp_path, monkeypatch):
        """Build the minimum to reach install_skill_deps' subprocess.run."""
        from skill_manager import install_skill_deps

        # Provide a fake venv python so install_skill_deps doesn't bail early
        fake_venv_py = str(tmp_path / "venv-py")
        with open(fake_venv_py, "w") as f:
            f.write("")  # contents irrelevant; we mock subprocess

        # Patch get_venv_python via the bootstrap_venv import path
        import sys

        bootstrap_dir = os.path.join(os.path.dirname(__file__), "..", "bootstrap")
        if bootstrap_dir not in sys.path:
            sys.path.insert(0, bootstrap_dir)
        import bootstrap_venv

        monkeypatch.setattr(bootstrap_venv, "get_venv_python", lambda _td: fake_venv_py)
        return install_skill_deps

    def test_pip_install_pins_the_index_on_the_command_line(self, tmp_path, monkeypatch):
        """Config files set optparse *defaults*; an explicit argument overrides them.

        `--isolated` alone is not enough: pip's `iter_config_files` yields GLOBAL
        and SITE unconditionally, so /etc/pip.conf and <venv>/pip.conf still load.
        """
        from skill_manager import DEFAULT_PIP_INDEX_URL

        cmd = _capture_pip_cmd(tmp_path, monkeypatch)
        assert "--isolated" in cmd
        assert cmd[cmd.index("--index-url") + 1] == DEFAULT_PIP_INDEX_URL

    def test_pip_install_runs_exactly_once(self, tmp_path, monkeypatch):
        """The old --no-config fallback invoked pip twice on every single install."""
        install_skill_deps = self._setup_install_skill_deps(tmp_path, monkeypatch)
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(subprocess, "run", fake_run)
        ok = install_skill_deps(
            repo_dir=str(tmp_path / "repo"),
            skill_info={"requires": ["requests"]},
            tausik_dir=str(tmp_path / ".tausik"),
        )
        assert ok is True
        assert len(calls) == 1, f"pip must run once, ran {len(calls)}×"

    def test_no_false_claim_about_old_pip(self, tmp_path, monkeypatch, capsys):
        """The removed fallback printed 'pip is too old for --no-config' on EVERY
        install. No pip is too old for it — no pip ever had it."""
        install_skill_deps = self._setup_install_skill_deps(tmp_path, monkeypatch)
        monkeypatch.setattr(
            subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0)
        )
        install_skill_deps(
            repo_dir=str(tmp_path / "repo"),
            skill_info={"requires": ["requests"]},
            tausik_dir=str(tmp_path / ".tausik"),
        )
        out = capsys.readouterr().out
        assert "too old" not in out
        assert "--no-config" not in out

    def test_pip_install_strips_pip_index_url_from_env(self, tmp_path, monkeypatch):
        install_skill_deps = self._setup_install_skill_deps(tmp_path, monkeypatch)
        # Set hostile vars in PARENT env
        monkeypatch.setenv("PIP_INDEX_URL", "https://evil.example.com/simple")
        monkeypatch.setenv("PIP_EXTRA_INDEX_URL", "https://evil2.example.com/")
        monkeypatch.setenv("PIP_TRUSTED_HOST", "evil.example.com")
        monkeypatch.setenv("PIP_FIND_LINKS", "https://evil.example.com/")
        monkeypatch.setenv("PIP_INDEX", "https://evil.example.com/")

        captured = {}

        def fake_run(cmd, **kwargs):
            captured["env"] = dict(kwargs.get("env") or {})
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(subprocess, "run", fake_run)
        install_skill_deps(
            repo_dir=str(tmp_path / "repo"),
            skill_info={"requires": ["requests"]},
            tausik_dir=str(tmp_path / ".tausik"),
        )
        env = captured["env"]
        assert "PIP_INDEX_URL" not in env, "PIP_INDEX_URL must be stripped — found: " + repr(
            env.get("PIP_INDEX_URL")
        )
        assert "PIP_EXTRA_INDEX_URL" not in env
        assert "PIP_TRUSTED_HOST" not in env
        assert "PIP_FIND_LINKS" not in env
        assert "PIP_INDEX" not in env

    def test_pip_install_preserves_other_env(self, tmp_path, monkeypatch):
        """Stripping is targeted — unrelated env vars (PATH, HOME) must survive."""
        install_skill_deps = self._setup_install_skill_deps(tmp_path, monkeypatch)
        monkeypatch.setenv("MY_UNRELATED_VAR", "preserved")

        captured = {}

        def fake_run(cmd, **kwargs):
            captured["env"] = dict(kwargs.get("env") or {})
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(subprocess, "run", fake_run)
        install_skill_deps(
            repo_dir=str(tmp_path / "repo"),
            skill_info={"requires": ["requests"]},
            tausik_dir=str(tmp_path / ".tausik"),
        )
        assert captured["env"].get("MY_UNRELATED_VAR") == "preserved"
        # PATH must survive too — pip needs it to find dependencies
        assert "PATH" in captured["env"] or "Path" in captured["env"]


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


class TestCloneEolPinning:
    """Decision #129 — the signed manifest hashes raw bytes, so a checkout that
    git line-ending-converted cannot reproduce the publisher's hashes.

    `git clone` is core's command, not the publisher's, so conversion is pinned
    off there. `-c` covers the clone only: without persisting the pin into the
    clone's local config, the next `git pull` re-reads the user's global
    core.autocrlf and re-converts. Both halves are exercised here.
    """

    def _git(self, cwd, *args, env=None):
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, env=env, timeout=60
        )

    def _origin(self, tmp_path, body: bytes = b"---\nname: s\n---\n# body\n"):
        src = tmp_path / "origin"
        (src / "myskill").mkdir(parents=True)
        (src / "myskill" / "SKILL.md").write_bytes(body)
        self._git(src, "init", "-q", "-b", "main")
        self._git(src, "config", "user.email", "a@b.c")
        self._git(src, "config", "user.name", "t")
        self._git(src, "config", "core.autocrlf", "false")
        self._git(src, "add", "-A")
        self._git(src, "commit", "-qm", "one")
        return src

    def _hostile_env(self, tmp_path):
        """A consumer whose GLOBAL git config converts to CRLF (Windows default).

        `-c core.autocrlf=true` would beat the clone's local config and test the
        wrong thing; GIT_CONFIG_GLOBAL is the honest simulation.
        """
        gcfg = tmp_path / "gitconfig-global"
        gcfg.write_text("[core]\n\tautocrlf = true\n")
        return {**os.environ, "GIT_CONFIG_GLOBAL": str(gcfg), "GIT_CONFIG_NOSYSTEM": "1"}

    def _clone(self, tmp_path, monkeypatch, src):
        import skill_manager

        monkeypatch.setattr(skill_manager, "_validate_url", lambda _u: None)
        for k, v in self._hostile_env(tmp_path).items():
            monkeypatch.setenv(k, v)
        # Path.as_uri(): "file:///" + str(path) becomes file:////tmp/... on POSIX,
        # where the path already starts with a slash. Windows-only code hid it.
        return skill_manager.clone_repo(src.as_uri(), str(tmp_path / "vendor"))

    def _sha(self, path) -> str:
        import hashlib

        return hashlib.sha256(open(path, "rb").read()).hexdigest()

    def test_clone_reproduces_publisher_bytes_under_hostile_global_config(
        self, tmp_path, monkeypatch
    ):
        src = self._origin(tmp_path)
        ref = self._sha(src / "myskill" / "SKILL.md")
        repo_dir, _ = self._clone(tmp_path, monkeypatch, src)
        got = self._sha(os.path.join(repo_dir, "myskill", "SKILL.md"))
        assert got == ref, "clone must not inherit the consumer's core.autocrlf"

    def test_pin_is_persisted_into_the_clone(self, tmp_path, monkeypatch):
        from skill_manager import _eol_is_pinned

        src = self._origin(tmp_path)
        repo_dir, _ = self._clone(tmp_path, monkeypatch, src)
        assert _eol_is_pinned(repo_dir), "a bare -c would not survive the next git pull"

    def test_pull_does_not_reconvert(self, tmp_path, monkeypatch):
        src = self._origin(tmp_path)
        repo_dir, _ = self._clone(tmp_path, monkeypatch, src)

        (src / "myskill" / "SKILL.md").write_bytes(b"---\nname: s\n---\n# body\nmore\n")
        self._git(src, "add", "-A")
        self._git(src, "commit", "-qm", "two")
        ref = self._sha(src / "myskill" / "SKILL.md")

        repo_dir, _ = self._clone(tmp_path, monkeypatch, src)  # takes the pull path
        assert self._sha(os.path.join(repo_dir, "myskill", "SKILL.md")) == ref

    def test_stale_unpinned_cache_is_recloned(self, tmp_path, monkeypatch, capsys):
        """A checkout made before this fix may hold converted bytes. Serving it
        silently would fail signature verification on an untouched file."""
        from skill_manager import _eol_is_pinned

        src = self._origin(tmp_path)
        repo_dir, _ = self._clone(tmp_path, monkeypatch, src)
        self._git(repo_dir, "config", "--unset", "core.autocrlf")
        assert not _eol_is_pinned(repo_dir)

        repo_dir, _ = self._clone(tmp_path, monkeypatch, src)
        assert "Re-cloning" in capsys.readouterr().out
        assert _eol_is_pinned(repo_dir)
        assert self._sha(os.path.join(repo_dir, "myskill", "SKILL.md")) == self._sha(
            src / "myskill" / "SKILL.md"
        )


class TestRmtreeForce:
    """3.3 — git marks pack files read-only; plain rmtree raises PermissionError
    on Windows and leaves the vendor cache alive."""

    def test_removes_readonly_files(self, tmp_path):
        import stat as _stat

        from skill_manager import rmtree_force

        pack = tmp_path / "repo" / ".git" / "objects" / "pack"
        pack.mkdir(parents=True)
        f = pack / "x.pack"
        f.write_bytes(b"x")
        os.chmod(f, _stat.S_IREAD)

        rmtree_force(str(tmp_path / "repo"))
        assert not (tmp_path / "repo").exists()
