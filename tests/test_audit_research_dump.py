"""Tests for scripts/audit_research_dump.py — stale research file detector."""

from __future__ import annotations

import os
import sys
import time

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import audit_research_dump as ard  # noqa: E402


def _make_research_file(repo_root, locale, name, content="dummy", days_old=0):
    d = repo_root / "docs" / locale / "research"
    d.mkdir(parents=True, exist_ok=True)
    f = d / name
    f.write_text(content, encoding="utf-8")
    if days_old:
        past = time.time() - days_old * 86400
        os.utime(f, (past, past))
    return f


def _make_ref_file(repo_root, sub, name, content):
    d = repo_root / sub
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(content, encoding="utf-8")


def test_empty_research_dirs(tmp_path):
    result = ard.audit_research_dump(str(tmp_path))
    assert result == {"candidates": [], "skipped_recent": 0, "skipped_referenced": 0, "scanned": 0}


def test_recent_file_skipped_as_recent(tmp_path):
    _make_research_file(tmp_path, "en", "fresh.md", days_old=5)
    result = ard.audit_research_dump(str(tmp_path), min_age_days=30)
    assert result["candidates"] == []
    assert result["skipped_recent"] == 1
    assert result["scanned"] == 1


def test_old_unreferenced_file_is_candidate(tmp_path):
    _make_research_file(tmp_path, "en", "stale.md", days_old=60)
    result = ard.audit_research_dump(str(tmp_path), min_age_days=30)
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["path"].endswith("stale.md")
    assert (
        result["candidates"][0]["age_days"] >= 59
    )  # floor division can produce 59 from 60-day mtime


def test_old_referenced_file_skipped(tmp_path):
    _make_research_file(tmp_path, "en", "referenced.md", days_old=60)
    _make_ref_file(tmp_path, "tests", "test_a.py", "# see referenced.md\n")
    result = ard.audit_research_dump(str(tmp_path), min_age_days=30)
    assert result["candidates"] == []
    assert result["skipped_referenced"] == 1


def test_age_threshold_boundary(tmp_path):
    """A file slightly past the boundary (age >= min_age_days) is a candidate.

    Use 31 days to avoid floor-division off-by-one (a 30-day mtime can floor to 29).
    """
    _make_research_file(tmp_path, "en", "edge.md", days_old=31)
    result = ard.audit_research_dump(str(tmp_path), min_age_days=30)
    assert len(result["candidates"]) == 1


def test_multiple_locales_scanned(tmp_path):
    _make_research_file(tmp_path, "en", "old-en.md", days_old=60)
    _make_research_file(tmp_path, "ru", "old-ru.md", days_old=60)
    result = ard.audit_research_dump(str(tmp_path), min_age_days=30)
    assert result["scanned"] == 2
    assert len(result["candidates"]) == 2


def test_changelog_reference_skips_candidate(tmp_path):
    _make_research_file(tmp_path, "en", "in-changelog.md", days_old=60)
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\nSee in-changelog.md for details.\n", encoding="utf-8"
    )
    result = ard.audit_research_dump(str(tmp_path), min_age_days=30)
    assert result["candidates"] == []
    assert result["skipped_referenced"] == 1
