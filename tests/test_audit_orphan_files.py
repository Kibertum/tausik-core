"""Tests for `scripts/audit_orphan_files.py` (v14-audit-orphan-files).

Covers:
  AC-1 — runs and produces a markdown report.
  AC-2 — exclusion globs are respected.
  AC-3 (negative) — assets/tests are excluded from the orphan report;
    additionally, a doc-mentioned standalone script is NOT marked orphan.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from audit_orphan_files import (  # noqa: E402
    DEFAULT_EXCLUDES,
    _is_excluded,
    collect_orphans,
)

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Lay out a tiny repo with a few python files and one markdown reference."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    # Imported by tests/test_used.py — should NOT be orphan
    (scripts / "imported_mod.py").write_text("def hi(): return 1\n")
    # Standalone CLI mentioned in docs/architecture.md — should NOT be orphan
    (scripts / "doc_only_cli.py").write_text("if __name__ == '__main__': pass\n")
    # Truly orphan — neither imported nor mentioned in docs
    (scripts / "lonely_helper.py").write_text("x = 1\n")
    # Asset/test/etc that should be excluded from scanning
    (scripts / "hooks").mkdir()
    (scripts / "hooks" / "any_hook.py").write_text("# hook\n")

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_used.py").write_text("from imported_mod import hi\n")

    docs = tmp_path / "docs" / "en"
    docs.mkdir(parents=True)
    (docs / "architecture.md").write_text("Standalone CLI: `doc_only_cli.py` runs separately.\n")
    return tmp_path


class TestExclusion:
    def test_tests_excluded(self):
        assert _is_excluded("tests/test_x.py", DEFAULT_EXCLUDES)

    def test_pycache_excluded(self):
        assert _is_excluded("scripts/__pycache__/foo.pyc", DEFAULT_EXCLUDES)

    def test_hooks_excluded(self):
        assert _is_excluded("scripts/hooks/any_hook.py", DEFAULT_EXCLUDES)

    def test_unrelated_path_not_excluded(self):
        assert not _is_excluded("scripts/foo.py", DEFAULT_EXCLUDES)


class TestCollectOrphans:
    def test_lonely_helper_reported(self, fake_repo: Path):
        orphans = collect_orphans(fake_repo)
        assert "scripts/lonely_helper.py" in orphans

    def test_imported_module_not_reported(self, fake_repo: Path):
        orphans = collect_orphans(fake_repo)
        assert "scripts/imported_mod.py" not in orphans

    def test_doc_referenced_standalone_not_reported(self, fake_repo: Path):
        # AC-3 negative: documented CLI scripts are NOT orphans
        orphans = collect_orphans(fake_repo)
        assert "scripts/doc_only_cli.py" not in orphans

    def test_hook_path_excluded_from_scan(self, fake_repo: Path):
        orphans = collect_orphans(fake_repo)
        assert "scripts/hooks/any_hook.py" not in orphans


class TestCli:
    def test_real_repo_check_zero_or_known(self):
        """Smoke test on the live TAUSIK repo: should be clean."""
        py = (
            REPO / ".tausik" / "venv" / "Scripts" / "python.exe"
            if (REPO / ".tausik" / "venv" / "Scripts" / "python.exe").is_file()
            else REPO / ".tausik" / "venv" / "bin" / "python"
        )
        r = subprocess.run(
            [str(py), str(REPO / "scripts" / "audit_orphan_files.py"), "--check"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        # Either clean (exit 0) or surfaces real candidates (exit 1) — never crash
        assert r.returncode in {0, 1}, r.stderr
        assert "Orphan-file audit" in r.stdout
