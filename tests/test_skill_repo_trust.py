"""3.2 / 3.3 — re-adding a repo must not silently un-pin it, and removing a repo
must survive git's read-only pack files on Windows.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from skill_manager import SkillManagerError  # noqa: E402
from skill_repos import (  # noqa: E402
    get_repo_pinned_pubkey,
    load_config,
    repo_remove,
    save_config,
    update_config_repo_add,
)

URL = "https://gitlab.example.com/team/skills.git"
OTHER_URL = "https://gitlab.example.com/attacker/skills.git"
PUBKEY = "AAAAC3NzaC1lZDI1NTE5AAAAIPinnedPublisherKeyForTests"


def _pin(config_path: str, name: str, key: str = PUBKEY) -> None:
    """Pin directly; update_config_repo_trust validates the key, which is a
    different concern from the one under test."""
    cfg = load_config(config_path)
    cfg["skill_repos"][name]["pubkey"] = key
    save_config(config_path, cfg)


class TestRepoAddPreservesPin:
    def test_readd_same_url_keeps_pin(self, tmp_path):
        """The reported bug. Not about --force: any re-add dropped the key."""
        config = str(tmp_path / "config.json")
        update_config_repo_add(config, "skills", URL)
        _pin(config, "skills")
        assert get_repo_pinned_pubkey(config, "skills") == PUBKEY

        dropped = update_config_repo_add(config, "skills", URL)
        assert dropped is False
        assert get_repo_pinned_pubkey(config, "skills") == PUBKEY

    def test_changed_url_drops_pin_and_says_so(self, tmp_path):
        """A different URL is a different repository; the old key must not vouch."""
        config = str(tmp_path / "config.json")
        update_config_repo_add(config, "skills", URL)
        _pin(config, "skills")

        dropped = update_config_repo_add(config, "skills", OTHER_URL)
        assert dropped is True, "silently keeping the pin would trust a new origin"
        assert get_repo_pinned_pubkey(config, "skills") is None
        assert load_config(config)["skill_repos"]["skills"]["url"] == OTHER_URL

    def test_first_add_reports_no_drop(self, tmp_path):
        config = str(tmp_path / "config.json")
        assert update_config_repo_add(config, "skills", URL) is False

    def test_other_fields_survive(self, tmp_path):
        config = str(tmp_path / "config.json")
        update_config_repo_add(config, "skills", URL)
        cfg = load_config(config)
        cfg["skill_repos"]["skills"]["default"] = True
        save_config(config, cfg)

        update_config_repo_add(config, "skills", URL)
        assert load_config(config)["skill_repos"]["skills"]["default"] is True

    def test_legacy_bare_url_string_entry(self, tmp_path):
        """Older configs stored the URL as a plain string."""
        config = str(tmp_path / "config.json")
        with open(config, "w") as f:
            json.dump({"skill_repos": {"skills": URL}}, f)
        assert update_config_repo_add(config, "skills", URL) is False
        assert load_config(config)["skill_repos"]["skills"]["url"] == URL


class TestRepoRemoveReadOnlyPacks:
    def _fake_clone(self, vendor: str, name: str) -> str:
        repo = os.path.join(vendor, name)
        pack = os.path.join(repo, ".git", "objects", "pack")
        os.makedirs(pack)
        for fname in ("x.pack", "x.idx"):
            p = os.path.join(pack, fname)
            with open(p, "wb") as f:
                f.write(b"x")
            os.chmod(p, stat.S_IREAD)  # git marks packs read-only
        return repo

    def test_remove_survives_readonly_packs(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        config = str(tmp_path / "config.json")
        update_config_repo_add(config, "skills", URL)
        repo = self._fake_clone(vendor, "skills")

        msg = repo_remove("skills", vendor, config)
        assert "removed" in msg
        assert not os.path.exists(repo), "a surviving cache keeps serving the stale skill"
        assert "skills" not in load_config(config).get("skill_repos", {})

    def test_removal_failure_leaves_config_untouched(self, tmp_path, monkeypatch):
        """rmtree used to raise before the config was updated. Now the failure is
        explicit — but the config must still reflect reality: repo not removed."""
        import skill_repos

        vendor = str(tmp_path / "vendor")
        config = str(tmp_path / "config.json")
        update_config_repo_add(config, "skills", URL)
        self._fake_clone(vendor, "skills")

        import skill_manager

        monkeypatch.setattr(
            skill_manager, "rmtree_force", lambda _p: (_ for _ in ()).throw(OSError("locked"))
        )
        with pytest.raises(SkillManagerError, match="could not remove"):
            skill_repos.repo_remove("skills", vendor, config)
        assert "skills" in load_config(config)["skill_repos"]

    def test_remove_when_never_cloned(self, tmp_path):
        vendor = str(tmp_path / "vendor")
        config = str(tmp_path / "config.json")
        update_config_repo_add(config, "skills", URL)
        assert "removed" in repo_remove("skills", vendor, config)


class TestRealGitPacksAreReadOnly:
    """Guards the premise of 3.3 rather than assuming it."""

    def test_git_writes_readonly_packs(self, tmp_path):
        src = tmp_path / "origin"
        src.mkdir()
        (src / "f.txt").write_text("x")

        def g(cwd, *a):
            return subprocess.run(["git", *a], cwd=str(cwd), capture_output=True, timeout=60)

        g(src, "init", "-q", "-b", "main")
        g(src, "config", "user.email", "a@b.c")
        g(src, "config", "user.name", "t")
        g(src, "add", "-A")
        g(src, "commit", "-qm", "one")

        dst = tmp_path / "clone"
        # Path.as_uri(): "file:///" + str(path) becomes file:////tmp/... on POSIX.
        subprocess.run(
            ["git", "clone", "-q", src.as_uri(), str(dst)],
            capture_output=True,
            timeout=120,
        )
        pack_dir = dst / ".git" / "objects" / "pack"
        packs = list(pack_dir.glob("*")) if pack_dir.is_dir() else []
        if not packs:
            pytest.skip("this git clones loose objects, no pack files to inspect")
        assert any(not os.access(p, os.W_OK) for p in packs), (
            "expected at least one read-only pack file"
        )
