"""Tests for scripts/supply_sign.py (v15-supplychain-sign-release).

AC coverage: deterministic manifest, sign -> .tausik-signature.json,
verify on intact dir, tamper detection (modified/added/removed file),
corrupt signature file, no-key error.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import crypto_keys  # noqa: E402
from supply_sign import (  # noqa: E402
    MANIFEST_SCHEMA,
    SIGNATURE_FILENAME,
    SupplySignError,
    build_artifact_manifest,
    sign_artifact,
    verify_signed_dir,
)


@pytest.fixture
def keyed_project(tmp_path):
    crypto_keys.init_keys(str(tmp_path))
    return str(tmp_path)


@pytest.fixture
def skill_dir(tmp_path):
    d = tmp_path / "myskill"
    (d / "sub").mkdir(parents=True)
    (d / "SKILL.md").write_text("# My skill\n", encoding="utf-8")
    (d / "sub" / "helper.py").write_text("X = 1\n", encoding="utf-8")
    (d / ".git").mkdir()
    (d / ".git" / "HEAD").write_text("ref", encoding="utf-8")
    return str(d)


class TestManifest:
    def test_deterministic_and_excludes_noise(self, skill_dir):
        m1 = build_artifact_manifest(skill_dir)
        m2 = build_artifact_manifest(skill_dir)
        assert m1 == m2
        assert m1["schema"] == MANIFEST_SCHEMA
        assert m1["name"] == "myskill"
        paths = [f["path"] for f in m1["files"]]
        assert paths == sorted(paths) == ["SKILL.md", "sub/helper.py"]

    def test_signature_file_excluded_from_manifest(self, keyed_project, skill_dir):
        sign_artifact(keyed_project, skill_dir)
        paths = [f["path"] for f in build_artifact_manifest(skill_dir)["files"]]
        assert SIGNATURE_FILENAME not in paths

    def test_empty_dir_rejected(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(SupplySignError, match="nothing to sign"):
            build_artifact_manifest(str(empty))

    def test_missing_dir_rejected(self, tmp_path):
        with pytest.raises(SupplySignError, match="not a directory"):
            build_artifact_manifest(str(tmp_path / "ghost"))


class TestSignAndVerify:
    def test_sign_then_verify_intact(self, keyed_project, skill_dir):
        info = sign_artifact(keyed_project, skill_dir)
        assert info["files"] == 2
        assert os.path.isfile(os.path.join(skill_dir, SIGNATURE_FILENAME))
        public = crypto_keys.load_public(keyed_project)
        valid, detail = verify_signed_dir(skill_dir, public)
        assert valid is True and "VALID" in detail

    def test_modified_file_detected(self, keyed_project, skill_dir):
        sign_artifact(keyed_project, skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "a", encoding="utf-8") as f:
            f.write("backdoor\n")
        valid, detail = verify_signed_dir(skill_dir, crypto_keys.load_public(keyed_project))
        assert valid is False and "modified: SKILL.md" in detail

    def test_added_file_detected(self, keyed_project, skill_dir):
        sign_artifact(keyed_project, skill_dir)
        with open(os.path.join(skill_dir, "evil.py"), "w", encoding="utf-8") as f:
            f.write("import os\n")
        valid, detail = verify_signed_dir(skill_dir, crypto_keys.load_public(keyed_project))
        assert valid is False and "added: evil.py" in detail

    def test_removed_file_detected(self, keyed_project, skill_dir):
        sign_artifact(keyed_project, skill_dir)
        os.remove(os.path.join(skill_dir, "sub", "helper.py"))
        valid, detail = verify_signed_dir(skill_dir, crypto_keys.load_public(keyed_project))
        assert valid is False and "removed: sub/helper.py" in detail

    def test_tampered_signature_payload_detected(self, keyed_project, skill_dir):
        sign_artifact(keyed_project, skill_dir)
        sig_path = os.path.join(skill_dir, SIGNATURE_FILENAME)
        env = json.loads(open(sig_path, encoding="utf-8").read())
        env["receipt"]["files"][0]["sha256"] = "0" * 64
        open(sig_path, "w", encoding="utf-8").write(json.dumps(env))
        valid, detail = verify_signed_dir(skill_dir, crypto_keys.load_public(keyed_project))
        assert valid is False and "INVALID" in detail

    def test_unsigned_dir_reports_clearly(self, keyed_project, skill_dir):
        valid, detail = verify_signed_dir(skill_dir, crypto_keys.load_public(keyed_project))
        assert valid is False and "unsigned" in detail

    def test_corrupt_signature_file_no_crash(self, keyed_project, skill_dir):
        open(os.path.join(skill_dir, SIGNATURE_FILENAME), "w", encoding="utf-8").write("{nope")
        valid, detail = verify_signed_dir(skill_dir, crypto_keys.load_public(keyed_project))
        assert valid is False and "corrupt" in detail

    def test_foreign_key_rejected(self, keyed_project, skill_dir, tmp_path_factory):
        sign_artifact(keyed_project, skill_dir)
        other = str(tmp_path_factory.mktemp("other"))
        crypto_keys.init_keys(other)
        valid, _ = verify_signed_dir(skill_dir, crypto_keys.load_public(other))
        assert valid is False

    def test_no_project_key_raises(self, tmp_path, skill_dir):
        with pytest.raises(SupplySignError, match="key"):
            sign_artifact(str(tmp_path / "keyless"), skill_dir)

    def test_resign_after_change_restores_validity(self, keyed_project, skill_dir):
        sign_artifact(keyed_project, skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "a", encoding="utf-8") as f:
            f.write("v2\n")
        sign_artifact(keyed_project, skill_dir)
        valid, _ = verify_signed_dir(skill_dir, crypto_keys.load_public(keyed_project))
        assert valid is True
