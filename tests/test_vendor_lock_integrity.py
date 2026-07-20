"""Vendor supply-chain integrity (vendor-lock-integrity).

The .lock file recorded a sha256 of every tarball and never read it back:
sync_deps decided "up-to-date" from the ref string alone. These tests cover the
missing half — an expected digest declared in skills.json, a hard refusal when
it does not match, and a loud signal when nothing pins the dependency at all.

No network: _download_tarball is patched everywhere.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_BOOTSTRAP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
if _BOOTSTRAP not in sys.path:
    sys.path.insert(0, _BOOTSTRAP)

import bootstrap_vendor  # noqa: E402
from bootstrap_vendor import _read_lock, sync_deps  # noqa: E402
from bootstrap_vendor_integrity import (  # noqa: E402
    digest_mismatch,
    is_pinned_ref,
    mutable_ref_warning,
    sha_change_note,
    tarball_digest,
)
from test_vendor import _make_tarball  # noqa: E402


def _lib(tmp_path, spec: dict) -> str:
    """A library dir whose skills.json declares one external skill."""
    lib = tmp_path / "lib"
    lib.mkdir(exist_ok=True)
    (lib / "skills.json").write_text(
        json.dumps({"external_skills": {"seo": spec}}), encoding="utf-8"
    )
    return str(lib)


def _patch_download(monkeypatch, tarball: bytes):
    monkeypatch.setattr(bootstrap_vendor, "_download_tarball", lambda repo, ref: tarball)


def _forbid_download(monkeypatch):
    def _boom(repo, ref):
        raise AssertionError("network was touched when the lock should have short-circuited")

    monkeypatch.setattr(bootstrap_vendor, "_download_tarball", _boom)


class TestPureHelpers:
    def test_digest_is_stable(self):
        assert tarball_digest(b"abc") == tarball_digest(b"abc")
        assert tarball_digest(b"abc") != tarball_digest(b"abd")

    def test_no_expected_digest_is_not_a_mismatch(self):
        assert digest_mismatch("seo", "aa", None) is None

    def test_mismatch_names_both_digests(self):
        msg = digest_mismatch("seo", "aaaa", "bbbb")
        assert msg is not None
        assert "aaaa" in msg and "bbbb" in msg and "seo" in msg

    @pytest.mark.parametrize("ref", ["main", "master", "v1.5.0", "abc123"])
    def test_unpinned_refs_warn(self, ref):
        assert mutable_ref_warning("seo", "o/r", ref, None) is not None

    def test_commit_sha_does_not_warn(self):
        assert is_pinned_ref("a" * 40)
        assert mutable_ref_warning("seo", "o/r", "a" * 40, None) is None

    def test_declared_digest_settles_a_moving_ref(self):
        assert mutable_ref_warning("seo", "o/r", "main", "deadbeef") is None

    def test_sha_change_note_only_on_real_change(self):
        assert sha_change_note(None, "bb") is None
        assert sha_change_note("bb", "bb") is None
        assert sha_change_note("aa", "bb") == {"from": "aa", "to": "bb"}


class TestDeclaredDigest:
    def test_matching_digest_syncs(self, tmp_path, monkeypatch):
        tarball = _make_tarball({"seo/SKILL.md": "# SEO"})
        _patch_download(monkeypatch, tarball)
        lib = _lib(
            tmp_path,
            {"repo": "o/r", "ref": "main", "sha256": tarball_digest(tarball)},
        )
        vendor = str(tmp_path / "vendor")

        result = sync_deps(lib, vendor)

        assert result["seo"]["status"] == "synced"
        assert os.path.isfile(os.path.join(vendor, "seo", "seo", "SKILL.md"))

    def test_mismatched_digest_refuses_and_writes_nothing(self, tmp_path, monkeypatch):
        """The whole point: a tampered artifact must not reach disk."""
        _patch_download(monkeypatch, _make_tarball({"seo/SKILL.md": "# evil"}))
        lib = _lib(tmp_path, {"repo": "o/r", "ref": "main", "sha256": "f" * 64})
        vendor = str(tmp_path / "vendor")

        result = sync_deps(lib, vendor)

        assert result["seo"]["status"] == "error"
        assert "integrity check FAILED" in result["seo"]["error"]
        assert not os.path.exists(os.path.join(vendor, "seo", "seo"))
        assert _read_lock(vendor, "seo") is None


class TestMutableRefWarning:
    def test_unpinned_branch_warns_but_syncs(self, tmp_path, monkeypatch):
        _patch_download(monkeypatch, _make_tarball({"seo/SKILL.md": "# SEO"}))
        lib = _lib(tmp_path, {"repo": "o/r", "ref": "main"})

        result = sync_deps(lib, str(tmp_path / "vendor"))

        assert result["seo"]["status"] == "synced"
        assert "moving target" in result["seo"]["warning"]

    def test_declared_digest_silences_the_warning(self, tmp_path, monkeypatch):
        tarball = _make_tarball({"seo/SKILL.md": "# SEO"})
        _patch_download(monkeypatch, tarball)
        lib = _lib(
            tmp_path,
            {"repo": "o/r", "ref": "main", "sha256": tarball_digest(tarball)},
        )

        result = sync_deps(lib, str(tmp_path / "vendor"))

        assert "warning" not in result["seo"]


class TestLockBecomesMeaningful:
    def test_force_resync_reports_changed_content(self, tmp_path, monkeypatch):
        """A moving ref that moved under us is now visible, not silent."""
        vendor = str(tmp_path / "vendor")
        lib = _lib(tmp_path, {"repo": "o/r", "ref": "main"})

        first = _make_tarball({"seo/SKILL.md": "# SEO"})
        _patch_download(monkeypatch, first)
        sync_deps(lib, vendor)

        second = _make_tarball({"seo/SKILL.md": "# SEO tampered"})
        _patch_download(monkeypatch, second)
        result = sync_deps(lib, vendor, force=True)

        assert result["seo"]["sha_changed"] == {
            "from": tarball_digest(first),
            "to": tarball_digest(second),
        }

    def test_force_resync_of_identical_content_is_quiet(self, tmp_path, monkeypatch):
        vendor = str(tmp_path / "vendor")
        lib = _lib(tmp_path, {"repo": "o/r", "ref": "main"})
        tarball = _make_tarball({"seo/SKILL.md": "# SEO"})
        _patch_download(monkeypatch, tarball)

        sync_deps(lib, vendor)
        result = sync_deps(lib, vendor, force=True)

        assert "sha_changed" not in result["seo"]

    def test_matching_lock_short_circuits_without_network(self, tmp_path, monkeypatch):
        """Regression: the existing cache path must keep working untouched."""
        vendor = str(tmp_path / "vendor")
        lib = _lib(tmp_path, {"repo": "o/r", "ref": "main"})
        _patch_download(monkeypatch, _make_tarball({"seo/SKILL.md": "# SEO"}))
        sync_deps(lib, vendor)

        _forbid_download(monkeypatch)
        result = sync_deps(lib, vendor)

        assert result["seo"]["status"] == "up-to-date"
