"""BLE001 (no-silent-errors) enforcement regression — qa-enforce-ble001-blind-except.

Guards that the rule stays enabled and that no unjustified blind `except Exception`
creeps back into the CI-linted tree. A new blind catch must carry
`# noqa: BLE001 — <why>` or be narrowed, or this test (and CI) fails.
"""

from __future__ import annotations

import os
import subprocess
import sys

_REPO = os.path.join(os.path.dirname(__file__), "..")


def test_ble001_enabled_in_config():
    with open(os.path.join(_REPO, "pyproject.toml"), encoding="utf-8") as f:
        cfg = f.read()
    assert "BLE001" in cfg and "extend-select" in cfg


def test_no_unannotated_blind_except_whole_tree():
    # Whole committed tree (ruff respects .gitignore → skips .claude/.tausik).
    # Covers harness/**/mcp too, not just CI-linted paths, so `ruff check .`
    # stays clean under BLE001.
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--select", "BLE001", "."],
        cwd=_REPO,
        capture_output=True,
        text=True, encoding="utf-8",
    )
    # ruff exits 0 when no violations remain; any BLE001 line = a new blind catch.
    assert "BLE001" not in proc.stdout, f"unannotated blind except found:\n{proc.stdout}"
    assert proc.returncode == 0, proc.stdout + proc.stderr
