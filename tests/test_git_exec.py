"""Tests for scripts/git_exec.py — the single guarded git subprocess primitive
(git-exec-single-wrapper).

The whole point of this module is that stdin=DEVNULL cannot be forgotten. These
tests pin that guarantee at the chokepoint, plus the ergonomics of `run`
(required timeout, text/binary decoding, returncode passthrough).
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import git_exec  # noqa: E402


class _Captured:
    def __init__(self):
        self.cmd = None
        self.kwargs = None

    def fake_run(self, cmd, **kwargs):
        self.cmd = cmd
        self.kwargs = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")


class TestRunGitStdinGuard:
    def test_forces_devnull_when_caller_omits_stdin(self, monkeypatch):
        cap = _Captured()
        monkeypatch.setattr(subprocess, "run", cap.fake_run)
        git_exec.run_git(["git", "rev-parse", "HEAD"])
        assert cap.kwargs["stdin"] is subprocess.DEVNULL

    def test_explicit_stdin_override_is_honoured(self, monkeypatch):
        # The guard is a floor, not a ceiling: a caller that passes its own stdin
        # wins. (No caller does — this documents the contract.)
        cap = _Captured()
        monkeypatch.setattr(subprocess, "run", cap.fake_run)
        git_exec.run_git(["git", "status"], stdin=None)
        assert cap.kwargs["stdin"] is None

    def test_run_also_closes_stdin(self, monkeypatch):
        cap = _Captured()
        monkeypatch.setattr(subprocess, "run", cap.fake_run)
        git_exec.run(["rev-parse", "HEAD"], timeout=5)
        assert cap.kwargs["stdin"] is subprocess.DEVNULL


class TestRunErgonomics:
    def test_prepends_git_and_captures(self, monkeypatch):
        cap = _Captured()
        monkeypatch.setattr(subprocess, "run", cap.fake_run)
        git_exec.run(["diff", "--numstat"], timeout=10)
        assert cap.cmd == ["git", "diff", "--numstat"]
        assert cap.kwargs["capture_output"] is True

    def test_timeout_is_required(self):
        # NEGATIVE/BOUNDARY: no silently-unbounded git call is possible.
        with pytest.raises(TypeError):
            git_exec.run(["status"])  # type: ignore[call-arg]

    def test_text_mode_decodes_utf8_replace(self, monkeypatch):
        cap = _Captured()
        monkeypatch.setattr(subprocess, "run", cap.fake_run)
        git_exec.run(["rev-parse", "HEAD"], timeout=5)
        assert cap.kwargs["text"] is True
        assert cap.kwargs["encoding"] == "utf-8"
        assert cap.kwargs["errors"] == "replace"

    def test_binary_mode_returns_bytes_no_text_decoding(self, monkeypatch):
        cap = _Captured()
        monkeypatch.setattr(subprocess, "run", cap.fake_run)
        git_exec.run(["cat-file", "blob", ":x"], timeout=5, binary=True)
        assert cap.kwargs["text"] is False
        assert "encoding" not in cap.kwargs
        assert "errors" not in cap.kwargs


class TestRealGit:
    """One real-git integration to prove the wrapper actually shells out."""

    def _has_git(self) -> bool:
        try:
            return git_exec.run(["--version"], timeout=5).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def test_nonzero_exit_passes_through_without_raising(self):
        if not self._has_git():
            pytest.skip("git not available")
        # A bogus subcommand exits nonzero; run() must NOT raise (check=False),
        # returning a CompletedProcess for the caller to inspect.
        result = git_exec.run(["cat-file", "-e", "0" * 40], cwd=".", timeout=5)
        assert isinstance(result, subprocess.CompletedProcess)
        assert result.returncode != 0

    def test_check_true_raises_on_nonzero(self):
        if not self._has_git():
            pytest.skip("git not available")
        with pytest.raises(subprocess.CalledProcessError):
            git_exec.run(["cat-file", "-e", "0" * 40], cwd=".", timeout=5, check=True)
