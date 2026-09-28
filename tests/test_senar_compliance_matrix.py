"""The compliance matrix has exactly the rows SENAR Core has (1.10, story F).

The matrix used to list Standard rules 9.2, 9.3, 9.5 under "Core" — SENAR Core
has none of them. Now each Core section is counted against the corpus when one
is configured (`senar_standard_corpus`), and against the Core shape the SENAR
drift detector names otherwise; the citations themselves are resolved by
`senar_self_check` (tests/test_senar_self_check.py).
"""

from __future__ import annotations

from pathlib import Path

import os
import re
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import senar_standard_drift as senar  # noqa: E402

CROSSCUTTING_SCOPE = ["docs/en/senar-compliance-matrix.md", "docs/ru/senar-compliance-matrix.md"]

_SECTIONS = {
    "en": (
        "## Core rules",
        "## Core gates",
        "## Three things that make a gate a gate",
        "## Core metrics",
    ),
    "ru": (
        "## Правила Core",
        "## Гейты Core",
        "## Три вещи, делающие гейт гейтом",
        "## Метрики Core",
    ),
}


def _rows(lang: str, heading: str) -> int:
    text = Path(_ROOT, "docs", lang, "senar-compliance-matrix.md").read_text(encoding="utf-8")
    block = text.split(heading, 1)[1].split("\n## ", 1)[0]
    lines = [ln for ln in block.splitlines() if ln.startswith("|")]
    return max(0, len(lines) - 2)  # header + separator


def _expected() -> tuple[int, int, int, int]:
    root = senar.corpus_root()
    rules, gates = senar.EXPECTED_CORE_RULES, len(senar.EXPECTED_CORE_GATES)
    if root is not None:
        shape = senar.core_shape(root)
        if shape:
            rules, gates = shape["rules"], len(shape["gates"])
    return rules, gates, 3, 2  # Core requires properties a, c, e; Core names FPSR and Dead End Rate


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_each_core_section_has_the_corpus_row_count(lang):
    got = tuple(_rows(lang, h) for h in _SECTIONS[lang])
    assert got == _expected()


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_no_standard_rule_is_listed_under_core(lang):
    """NEGATIVE: the old defect — Standard 9.x rows inside the Core sections."""
    text = Path(_ROOT, "docs", lang, "senar-compliance-matrix.md").read_text(encoding="utf-8")
    core = text.split(_SECTIONS[lang][0], 1)[1].split(_SECTIONS[lang][3], 1)[0]
    assert not re.search(r"^\| 9\.\d", core, re.M)
