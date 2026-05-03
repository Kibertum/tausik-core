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
    def test_empty_groups_clean_message(self):
        out = render_markdown([])
        assert "No duplicate test scenarios detected" in out
        assert "Documented false positives" in out

    def test_documents_false_positives(self):
        # AC-3 negative: false positives must be documented in the report
        out = render_markdown([])
        assert "false positives" in out.lower()
        assert "not bugs" in out.lower()


class TestArtifactExists:
    def test_research_artifact_committed(self):
        # AC-2: report file lives under research/
        path = REPO / "docs" / "ru" / "research" / "tausik-1.4-pytest-dedupe-2026-05-02.md"
        assert path.is_file(), f"Missing research artifact at {path}"
        text = path.read_text(encoding="utf-8")
        assert "pytest dedupe audit" in text


class TestCli:
    def test_real_repo_runs(self):
        py = (
            REPO / ".tausik" / "venv" / "Scripts" / "python.exe"
            if (REPO / ".tausik" / "venv" / "Scripts" / "python.exe").is_file()
            else REPO / ".tausik" / "venv" / "bin" / "python"
        )
        r = subprocess.run(
            [str(py), str(REPO / "scripts" / "audit_pytest_dedupe.py")],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        assert r.returncode == 0
        assert "pytest dedupe audit" in r.stdout
