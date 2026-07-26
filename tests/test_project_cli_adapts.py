"""Tests for project_cli_adapts — CLI handler exit-code contract.

Sibling of test_project_cli_role: the `adapt` dispatch swallowed ServiceError,
printed to stdout and returned — exiting 0 on a real failure. It must exit
non-zero on stderr like every other command (CLAUDE.md zero-tolerance).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import project_cli_adapts as cli
from tausik_utils import ServiceError


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Svc:
    def __init__(self, fn):
        self._fn = fn

    def adapt_delete(self, slug):
        return self._fn(slug)


class TestAdaptCliExitCodes:
    def test_error_exits_nonzero_on_stderr(self, capsys):
        def _raise(slug):
            raise ServiceError("ADAPT 'x' not found.")

        with pytest.raises(SystemExit) as exc:
            cli.cmd_adapt(_Svc(_raise), _Args(adapt_cmd="delete", slug="x"))
        assert exc.value.code == 1
        cap = capsys.readouterr()
        assert "not found" in cap.err  # error on stderr, not stdout
        assert cap.out == ""

    def test_success_does_not_exit(self, capsys):
        cli.cmd_adapt(_Svc(lambda slug: "ADAPT deleted"), _Args(adapt_cmd="delete", slug="x"))
        assert "ADAPT deleted" in capsys.readouterr().out
