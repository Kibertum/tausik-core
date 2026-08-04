"""Signing must refuse a worktree whose bytes differ from the repository's.

Decision #129: the signed manifest hashes raw bytes and is NOT normalised, so a
signature made over git-converted bytes verifies only where the same conversion
happens. The publisher-side guard catches that before the signature ships.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from supply_eol import (  # noqa: E402
    WorktreeDriftError,
    assert_worktree_matches_repo,
    drifted_files,
    is_git_worktree,
)


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", timeout=60)


def _origin(tmp_path):
    """A repo whose committed bytes use LF, containing one text + one binary file."""
    origin = tmp_path / "origin"
    (origin / "noslop").mkdir(parents=True)
    (origin / "noslop" / "SKILL.md").write_bytes(b"---\nname: noslop\n---\n# body\n")
    (origin / "noslop" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x01")
    _git(origin, "init", "-q", "-b", "main")
    _git(origin, "config", "user.email", "a@b.c")
    _git(origin, "config", "user.name", "t")
    _git(origin, "config", "core.autocrlf", "false")
    _git(origin, "add", "-A")
    _git(origin, "commit", "-qm", "one")
    return origin


def _clone(tmp_path, origin, name, *cfg):
    dst = tmp_path / name
    # `Path.as_uri()`, not `"file:///" + str(path)`: the manual form yields
    # `file:////tmp/...` on POSIX (four slashes) because the path already starts
    # with one. It only looked right because it was only ever run on Windows.
    subprocess.run(
        ["git", *cfg, "clone", "-q", origin.as_uri(), str(dst)],
        capture_output=True,
        timeout=120,
    )
    return dst


ALL = ["SKILL.md", "logo.png"]


class TestDriftDetection:
    def test_converted_worktree_is_detected(self, tmp_path):
        origin = _origin(tmp_path)
        work = _clone(tmp_path, origin, "crlf", "-c", "core.autocrlf=true")
        _git(work, "config", "core.autocrlf", "true")

        # This is the trap: git itself wrote CRLF, so it reports a clean tree.
        assert _git(work, "status", "--porcelain").stdout.strip() == ""
        assert drifted_files(str(work / "noslop"), ALL) == ["SKILL.md"]

    def test_binary_file_is_not_a_false_positive(self, tmp_path):
        origin = _origin(tmp_path)
        work = _clone(tmp_path, origin, "crlf", "-c", "core.autocrlf=true")
        assert "logo.png" not in drifted_files(str(work / "noslop"), ALL)

    def test_clean_worktree_passes(self, tmp_path):
        origin = _origin(tmp_path)
        work = _clone(tmp_path, origin, "lf", "-c", "core.autocrlf=false", "-c", "core.eol=lf")
        assert drifted_files(str(work / "noslop"), ALL) == []
        assert_worktree_matches_repo(str(work / "noslop"), ALL)  # must not raise

    def test_untracked_file_is_skipped(self, tmp_path):
        origin = _origin(tmp_path)
        work = _clone(tmp_path, origin, "lf", "-c", "core.autocrlf=false", "-c", "core.eol=lf")
        (work / "noslop" / "NEW.md").write_bytes(b"fresh\r\n")
        assert drifted_files(str(work / "noslop"), [*ALL, "NEW.md"]) == []

    def test_outside_a_git_repo_is_skipped(self, tmp_path):
        loose = tmp_path / "loose"
        loose.mkdir()
        (loose / "SKILL.md").write_bytes(b"---\nname: x\n---\n")
        assert not is_git_worktree(str(loose))
        assert drifted_files(str(loose), ["SKILL.md"]) == []


class TestRaising:
    def test_assert_names_the_files(self, tmp_path):
        origin = _origin(tmp_path)
        work = _clone(tmp_path, origin, "crlf", "-c", "core.autocrlf=true")
        with pytest.raises(WorktreeDriftError) as exc:
            assert_worktree_matches_repo(str(work / "noslop"), ALL)
        message = str(exc.value)
        assert "SKILL.md" in message
        assert ".gitattributes" in message
        assert "--allow-eol-drift" in message

    def test_tracked_blob_failure_is_not_swallowed(self, tmp_path, monkeypatch):
        """A guard that returns 'clean' when git errors is decorative.

        The first cut of this module did exactly that: a bad path made cat-file
        exit 128 and the file was silently treated as untracked.
        """
        import supply_eol

        origin = _origin(tmp_path)
        work = _clone(tmp_path, origin, "lf", "-c", "core.autocrlf=false")
        real = supply_eol._git

        def fake(cwd, *args, binary=False):
            if args and args[0] == "cat-file":
                return subprocess.CompletedProcess(args, 128, stdout=b"")
            return real(cwd, *args, binary=binary)

        monkeypatch.setattr(supply_eol, "_git", fake)
        with pytest.raises(WorktreeDriftError, match="cat-file failed"):
            drifted_files(str(work / "noslop"), ALL)


class TestSignArtifactIntegration:
    def test_sign_refuses_converted_worktree(self, tmp_path):
        from supply_sign import SupplySignError, sign_artifact

        origin = _origin(tmp_path)
        work = _clone(tmp_path, origin, "crlf", "-c", "core.autocrlf=true")
        with pytest.raises(SupplySignError, match="worktree bytes differ"):
            sign_artifact(str(tmp_path), str(work / "noslop"))

    def test_allow_eol_drift_reaches_the_signer(self, tmp_path):
        """With the escape hatch the guard is bypassed; signing then fails for the
        ordinary reason (no project key here), not for drift."""
        from supply_sign import SupplySignError, sign_artifact

        origin = _origin(tmp_path)
        work = _clone(tmp_path, origin, "crlf", "-c", "core.autocrlf=true")
        with pytest.raises(SupplySignError) as exc:
            sign_artifact(str(tmp_path), str(work / "noslop"), allow_eol_drift=True)
        assert "worktree bytes differ" not in str(exc.value)
