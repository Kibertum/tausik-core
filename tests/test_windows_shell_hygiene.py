"""Detector for Windows shell hygiene nudge (warn-only)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from windows_shell_hygiene import findings


@pytest.mark.parametrize(
    "command,expected",
    [
        ('powershell -Command "Write-Host \\"hi\\""', ["nested-quotes"]),
        (
            "powershell -EncodedCommand AAA= --extra",
            ["EncodedCommand-trailing-args"],
        ),
        ("gh api repos/o/r --jq '.items[] | {name}'", ["gh-jq-braces"]),
        ("ssh host 'bash -s' <<'EOF'\necho hi\nEOF", ["ssh-heredoc"]),
        ("echo hello", []),
        ("powershell -File .\\run.ps1", []),
        ('python scripts\\do_it.py --flag "value"', []),
    ],
)
def test_findings_matrix(command: str, expected: list[str]):
    assert findings(command) == expected
