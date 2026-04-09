"""Tests for bootstrap_venv — Python discovery, venv creation, dependency install."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

from bootstrap_venv import (
    MIN_PYTHON,
    _check_version,
    find_python,
    get_venv_python,
)


class TestCheckVersion:
    def test_current_python(self):
        ver = _check_version(sys.executable)
        assert ver is not None
        assert ver >= MIN_PYTHON

    def test_nonexistent_binary(self):
        ver = _check_version("/no/such/python999")
        assert ver is None

    def test_invalid_command(self):
        ver = _check_version("echo")
        assert ver is None


class TestFindPython:
    def test_finds_something(self):
        result = find_python()
        assert result is not None
        assert os.path.isabs(result)

    def test_found_version_sufficient(self):
        python = find_python()
        assert python is not None
        ver = _check_version(python)
        assert ver is not None
        assert ver >= MIN_PYTHON


class TestGetVenvPython:
    def test_no_venv(self, tmp_path):
        result = get_venv_python(str(tmp_path))
        assert result is None

    def test_finds_venv_python(self, tmp_path):
        """Create a fake venv structure and verify detection."""
        if sys.platform == "win32":
            venv_python = tmp_path / "venv" / "Scripts" / "python.exe"
        else:
            venv_python = tmp_path / "venv" / "bin" / "python3"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()
        result = get_venv_python(str(tmp_path))
        assert result is not None
        assert "venv" in result


class TestEnsureVenv:
    def test_creates_venv(self, tmp_path):
        """ensure_venv creates a working venv."""
        from bootstrap_venv import ensure_venv

        tausik_dir = str(tmp_path / ".tausik")
        os.makedirs(tausik_dir)
        result = ensure_venv(tausik_dir)
        assert os.path.isfile(result)
        # Verify venv python works
        ver = _check_version(result)
        assert ver is not None
        assert ver >= MIN_PYTHON


class TestInstallRequirements:
    def test_install_with_requirements(self, tmp_path):
        """install_requirements installs from requirements.txt."""
        from bootstrap_venv import ensure_venv, install_requirements

        # Create a minimal requirements.txt
        lib_dir = str(tmp_path / "lib")
        os.makedirs(lib_dir)
        req_file = os.path.join(lib_dir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("# test\n")  # empty requirements — just verify it runs

        tausik_dir = str(tmp_path / ".tausik")
        os.makedirs(tausik_dir)
        ensure_venv(tausik_dir)
        result = install_requirements(tausik_dir, lib_dir)
        assert result is True

    def test_no_venv_returns_false(self, tmp_path):
        """install_requirements returns False when venv doesn't exist."""
        from bootstrap_venv import install_requirements

        tausik_dir = str(tmp_path / ".tausik")
        os.makedirs(tausik_dir)
        result = install_requirements(tausik_dir, str(tmp_path / "lib"))
        assert result is False
