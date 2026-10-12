"""doctor names the state of the RENAR corpus it reads (task G1 of 1.10).

The standard moved from `standards/renar` (now the site) to
`standards/renar-standart`; the configured path still resolved, the detector
read nothing and could only say "unreadable". The three states below call for
different actions and must not collapse into one.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from renar_standard_drift import CORPUS_CONFIG_KEY, corpus_health  # noqa: E402


def test_unconfigured_is_a_dormant_ok():
    level, text = corpus_health({})
    assert level == "ok" and "dormant" in text


def test_a_missing_path_is_a_warning(tmp_path):
    level, text = corpus_health({CORPUS_CONFIG_KEY: str(tmp_path / "nowhere")})
    assert level == "warn" and "does not exist" in text


def test_a_path_without_chapters_is_not_the_standard(tmp_path):
    """NEGATIVE: the case that happened — a real directory, the wrong repository."""
    (tmp_path / "site" / "content").mkdir(parents=True)
    level, text = corpus_health({CORPUS_CONFIG_KEY: str(tmp_path / "site")})
    assert level == "warn" and "no standard/ chapters" in text


def test_a_real_corpus_reports_version_and_chapters(tmp_path):
    std = tmp_path / "renar-standart" / "standard"
    std.mkdir(parents=True)
    (std / "13-conformance.md").write_text("**Часть RENAR Standard v1.1**\n", encoding="utf-8")
    level, text = corpus_health({CORPUS_CONFIG_KEY: str(tmp_path / "renar-standart")})
    assert level == "ok" and "RENAR v1.1" in text and "1 chapter file(s)" in text


def test_a_corpus_without_a_banner_is_a_warning(tmp_path):
    """NEGATIVE: chapters present but no version — not silently green."""
    std = tmp_path / "c" / "standard"
    std.mkdir(parents=True)
    (std / "13-conformance.md").write_text("no banner here\n", encoding="utf-8")
    level, text = corpus_health({CORPUS_CONFIG_KEY: str(tmp_path / "c")})
    assert level == "warn" and "no version banner" in text
