"""Tests for project_cli_role — CLI handler exit-code contract.

Regression: `tausik role show <missing>` caught the ServiceError, printed it to
stdout and returned — exiting 0. A script checking $? saw success on a real error
(CLAUDE.md zero-tolerance for silent errors). Handlers must exit non-zero and
write to stderr, like every other CLI command (`task show <missing>` exits 1).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import project_cli_role as cli
from tausik_utils import ServiceError


class _FakeSvc:
    be = object()


class TestRoleCliExitCodes:
    def test_role_show_missing_exits_nonzero_on_stderr(self, monkeypatch, capsys):
        def _raise(be, slug):
            raise ServiceError(f"Role '{slug}' not found.")

        # _cmd_show does `from service_roles import role_show` at call time, so
        # patching the attribute on the module is what it resolves.
        monkeypatch.setattr("service_roles.role_show", _raise)

        with pytest.raises(SystemExit) as exc:
            cli._cmd_show(_FakeSvc(), "no-such-role")
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err  # error on stderr, not stdout
        assert captured.out == ""

    def test_role_show_existing_still_exits_zero(self, monkeypatch, capsys):
        """Happy path unbroken: a found role prints and returns normally."""

        def _ok(be, slug):
            return {
                "slug": slug,
                "title": "DevOps",
                "description": "d",
                "task_count": 1,
                "profile_path_source": "/x/devops.md",
                "profile": None,
            }

        monkeypatch.setattr("service_roles.role_show", _ok)
        cli._cmd_show(_FakeSvc(), "devops")  # must NOT raise SystemExit
        assert "Role: devops" in capsys.readouterr().out

    def test_role_create_failure_exits_nonzero(self, monkeypatch, capsys):
        class _Args:
            slug = "bad slug"
            title = "T"
            description = None
            extends = None

        def _raise(be, slug, title, description, extends):
            raise ServiceError("invalid slug")

        monkeypatch.setattr("service_roles.role_create", _raise)
        with pytest.raises(SystemExit) as exc:
            cli._cmd_create(_FakeSvc(), _Args())
        assert exc.value.code == 1
        assert "invalid slug" in capsys.readouterr().err
