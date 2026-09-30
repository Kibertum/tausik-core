"""The four answer rules decision #407 made ours are carried by the shipped block.

They came from reading ayghri/i-have-adhd and were restated in our words: numbered
multi-step work, a ceiling on items per group, one tangent once, estimates in minutes.
Nothing else pinned them, so a rewrite for length could drop one in silence.
"""

from __future__ import annotations

import os
import re
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "bootstrap"))

from bootstrap_templates import ANSWER_SHAPE  # noqa: E402

RULES = {
    "numbered steps": r"numbered",
    "one action per step": r"one action each",
    "last step doable in two minutes": r"two minutes",
    "five items per group": r"five items per\s+group",
    "one tangent, once": r"one tangent, once",
    "estimates in minutes": r"estimates in minutes",
}


@pytest.mark.parametrize("name,rx", RULES.items(), ids=list(RULES))
def test_the_shipped_block_carries_the_rule(name, rx):
    assert re.search(rx, ANSWER_SHAPE, re.I), name


def test_no_vendored_copy_came_back():
    assert not os.path.isdir(os.path.join(_ROOT, "harness", "skills", "i-have-adhd"))
