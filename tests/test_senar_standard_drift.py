"""SENAR corpus drift is detected by machine, like RENAR's (1.10, story F)."""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import senar_standard_drift as senar  # noqa: E402

_CORE = (
    "# SENAR Core\n"
    + "".join(f"### Rule {n}. R{n}\n" for n in range(1, 9))
    + "### Start Gate\n### Done Gate\n"
)
_GATES = (
    "## 8.6 Gate Properties\n" + "".join(f"{c}) **P{c}.** x\n" for c in "abcde") + "## 8.7 Next\n"
)


def _corpus(tmp_path, *, rules: int = 8, released: str = "1.5", claim: str = "1.5"):
    root = tmp_path / "senar"
    (root / "core" / "en").mkdir(parents=True)
    (root / "standard").mkdir()
    core = (
        _CORE
        if rules == 8
        else "# SENAR Core\n"
        + "".join(f"### Rule {n}. R{n}\n" for n in range(1, rules + 1))
        + "### Start Gate\n### Done Gate\n"
    )
    (root / "core" / "en" / "senar-core.md").write_text(core, encoding="utf-8")
    (root / "standard" / "08-quality-gates.md").write_text(_GATES, encoding="utf-8")
    (root / "CHANGELOG.md").write_text(
        f"# SENAR\n## v1.6 (unreleased)\n## v{released} (2026-09-07)\n## v1.4 (2026-09-04)\n## v1.3 (2026-03-25)\n",
        encoding="utf-8",
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text(
        f"TAUSIK claims SENAR v{claim} Core — that edition.\n", encoding="utf-8"
    )
    return str(root), str(repo)


def test_a_corpus_matching_the_claim_is_silent(tmp_path):
    root, repo = _corpus(tmp_path)
    assert senar.detect_senar_drift(root, repo) == []


def test_an_older_claim_names_the_releases_since(tmp_path):
    root, repo = _corpus(tmp_path, claim="1.3")
    kinds = {f["kind"]: f["message"] for f in senar.detect_senar_drift(root, repo)}
    assert "v1.5, v1.4 since" in kinds["edition-drift"]


def test_an_unreleased_heading_is_not_a_release(tmp_path):
    root, _ = _corpus(tmp_path)
    assert senar.released_versions(root)[0] == "1.5"


def test_a_different_core_rule_count_is_a_finding(tmp_path):
    """NEGATIVE: the standard changed shape — the matrix assumption is named."""
    root, repo = _corpus(tmp_path, rules=9)
    kinds = [f["kind"] for f in senar.detect_senar_drift(root, repo)]
    assert kinds == ["core-rules-drift"]


def test_no_corpus_is_not_checked_and_says_so():
    """NEGATIVE: an absent corpus is a sentence, not an empty verdict."""
    assert "NOT CHECKED" in senar.corpus_status(None)
    assert senar.corpus_root({senar.CORPUS_CONFIG_KEY: "/nowhere/at/all"}) is None


def test_a_path_without_the_parsed_files_is_unreadable(tmp_path):
    """NEGATIVE: the missing part is named."""
    (tmp_path / "empty").mkdir()
    kinds = [f["kind"] for f in senar.detect_senar_drift(str(tmp_path / "empty"), str(tmp_path))]
    assert kinds.count("corpus-unreadable") == 3
    level, text = senar.corpus_health({senar.CORPUS_CONFIG_KEY: str(tmp_path / "empty")})
    assert level == "warn" and "not the SENAR standard's source" in text


def test_the_live_corpus_is_readable_when_configured():
    root = senar.corpus_root()
    if root is None:
        pytest.skip("no SENAR corpus configured on this machine (senar_standard_corpus)")
    findings = senar.detect_senar_drift(root, _ROOT)
    assert not [f for f in findings if f["kind"] == "corpus-unreadable"], findings
    assert not [
        f
        for f in findings
        if f["kind"] in ("core-rules-drift", "core-gates-drift", "gate-properties-drift")
    ], findings
