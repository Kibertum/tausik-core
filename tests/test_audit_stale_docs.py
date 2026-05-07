"""Tests for `scripts/audit_stale_docs.py` (v14-audit-stale-docs).

Covers:
  AC-1 — markdown report via the CLI.
  AC-2 — stale criteria: not referenced anywhere; root docs always kept;
    research / release-notes archives excluded by glob.
  AC-3 (negative) — must-keep docs (root README, mirror partner of a
    referenced doc) are NOT flagged stale.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from audit_stale_docs import (  # noqa: E402
    DEFAULT_EXCLUDES,
    ROOT_DOCS,
    _is_excluded,
    _mirror_partner,
    collect_stale,
)

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    docs_en = tmp_path / "docs" / "en"
    docs_ru = tmp_path / "docs" / "ru"
    docs_en.mkdir(parents=True)
    docs_ru.mkdir(parents=True)
    research_ru = tmp_path / "docs" / "ru" / "research"
    research_ru.mkdir(parents=True)

    # Linked from README → not stale; its RU mirror also stays
    (docs_en / "intro.md").write_text("intro EN\n")
    (docs_ru / "intro.md").write_text("intro RU\n")

    # Truly stale — nothing links to it
    (docs_en / "lonely-doc.md").write_text("nobody links here\n")

    # Inside research/* — excluded by glob even if unreferenced
    (research_ru / "old-spike.md").write_text("archived\n")

    # Inbound link source: only `intro.md` mentioned
    (tmp_path / "README.md").write_text("See [intro](docs/en/intro.md)\n")
    return tmp_path


class TestExclusion:
    @pytest.mark.parametrize(
        "path",
        [
            pytest.param("docs/en/research/old.md", id="research_excluded"),
            pytest.param("docs/_generated/x.md", id="generated_excluded"),
            pytest.param("docs/en/release-notes/v1.4.md", id="release_notes_excluded"),
        ],
    )
    def test_excluded_paths(self, path):
        assert _is_excluded(path, DEFAULT_EXCLUDES)

    def test_unrelated_path_not_excluded(self):
        assert not _is_excluded("docs/en/cli.md", DEFAULT_EXCLUDES)


class TestMirrorPartner:
    @pytest.mark.parametrize(
        "input_path,expected",
        [
            pytest.param("docs/en/cli.md", "docs/ru/cli.md", id="en_partner"),
            pytest.param("docs/ru/cli.md", "docs/en/cli.md", id="ru_partner"),
        ],
    )
    def test_partner_swap(self, input_path, expected):
        assert _mirror_partner(input_path) == expected

    def test_no_partner_for_root(self):
        assert _mirror_partner("docs/README.md") is None


class TestCollectStale:
    def test_lonely_reported(self, fake_repo: Path):
        stale = collect_stale(fake_repo)
        assert "docs/en/lonely-doc.md" in stale

    @pytest.mark.parametrize(
        "path",
        [
            pytest.param("docs/en/intro.md", id="referenced_doc_not_reported"),
            # AC-3 negative: README references EN intro; the RU mirror must NOT be stale
            pytest.param("docs/ru/intro.md", id="mirror_partner_protected"),
            # AC-2: research archive is excluded by glob, never reported
            pytest.param("docs/ru/research/old-spike.md", id="research_excluded"),
        ],
    )
    def test_path_not_in_stale(self, fake_repo: Path, path):
        stale = collect_stale(fake_repo)
        assert path not in stale

    def test_root_docs_always_safe(self, fake_repo: Path):
        # ROOT_DOCS list shouldn't be flagged even if unreferenced
        for rel in ROOT_DOCS:
            assert rel not in collect_stale(fake_repo)


class TestCli:
    def test_real_repo_runs(self):
        py = (
            REPO / ".tausik" / "venv" / "Scripts" / "python.exe"
            if (REPO / ".tausik" / "venv" / "Scripts" / "python.exe").is_file()
            else REPO / ".tausik" / "venv" / "bin" / "python"
        )
        r = subprocess.run(
            [str(py), str(REPO / "scripts" / "audit_stale_docs.py")],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        assert r.returncode == 0, r.stderr
        assert "Stale-docs audit" in r.stdout
