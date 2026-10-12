"""The answer budget is on the retelling, not on the proof (convention #768).

Evidence is DECLARED by form: a closed fenced block or a markdown table row.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from answer_shape import evidence_words, score  # noqa: E402

FENCE = "`" * 3


def test_fenced_output_and_table_rows_are_evidence_not_retelling():
    text = f"Closed.\n\n{FENCE}\nFAILED tests/a.py::t\n{FENCE}\n| n | p90 |\n|---|---|\n| 10 | 453 |\nprose words here"
    s = score(text)
    assert s.evidence == evidence_words(text) > 0
    assert s.words == 4  # "Closed" + "prose words here"


def test_an_answer_with_no_evidence_is_counted_whole():
    """NEGATIVE (AC-3): nothing is exempt without the declared form."""
    text = "This is a long answer that merely claims to be evidence of everything."
    assert score(text).evidence == 0
    assert score(text).words == 13


def test_an_unclosed_fence_does_not_exempt_the_rest():
    """NEGATIVE: one stray fence cannot turn the whole answer into proof."""
    text = f"Done.\n{FENCE}\nall of this is retelling\nand so is this"
    assert score(text).evidence == 0
