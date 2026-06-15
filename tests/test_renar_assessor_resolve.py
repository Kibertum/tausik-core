"""Tests for assessor resolution in `tausik renar conformance`.

Guards the fix that removed the hardcoded personal identity
'architect-andrey-y' as the default assessor. Resolution must be:
explicit --assessor -> config renar_default_assessor -> git user.name ->
neutral FALLBACK_ASSESSOR, and must never silently attribute a manifest to a
real person who did not run the assessment.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import project_cli_renar as renar  # noqa: E402
from project_cli_renar import FALLBACK_ASSESSOR, resolve_assessor  # noqa: E402


def test_explicit_assessor_wins(monkeypatch):
    # Even with config + git available, explicit takes precedence.
    monkeypatch.setattr(renar, "_git_user_name", lambda: "git-person")
    assert resolve_assessor("alice", {"renar_default_assessor": "bob"}) == "alice"


def test_config_assessor_used_when_no_explicit(monkeypatch):
    monkeypatch.setattr(renar, "_git_user_name", lambda: "git-person")
    assert resolve_assessor(None, {"renar_default_assessor": "bob"}) == "bob"


def test_git_user_name_used_when_no_config(monkeypatch):
    monkeypatch.setattr(renar, "_git_user_name", lambda: "carol")
    assert resolve_assessor(None, {}) == "carol"


def test_fallback_when_nothing_resolves(monkeypatch):
    # Negative scenario: no config, git unavailable -> neutral fallback, no crash.
    monkeypatch.setattr(renar, "_git_user_name", lambda: None)
    assert resolve_assessor(None, {}) == FALLBACK_ASSESSOR
    assert FALLBACK_ASSESSOR == "unknown-assessor"


def test_whitespace_explicit_falls_through(monkeypatch):
    # A blank --assessor must not win; it falls through to the next source.
    monkeypatch.setattr(renar, "_git_user_name", lambda: None)
    assert resolve_assessor("   ", {}) == FALLBACK_ASSESSOR
    assert resolve_assessor("   ", {"renar_default_assessor": "bob"}) == "bob"


def test_blank_config_value_falls_through_to_git(monkeypatch):
    monkeypatch.setattr(renar, "_git_user_name", lambda: "carol")
    assert resolve_assessor(None, {"renar_default_assessor": "  "}) == "carol"


def test_null_config_value_falls_through(monkeypatch):
    # JSON null -> Python None. cfg.get(key, "") returns None (key present), and
    # str(None) == "None" must NOT leak as the assessor id — fall through instead.
    monkeypatch.setattr(renar, "_git_user_name", lambda: None)
    assert resolve_assessor(None, {"renar_default_assessor": None}) == FALLBACK_ASSESSOR


def test_null_config_value_falls_through_to_git(monkeypatch):
    monkeypatch.setattr(renar, "_git_user_name", lambda: "carol")
    assert resolve_assessor(None, {"renar_default_assessor": None}) == "carol"


def test_git_helper_never_raises(monkeypatch):
    # _git_user_name must swallow subprocess/OS failures and return None.
    def boom(*_a, **_k):
        raise OSError("git not found")

    monkeypatch.setattr(renar.subprocess, "run", boom)
    assert renar._git_user_name() is None
