"""Tests for project_cli_specs — CLI handler exit-code contract.

Sibling of test_project_cli_role: the `spec` dispatch swallowed ServiceError,
printed to stdout and returned — exiting 0 on a real failure. It must exit
non-zero on stderr like every other command (CLAUDE.md zero-tolerance).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import project_cli_specs as cli
from tausik_utils import ServiceError


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Svc:
    def __init__(self, fn):
        self._fn = fn

    def spec_delete(self, slug):
        return self._fn(slug)


class TestSpecCliExitCodes:
    def test_error_exits_nonzero_on_stderr(self, capsys):
        def _raise(slug):
            raise ServiceError("SPEC 'x' not found.")

        with pytest.raises(SystemExit) as exc:
            cli.cmd_spec(_Svc(_raise), _Args(spec_cmd="delete", slug="x"))
        assert exc.value.code == 1
        cap = capsys.readouterr()
        assert "not found" in cap.err  # error on stderr, not stdout
        assert cap.out == ""

    def test_success_does_not_exit(self, capsys):
        cli.cmd_spec(_Svc(lambda slug: "SPEC deleted"), _Args(spec_cmd="delete", slug="x"))
        assert "SPEC deleted" in capsys.readouterr().out
