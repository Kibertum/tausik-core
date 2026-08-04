"""Smoke tests for the generated CLI wrappers (tausik_wrapper.cmd / .sh).

Two regressions guarded here:

1. v153 Windows defect: a literal "(" / ")" in the "no scripts dir found"
   error text closed the `if not defined SCRIPTS (...)` block early, making
   `exit /b 1` unconditional — every command failed exit 1 even when a
   scripts dir was present.

2. v156 Kilo-only defect: the wrapper's IDE-discovery loop hardcoded
   `claude cursor qwen windsurf codex` (no kilo), so a `--ide kilo`-only
   install (.kilo/scripts) hit "no scripts dir found". The loop is now
   injected from bootstrap_config.IDE_DIRS via install_cli_wrapper, so the
   tests render through that real code path rather than copying the template
   (which still contains the unsubstituted __IDE_LIST__ placeholder).

Run: pytest tests/test_wrapper_smoke.py -v
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BOOTSTRAP = os.path.join(_ROOT, "bootstrap")

# install_cli_wrapper lives in bootstrap/ and imports bootstrap_config;
# both need the bootstrap dir on sys.path.
if _BOOTSTRAP not in sys.path:
    sys.path.insert(0, _BOOTSTRAP)

from bootstrap_venv import install_cli_wrapper  # noqa: E402

# A standalone stub that mimics scripts/project.py: echoes its args, exits 0.
_STUB = "import sys\nprint('STUB_OK ' + ' '.join(sys.argv[1:]))\n"


def _make_project(tmp_path, ide_dir=".claude"):
    """Lay out tmp/.tausik/<rendered wrappers> + tmp/<ide_dir>/scripts/project.py.

    ide_dir=None lays out NO scripts dir (negative case). Wrappers are
    rendered through install_cli_wrapper so __IDE_LIST__ is substituted
    from bootstrap_config.IDE_DIRS — exactly what bootstrap does.
    """
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    if ide_dir is not None:
        scripts = tmp_path / ide_dir / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "project.py").write_text(_STUB)
    install_cli_wrapper(_BOOTSTRAP, str(tausik_dir))
    return tausik_dir


class TestCmdWrapper:
    """Windows .cmd wrapper — needs cmd.exe."""

    @pytest.mark.skipif(os.name != "nt", reason="cmd wrapper is Windows-only")
    @pytest.mark.parametrize("ide_dir", [".claude", ".kilo", ".qwen"])
    def test_passthrough_exits_zero(self, tmp_path, ide_dir):
        """With any supported scripts dir present, wrapper runs python, exit 0.

        .kilo is the v156 regression: a Kilo-only install must be discovered.
        """
        tausik_dir = _make_project(tmp_path, ide_dir=ide_dir)
        wrapper = tausik_dir / "tausik.cmd"

        result = subprocess.run(
            ["cmd", "/c", str(wrapper), "status"],
            capture_output=True,
            text=True, encoding="utf-8",
        )
        assert result.returncode == 0, result.stderr
        assert "STUB_OK status" in result.stdout

    @pytest.mark.skipif(os.name != "nt", reason="cmd wrapper is Windows-only")
    def test_missing_scripts_one_error_exit_one(self, tmp_path):
        """No scripts dir → exactly one error line and exit 1."""
        tausik_dir = _make_project(tmp_path, ide_dir=None)
        wrapper = tausik_dir / "tausik.cmd"

        result = subprocess.run(
            ["cmd", "/c", str(wrapper), "status"],
            capture_output=True,
            text=True, encoding="utf-8",
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
    @pytest.mark.parametrize("ide_dir", [".claude", ".kilo", ".qwen"])
    def test_passthrough_exits_zero(self, tmp_path, ide_dir):
        tausik_dir = _make_project(tmp_path, ide_dir=ide_dir)
        wrapper = tausik_dir / "tausik"

        result = subprocess.run(
            ["bash", str(wrapper), "status"],
            capture_output=True,
            text=True, encoding="utf-8",
        )
        assert result.returncode == 0, result.stderr
        assert "STUB_OK status" in result.stdout

    @pytest.mark.skipif(
        os.name == "nt" or shutil.which("bash") is None,
        reason="POSIX sh wrapper; git-bash path interop on Windows is unreliable",
    )
    def test_missing_scripts_one_error_exit_one(self, tmp_path):
        tausik_dir = _make_project(tmp_path, ide_dir=None)
        wrapper = tausik_dir / "tausik"

        result = subprocess.run(
            ["bash", str(wrapper), "status"],
            capture_output=True,
            text=True, encoding="utf-8",
        )
        assert result.returncode == 1
        assert result.stderr.count("no scripts dir found") == 1
        assert "STUB_OK" not in result.stdout


def test_template_has_placeholder_not_hardcoded_list():
    """The committed templates must use __IDE_LIST__, not a hardcoded IDE list,
    so bootstrap_config.IDE_DIRS stays the single source of truth."""
    for name in ("tausik_wrapper.sh", "tausik_wrapper.cmd"):
        text = open(os.path.join(_BOOTSTRAP, name), encoding="utf-8").read()
        assert "__IDE_LIST__" in text, f"{name} lost its __IDE_LIST__ placeholder"


def test_rendered_wrapper_contains_kilo(tmp_path):
    """install_cli_wrapper must substitute the placeholder with the real IDE
    list including kilo (the v156 fix)."""
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    install_cli_wrapper(_BOOTSTRAP, str(tausik_dir))
    for fname in ("tausik", "tausik.cmd"):
        rendered = (tausik_dir / fname).read_text(encoding="utf-8")
        assert "__IDE_LIST__" not in rendered, f"{fname} placeholder not substituted"
        assert "kilo" in rendered, f"{fname} missing kilo in injected IDE list"
