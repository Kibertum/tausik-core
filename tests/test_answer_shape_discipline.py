"""The four answer rules decision #407 made ours are carried by the shipped block.

They came from reading ayghri/i-have-adhd and were restated in our words: numbered
multi-step work, a ceiling on items per group, one tangent once, estimates in minutes.
Nothing else pinned them, so a rewrite for length could drop one in silence.
"""

from __future__ import annotations

import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "bootstrap"))

from bootstrap_templates import ANSWER_SHAPE  # noqa: E402

RULES = {
    "numbered steps": r"numbered",
    "one action per step": r"one action each",
    "last step doable in two minutes": r"two minutes|≤2 min",
    "five items per group": r"five items per\s+group|≤5/group",
    "one tangent, once": r"one tangent, once|tangent last",
    "estimates when useful": r"estimate",
}


def test_the_shipped_block_carries_every_rule():
    missing = [name for name, rx in RULES.items() if not re.search(rx, ANSWER_SHAPE, re.I)]
    assert not missing, missing
