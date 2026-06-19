"""Smoke tests for the generated CLI wrappers (tausik_wrapper.cmd / .sh).

Regression guard for the v153 Windows defect: a literal "(" / ")" in the
"no scripts dir found" error text closed the `if not defined SCRIPTS (...)`
block early, making `exit /b 1` unconditional — every command failed exit 1
even when a scripts dir was present.

Run: pytest tests/test_wrapper_smoke.py -v
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_CMD_SRC = os.path.join(_ROOT, "bootstrap", "tausik_wrapper.cmd")
_SH_SRC = os.path.join(_ROOT, "bootstrap", "tausik_wrapper.sh")

# A standalone stub that mimics scripts/project.py: echoes its args, exits 0.
_STUB = "import sys\nprint('STUB_OK ' + ' '.join(sys.argv[1:]))\n"


def _make_project(tmp_path, with_scripts=True):
    """Lay out tmp/.tausik/<wrapper> + tmp/.claude/scripts/project.py."""
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    if with_scripts:
        scripts = tmp_path / ".claude" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "project.py").write_text(_STUB)
    return tausik_dir


class TestCmdWrapper:
    """Windows .cmd wrapper — needs cmd.exe."""

    @pytest.mark.skipif(os.name != "nt", reason="cmd wrapper is Windows-only")
    def test_passthrough_exits_zero(self, tmp_path):
        """With a scripts dir present, the wrapper runs python and exits 0."""
        tausik_dir = _make_project(tmp_path, with_scripts=True)
        wrapper = tausik_dir / "tausik.cmd"
        shutil.copyfile(_CMD_SRC, wrapper)

        result = subprocess.run(
            ["cmd", "/c", str(wrapper), "status"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "STUB_OK status" in result.stdout

    @pytest.mark.skipif(os.name != "nt", reason="cmd wrapper is Windows-only")
    def test_missing_scripts_one_error_exit_one(self, tmp_path):
        """No scripts dir → exactly one error line and exit 1."""
        tausik_dir = _make_project(tmp_path, with_scripts=False)
        wrapper = tausik_dir / "tausik.cmd"
        shutil.copyfile(_CMD_SRC, wrapper)

        result = subprocess.run(
            ["cmd", "/c", str(wrapper), "status"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert result.stderr.count("no scripts dir found") == 1
        assert "STUB_OK" not in result.stdout


class TestShWrapper:
    """POSIX .sh wrapper — needs bash."""

    @pytest.mark.skipif(
        os.name == "nt" or shutil.which("bash") is None,
        reason="POSIX sh wrapper; git-bash path interop on Windows is unreliable",
    )
    def test_passthrough_exits_zero(self, tmp_path):
        tausik_dir = _make_project(tmp_path, with_scripts=True)
        wrapper = tausik_dir / "tausik"
        shutil.copyfile(_SH_SRC, wrapper)

        result = subprocess.run(
            ["bash", str(wrapper), "status"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "STUB_OK status" in result.stdout

    @pytest.mark.skipif(
        os.name == "nt" or shutil.which("bash") is None,
        reason="POSIX sh wrapper; git-bash path interop on Windows is unreliable",
    )
    def test_missing_scripts_one_error_exit_one(self, tmp_path):
        tausik_dir = _make_project(tmp_path, with_scripts=False)
        wrapper = tausik_dir / "tausik"
        shutil.copyfile(_SH_SRC, wrapper)

        result = subprocess.run(
            ["bash", str(wrapper), "status"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert result.stderr.count("no scripts dir found") == 1
        assert "STUB_OK" not in result.stdout
