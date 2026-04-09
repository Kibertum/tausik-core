"""Test bootstrap --dry-run mode.

Run: pytest tests/test_bootstrap_dryrun.py -v
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_bootstrap_dir = os.path.join(os.path.dirname(__file__), "..", "bootstrap")


class TestBootstrapDryRun:
    """Test that --dry-run shows plan without writing files."""

    def test_dry_run_no_files_created(self, tmp_path):
        """--dry-run should not create any files or directories."""
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(_bootstrap_dir, "bootstrap.py"),
                "--project-dir",
                str(tmp_path),
                "--ide",
                "claude",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        assert result.returncode == 0
        assert "DRY RUN" in result.stdout
        assert "No changes made" in result.stdout

        # No .claude or .tausik directories should be created
        assert not (tmp_path / ".claude").exists()
        assert not (tmp_path / ".tausik").exists()

    def test_dry_run_shows_skills(self, tmp_path):
        """--dry-run should list skills that would be copied."""
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(_bootstrap_dir, "bootstrap.py"),
                "--project-dir",
                str(tmp_path),
                "--ide",
                "claude",
                "--smart",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        assert result.returncode == 0
        assert "Skills" in result.stdout
        assert "start" in result.stdout  # core skill always present

    def test_dry_run_shows_target_dir(self, tmp_path):
        """--dry-run should show the target directory."""
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(_bootstrap_dir, "bootstrap.py"),
                "--project-dir",
                str(tmp_path),
                "--ide",
                "cursor",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        assert result.returncode == 0
        assert ".cursor" in result.stdout

    def test_dry_run_all_ides(self, tmp_path):
        """--dry-run with --ide all should show both IDEs."""
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(_bootstrap_dir, "bootstrap.py"),
                "--project-dir",
                str(tmp_path),
                "--ide",
                "all",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        assert result.returncode == 0
        assert "claude" in result.stdout
        assert "cursor" in result.stdout
        assert not (tmp_path / ".claude").exists()
        assert not (tmp_path / ".cursor").exists()
