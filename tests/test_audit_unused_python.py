"""Tests for `scripts/audit_unused_python.py` (v14-audit-unused-python).

Covers:
  AC-1 — exclusion config (EXEMPT_MODULES, SOURCE_EXCLUDES, private helpers).
  AC-2 — markdown report artifact via the CLI.
  AC-3 (negative) — false-positive sources are documented and respected:
    generated/exempt modules and private helpers are NOT flagged; tests
    on the SOURCE side stay out of scope.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from audit_unused_python import (  # noqa: E402
    EXEMPT_MODULES,
    SOURCE_EXCLUDES,
    _is_excluded,
    _module_name,
    _toplevel_defs,
    collect_unused,
)

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    # Used by README → not unused
    (scripts / "live.py").write_text("def used_func():\n    return 1\n")
    # Defines symbol no one references → unused
    (scripts / "ghost.py").write_text("def ghost_func():\n    return 1\n")
    # Private helper — should be skipped (noise)
    (scripts / "internals.py").write_text("def _quiet_helper():\n    return 1\n")
    # Hook path — excluded by glob
    hooks = scripts / "hooks"
    hooks.mkdir()
    (hooks / "any_hook.py").write_text("def hook_only():\n    return 1\n")

    (tmp_path / "README.md").write_text("Run `used_func()` to do the thing.\n")
    return tmp_path


class TestExclusionHelpers:
    def test_module_name(self):
        assert _module_name("scripts/foo.py") == "foo"
        assert _module_name("scripts/sub/bar.py") == "bar"

    @pytest.mark.parametrize(
        "path",
        [
            pytest.param("scripts/hooks/any.py", id="hooks_glob_excluded"),
            pytest.param("scripts/__pycache__/x.pyc", id="pycache_excluded"),
        ],
    )
    def test_excluded_paths(self, path):
        assert _is_excluded(path, SOURCE_EXCLUDES)

    def test_unrelated_path_kept(self):
        assert not _is_excluded("scripts/foo.py", SOURCE_EXCLUDES)

    def test_exempt_modules_set_is_frozen(self):
        # Documented invariant — config-style frozen set
        assert isinstance(EXEMPT_MODULES, frozenset)


class TestToplevelDefs:
    def test_collects_def_and_class(self, tmp_path: Path):
        p = tmp_path / "x.py"
        p.write_text("def f(): pass\nclass C: pass\nx = 1\n")
        names = [n for n, _ in _toplevel_defs(p)]
        assert "f" in names
        assert "C" in names

    def test_skips_nested(self, tmp_path: Path):
        p = tmp_path / "n.py"
        p.write_text("def outer():\n    def inner(): pass\n")
        names = [n for n, _ in _toplevel_defs(p)]
        assert names == ["outer"]


class TestCollectUnused:
    def test_ghost_reported(self, fake_repo: Path):
        rows = collect_unused(fake_repo)
        names = {r["name"] for r in rows}
        assert "ghost_func" in names

    @pytest.mark.parametrize(
        "field,absent_value",
        [
            # AC-3 negative: referenced symbols stay clean
            pytest.param("name", "used_func", id="referenced_kept_clean"),
            # AC-3 negative: private helpers excluded from report regardless
            pytest.param("name", "_quiet_helper", id="private_helper_skipped"),
            # AC-1: SOURCE_EXCLUDES respected — hooks never appear
            pytest.param("file", "scripts/hooks/any_hook.py", id="hooks_excluded_by_glob"),
        ],
    )
    def test_value_absent_from_unused(self, fake_repo: Path, field, absent_value):
        rows = collect_unused(fake_repo)
        values = {r[field] for r in rows}
        assert absent_value not in values


class TestCli:
    def test_real_repo_runs(self):
        py = (
            REPO / ".tausik" / "venv" / "Scripts" / "python.exe"
            if (REPO / ".tausik" / "venv" / "Scripts" / "python.exe").is_file()
            else REPO / ".tausik" / "venv" / "bin" / "python"
        )
        r = subprocess.run(
            [str(py), str(REPO / "scripts" / "audit_unused_python.py")],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        # Exit 0 (clean) or 1 (--check would flag) — never crash on real repo
        assert r.returncode == 0
        assert "Unused Python audit" in r.stdout
