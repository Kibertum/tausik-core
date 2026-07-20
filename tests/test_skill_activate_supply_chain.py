"""`skill activate` must be no weaker than `skill install`.

Regression suite for skill-activate-signature-bypass: the publisher-signature
check lived only on the install path, so a skill that install refused went in
cleanly through activate — which also copied hooks/ and .claude-plugin/ that
install strips. Every test here fails on the pre-fix code.
"""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import crypto_keys  # noqa: E402
from project_service import ProjectService  # noqa: E402
from skill_repos import update_config_repo_add, update_config_repo_trust  # noqa: E402
from supply_sign import sign_artifact  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


def _make_skill(root, repo_name, skill_name="myskill"):
    """A vendor repo holding one skill. Returns the skill directory."""
    skill = root / repo_name / skill_name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    return skill


@pytest.fixture
def env(tmp_path):
    """Project layout activate expects: <proj>/.claude/skills as destination.

    project_dir is derived as dirname(dirname(skills_dst)), so nothing named
    `skills` or `skills-official` may sit beside it or the first-party lookup
    would shadow the vendor one.
    """
    proj = tmp_path / "proj"
    vendor = tmp_path / "vendor"
    skills_dst = proj / ".claude" / "skills"
    skills_dst.mkdir(parents=True)
    vendor.mkdir()
    tausik_dir = proj / ".tausik"
    tausik_dir.mkdir()
    config = str(tausik_dir / "config.json")
    update_config_repo_add(config, "test-repo", "https://example.invalid/repo")
    return {
        "proj": proj,
        "vendor": str(vendor),
        "vendor_path": vendor,
        "skills_dst": str(skills_dst),
        "config": config,
    }


def _activate(env, name="myskill", config=True):
    return ProjectService.skill_activate(
        name,
        env["vendor"],
        env["skills_dst"],
        str(env["proj"] / "lib-skills"),
        env["config"] if config else None,
    )


@pytest.fixture
def publisher(tmp_path):
    pub_dir = tmp_path / "publisher"
    pub_dir.mkdir()
    crypto_keys.init_keys(str(pub_dir))
    return str(pub_dir), f"ed25519:{crypto_keys.load_public(str(pub_dir)).hex()}"


class TestSignatureEnforced:
    def test_unsigned_warns_but_activates(self, env):
        """Adoption path: unsigned is a warning, same as install. Not silence."""
        _make_skill(env["vendor_path"], "test-repo")
        msg = _activate(env)
        assert "UNSIGNED" in msg
        assert os.path.isdir(os.path.join(env["skills_dst"], "myskill"))

    def test_signed_and_pinned_activates_without_warning(self, env, publisher):
        skill = _make_skill(env["vendor_path"], "test-repo")
        pub_dir, pubkey = publisher
        sign_artifact(pub_dir, str(skill))
        update_config_repo_trust(env["config"], "test-repo", pubkey)
        msg = _activate(env)
        assert "WARNING" not in msg
        assert os.path.isdir(os.path.join(env["skills_dst"], "myskill"))

    def test_tampered_after_signing_is_refused(self, env, publisher):
        """The core bypass: install blocks this, activate used to wave it in."""
        skill = _make_skill(env["vendor_path"], "test-repo")
        pub_dir, pubkey = publisher
        sign_artifact(pub_dir, str(skill))
        update_config_repo_trust(env["config"], "test-repo", pubkey)
        (skill / "SKILL.md").write_text("# skill\nrm -rf /\n", encoding="utf-8")

        with pytest.raises(ServiceError, match="Refusing to activate"):
            _activate(env)
        # Nothing may land on disk when the verdict is "refuse".
        assert not os.path.exists(os.path.join(env["skills_dst"], "myskill"))

    def test_no_config_still_checks(self, env):
        """No config = nowhere to pin a key. That is unknown, not verified."""
        _make_skill(env["vendor_path"], "test-repo")
        msg = _activate(env, config=False)
        assert "WARNING" in msg


class TestCopyFilter:
    def test_hooks_and_plugin_manifest_never_reach_the_tree(self, env):
        skill = _make_skill(env["vendor_path"], "test-repo")
        (skill / "hooks").mkdir()
        (skill / "hooks" / "pre.py").write_text("evil\n", encoding="utf-8")
        (skill / ".claude-plugin").mkdir()
        (skill / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
        (skill / "CLAUDE.md").write_text("override\n", encoding="utf-8")
        (skill / ".gitignore").write_text("*\n", encoding="utf-8")
        (skill / "references").mkdir()
        (skill / "references" / "doc.md").write_text("keep me\n", encoding="utf-8")

        _activate(env)

        dst = os.path.join(env["skills_dst"], "myskill")
        assert not os.path.exists(os.path.join(dst, "hooks"))
        assert not os.path.exists(os.path.join(dst, ".claude-plugin"))
        assert not os.path.exists(os.path.join(dst, "CLAUDE.md"))
        assert not os.path.exists(os.path.join(dst, ".gitignore"))
        # The filter strips threats, not content.
        assert os.path.isfile(os.path.join(dst, "references", "doc.md"))
        assert os.path.isfile(os.path.join(dst, "SKILL.md"))


class TestNameCollision:
    def test_two_repos_publishing_one_name_is_an_error(self, env):
        """First-wins let an already-added repo shadow a popular skill."""
        _make_skill(env["vendor_path"], "aaa-repo")
        _make_skill(env["vendor_path"], "zzz-repo")

        with pytest.raises(ServiceError, match="more than one repo"):
            _activate(env)

    def test_collision_message_names_every_candidate(self, env):
        _make_skill(env["vendor_path"], "aaa-repo")
        _make_skill(env["vendor_path"], "zzz-repo")

        with pytest.raises(ServiceError) as exc:
            _activate(env)
        assert "aaa-repo" in str(exc.value)
        assert "zzz-repo" in str(exc.value)

    def test_lookup_is_deterministic(self, env):
        """Single match resolves to (path, repo_name) — the key for the pin."""
        _make_skill(env["vendor_path"], "only-repo")
        found = ProjectService._find_vendor_skill(env["vendor"], "myskill")
        assert found is not None
        skill_path, repo_name = found
        assert repo_name == "only-repo"
        assert skill_path.endswith("myskill")


class TestFirstPartySkills:
    def test_official_skill_activates_without_a_signature(self, env):
        """Framework skills ship in-repo: nothing signs them, nothing should."""
        official = env["proj"] / "skills-official" / "offskill"
        official.mkdir(parents=True)
        (official / "SKILL.md").write_text("# official\n", encoding="utf-8")

        msg = _activate(env, name="offskill")
        assert "WARNING" not in msg
        assert os.path.isfile(os.path.join(env["skills_dst"], "offskill", "SKILL.md"))
