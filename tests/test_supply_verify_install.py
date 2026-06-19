"""Tests for install-time supply-chain verification (v15-supplychain-verify-install)."""

from __future__ import annotations

import json
import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import crypto_keys  # noqa: E402
from skill_manager import SkillManagerError, install_skill  # noqa: E402
from skill_repos import (  # noqa: E402
    get_repo_pinned_pubkey,
    update_config_repo_add,
    update_config_repo_trust,
)
from supply_sign import sign_artifact  # noqa: E402
from supply_verify_install import (  # noqa: E402
    LEVEL_BLOCK,
    LEVEL_OK,
    LEVEL_WARN,
    check_skill_signature,
    decode_pubkey,
)


@pytest.fixture
def publisher(tmp_path):
    pub_dir = tmp_path / "publisher"
    pub_dir.mkdir()
    crypto_keys.init_keys(str(pub_dir))
    public = crypto_keys.load_public(str(pub_dir))
    return str(pub_dir), f"ed25519:{public.hex()}"


@pytest.fixture
def repo(tmp_path):
    """Vendored skill repo with one skill."""
    vendor = tmp_path / "vendor"
    repo_dir = vendor / "test-repo"
    skill = repo_dir / "myskill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    (repo_dir / "tausik-skills.json").write_text(
        json.dumps(
            {
                "format": "tausik-skills",
                "skills": {"myskill": {"path": "myskill/", "description": "t"}},
            }
        ),
        encoding="utf-8",
    )
    return str(vendor), str(skill)


@pytest.fixture
def env(tmp_path, repo):
    vendor, skill_src = repo
    skills_dst = tmp_path / "skills"
    skills_dst.mkdir()
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    config = str(tausik_dir / "config.json")
    update_config_repo_add(config, "test-repo", "https://example.invalid/repo")
    return {
        "vendor": vendor,
        "skill_src": skill_src,
        "skills_dst": str(skills_dst),
        "config": config,
        "tausik_dir": str(tausik_dir),
    }


def _install(env):
    return install_skill(
        "myskill", env["vendor"], env["skills_dst"], env["config"], env["tausik_dir"]
    )


class TestDecodePubkey:
    def test_prefixed_and_bare(self):
        key = "ab" * 32
        assert decode_pubkey(f"ed25519:{key}") == bytes.fromhex(key)
        assert decode_pubkey(key) == bytes.fromhex(key)

    @pytest.mark.parametrize("bad", ["", "rsa:aabb", "ed25519:zz", "ed25519:aabb", None])
    def test_bad_keys_raise(self, bad):
        with pytest.raises(ValueError):
            decode_pubkey(bad)


class TestTrustPin:
    def test_trust_pin_roundtrip(self, env, publisher):
        _, pubkey = publisher
        assert get_repo_pinned_pubkey(env["config"], "test-repo") is None
        update_config_repo_trust(env["config"], "test-repo", pubkey)
        assert get_repo_pinned_pubkey(env["config"], "test-repo") == pubkey

    def test_trust_unknown_repo_rejected(self, env, publisher):
        with pytest.raises(SkillManagerError, match="not configured"):
            update_config_repo_trust(env["config"], "ghost", publisher[1])

    def test_trust_bad_key_rejected(self, env):
        with pytest.raises(SkillManagerError, match="unusable"):
            update_config_repo_trust(env["config"], "test-repo", "ed25519:nope")


class TestInstallScenarios:
    def test_unsigned_warns_but_installs(self, env):
        msg = _install(env)
        assert "installed" in msg and "UNSIGNED" in msg
        assert os.path.isdir(os.path.join(env["skills_dst"], "myskill"))

    def test_signed_unpinned_warns_but_installs(self, env, publisher):
        pub_dir, _ = publisher
        sign_artifact(pub_dir, env["skill_src"])
        msg = _install(env)
        assert "installed" in msg and "no publisher key is pinned" in msg

    def test_signed_pinned_verified(self, env, publisher):
        pub_dir, pubkey = publisher
        sign_artifact(pub_dir, env["skill_src"])
        update_config_repo_trust(env["config"], "test-repo", pubkey)
        msg = _install(env)
        assert "signature verified" in msg
        assert os.path.isdir(os.path.join(env["skills_dst"], "myskill"))

    def test_tampered_skill_blocked_nothing_copied(self, env, publisher):
        pub_dir, pubkey = publisher
        sign_artifact(pub_dir, env["skill_src"])
        update_config_repo_trust(env["config"], "test-repo", pubkey)
        with open(os.path.join(env["skill_src"], "SKILL.md"), "a", encoding="utf-8") as f:
            f.write("rm -rf /\n")
        with pytest.raises(SkillManagerError, match="FAILED"):
            _install(env)
        assert not os.path.exists(os.path.join(env["skills_dst"], "myskill"))

    def test_foreign_signature_blocked(self, env, publisher, tmp_path):
        attacker = tmp_path / "attacker"
        attacker.mkdir()
        crypto_keys.init_keys(str(attacker))
        sign_artifact(str(attacker), env["skill_src"])  # attacker re-signs
        update_config_repo_trust(env["config"], "test-repo", publisher[1])
        with pytest.raises(SkillManagerError, match="FAILED"):
            _install(env)

    def test_corrupt_pinned_key_blocks(self, env, publisher):
        pub_dir, _ = publisher
        sign_artifact(pub_dir, env["skill_src"])
        # bypass update_config_repo_trust validation to simulate config rot
        cfg = json.loads(open(env["config"], encoding="utf-8").read())
        cfg["skill_repos"]["test-repo"]["pubkey"] = "ed25519:rotten"
        open(env["config"], "w", encoding="utf-8").write(json.dumps(cfg))
        with pytest.raises(SkillManagerError, match="unusable"):
            _install(env)


class TestCheckLevels:
    def test_levels_directly(self, env, publisher):
        pub_dir, pubkey = publisher
        level, _ = check_skill_signature(env["skill_src"], "r", None)
        assert level == LEVEL_WARN  # unsigned
        sign_artifact(pub_dir, env["skill_src"])
        assert check_skill_signature(env["skill_src"], "r", None)[0] == LEVEL_WARN
        assert check_skill_signature(env["skill_src"], "r", pubkey)[0] == LEVEL_OK
        assert check_skill_signature(env["skill_src"], "r", "garbage")[0] == LEVEL_BLOCK
