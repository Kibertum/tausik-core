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

    def test_input_really_reaches_the_child(self):
        """Batch-mode git reads what we pipe in, and DEVNULL still holds without it.

        `hash-object --stdin` names the two branches apart by construction: fed
        b"abc\\n" it answers that blob's id; with stdin closed it hashes the
        empty blob. Neither touches the object store (no -w). Bytes, because a
        text-mode pipe applies the platform's newline translation on the way
        in — on Windows "abc\\n" would arrive as "abc\\r\\n" and hash differently.
        """
        if not self._has_git():
            pytest.skip("git not available")
        fed = git_exec.run(
            ["hash-object", "--stdin"], cwd=".", timeout=5, binary=True, input=b"abc\n"
        )
        assert fed.returncode == 0
        assert fed.stdout.strip() == b"8baef1b4abc478178b004d62031cf7fe6db6f903"
        closed = git_exec.run(["hash-object", "--stdin"], cwd=".", timeout=5, binary=True)
        assert closed.returncode == 0
        assert closed.stdout.strip() == b"e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


class TestInputKeepsTheGuard:
    """`input` opens a pipe of our own; it never hands the child the inherited stdin."""

    def test_input_sets_stdin_none_so_subprocess_may_open_its_pipe(self, monkeypatch):
        # subprocess.run refuses `input` beside any other stdin value; the keyword
        # is still passed (explicitly None) so the AST guard keeps seeing it.
        cap = _Captured()
        monkeypatch.setattr(subprocess, "run", cap.fake_run)
        git_exec.run_git(["git", "cat-file", "--batch"], input=b"HEAD:./x\n")
        assert "stdin" in cap.kwargs
        assert cap.kwargs["stdin"] is None
        assert cap.kwargs["input"] == b"HEAD:./x\n"

    def test_run_passes_input_through_and_omits_it_otherwise(self, monkeypatch):
        cap = _Captured()
        monkeypatch.setattr(subprocess, "run", cap.fake_run)
        git_exec.run(["cat-file", "--batch"], timeout=5, binary=True, input=b"a\n")
        assert cap.kwargs["input"] == b"a\n"
        assert cap.kwargs["stdin"] is None
        git_exec.run(["cat-file", "--batch"], timeout=5, binary=True)
        assert "input" not in cap.kwargs
        assert cap.kwargs["stdin"] is subprocess.DEVNULL

    def test_both_given_is_subprocesss_loud_error_not_a_quiet_pick(self):
        """NEGATIVE, real subprocess (review #38): the documented incompatibility
        is observable, not just a statement about forwarded kwargs."""
        with pytest.raises(ValueError, match="stdin and input"):
            git_exec.run_git(["git", "--version"], stdin=subprocess.DEVNULL, input=b"x\n")

    def test_input_none_is_the_same_as_no_input(self, monkeypatch):
        # NEGATIVE: an explicit None must not open a pipe — DEVNULL stays.
        cap = _Captured()
        monkeypatch.setattr(subprocess, "run", cap.fake_run)
        git_exec.run_git(["git", "status"], input=None)
        assert cap.kwargs["stdin"] is subprocess.DEVNULL

    def test_an_explicit_stdin_still_wins_over_input(self, monkeypatch):
        """NEGATIVE: the floor-not-ceiling contract survives `input`.

        Found by review: the first shape of the guard overrode a caller's
        explicit `stdin` with None whenever `input` was present — the one
        thing the docstring promised never to do. The guard fills a gap; it
        does not arbitrate between two things the caller said.
        """
        cap = _Captured()
        monkeypatch.setattr(subprocess, "run", cap.fake_run)
        sentinel = object()
        git_exec.run_git(["git", "cat-file", "--batch"], stdin=sentinel, input=b"x\n")
        assert cap.kwargs["stdin"] is sentinel
        assert cap.kwargs["input"] == b"x\n"
