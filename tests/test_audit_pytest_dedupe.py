"""Tests for `scripts/audit_pytest_dedupe.py` (v14-pytest-dedupe-audit).

Covers:
  AC-1 — script with markdown output.
  AC-2 — research artifact saved to `docs/ru/research/...`.
  AC-3 (negative) — false positives are documented in the report itself.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from audit_pytest_dedupe import (  # noqa: E402
    _normalize_function,
    _signature,
    collect_duplicates,
    render_markdown,
)
import ast  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def _parse_func(src: str) -> ast.FunctionDef:
    tree = ast.parse(src)
    func = tree.body[0]
    assert isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef))
    return func


class TestNormalize:
    def test_identical_logic_same_signature(self):
        a = _parse_func("def test_a():\n    x = 1\n    assert x == 1\n")
        b = _parse_func("def test_b():\n    y = 7\n    assert y == 7\n")
        assert _signature(_normalize_function(a)) == _signature(_normalize_function(b))

    def test_different_logic_different_signature(self):
        a = _parse_func("def test_a():\n    x = 1\n    assert x == 1\n")
        b = _parse_func("def test_b():\n    return 1\n")
        assert _signature(_normalize_function(a)) != _signature(_normalize_function(b))


class TestCollectDuplicates:
    def test_duplicates_grouped(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_dups.py").write_text(
            "def test_one():\n    a = 1\n    assert a == 1\n"
            "def test_two():\n    b = 2\n    assert b == 2\n"
            "def test_unique():\n    return 7\n"
        )
        groups = collect_duplicates(tmp_path)
        assert len(groups) == 1
        names = {m["name"] for m in groups[0]["members"]}
        assert names == {"test_one", "test_two"}

    def test_no_duplicates_yields_empty(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_clean.py").write_text(
            "def test_one():\n    return 1\ndef test_two():\n    yield 2\n"
        )
        assert collect_duplicates(tmp_path) == []

    def test_class_methods_collected(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_class.py").write_text(
            "class TestX:\n"
            "    def test_a(self):\n        x = 1\n        assert x == 1\n"
            "    def test_b(self):\n        y = 2\n        assert y == 2\n"
        )
        groups = collect_duplicates(tmp_path)
        assert len(groups) == 1
        names = {m["name"] for m in groups[0]["members"]}
        assert "TestX.test_a" in names
        assert "TestX.test_b" in names


class TestRenderMarkdown:
    def test_empty_groups_omits_per_test_rows(self):
        # Behavior contrast: empty input produces no per-test enumerations,
        # while populated input does. Asserts the rendering distinguishes
        # the two states without locking on exact label strings.
        out_empty = render_markdown([])
        out_populated = render_markdown(
            [
                {
                    "signature": "sig-x",
                    "members": [
                        {"name": "test_dup_a", "file": "x.py", "lineno": 1},
                        {"name": "test_dup_b", "file": "y.py", "lineno": 1},
                    ],
                }
            ]
        )
        assert "test_dup_a" not in out_empty
        assert "test_dup_a" in out_populated
        assert out_empty.strip()  # still produces some scaffolding

    def test_documents_false_positives(self):
        # AC-3 negative: false positives must be documented in the report
        out = render_markdown([])
        assert "false positives" in out.lower()
        assert "not bugs" in out.lower()


class TestArtifactExists:
    def test_research_artifact_committed(self):
        # AC-2: report file lives under research/. Glob matches any dated
        # sibling so the audit can re-run with a fresh date without breaking
        # this test.
        research_dir = REPO / "docs" / "ru" / "research"
        hits = sorted(research_dir.glob("tausik-1.4-pytest-dedupe-*.md"))
        assert hits, f"Missing pytest dedupe research artifact under {research_dir}"
        text = hits[-1].read_text(encoding="utf-8")
        assert "pytest dedupe audit" in text


def _venv_python(repo: Path) -> Path:
    """Return the project's venv python — Windows or POSIX layout."""
    win = repo / ".tausik" / "venv" / "Scripts" / "python.exe"
    if win.is_file():
        return win
    return repo / ".tausik" / "venv" / "bin" / "python"


def _run_audit_script(repo: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    """Invoke scripts/audit_pytest_dedupe.py via the project venv.

    UTF-8 IO is forced so Windows consoles don't choke on the Markdown
    output. Used by `test_real_repo_runs` and any future subprocess test
    that needs to drive the audit CLI directly.
    """
    return subprocess.run(
        [str(_venv_python(repo)), str(repo / "scripts" / "audit_pytest_dedupe.py"), *args],
        cwd=str(repo),
        capture_output=True,
        text=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


class TestCli:
    def test_real_repo_runs(self):
        r = _run_audit_script(REPO)
        assert r.returncode == 0
        assert "pytest dedupe audit" in r.stdout
