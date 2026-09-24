"""`scope-narrower-than-diff` is explained, not left to read as a cache miss (github#12)."""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from render_verify import _status_explained  # noqa: E402
from verify_cached_run import SCOPE_NARROWER  # noqa: E402


def test_the_status_names_what_happened_and_what_to_do():
    lines = _status_explained(
        {"status": SCOPE_NARROWER, "scope_description": {"undeclared_count": 58}}
    )
    assert len(lines) == 1
    assert "58 changed file(s)" in lines[0]
    assert "the run happened" in lines[0] and "--relevant-files" in lines[0]


def test_a_consistent_scope_gets_no_explanation():
    """NEGATIVE: miss and hit are what they say; no sentence is added."""
    assert _status_explained({"status": "miss"}) == []
    assert _status_explained({"status": "hit"}) == []


def test_the_old_name_is_gone():
    assert SCOPE_NARROWER == "scope-narrower-than-diff"
    src = open(os.path.join(_ROOT, "scripts", "verify_cached_run.py"), encoding="utf-8").read()
    assert 'cache_status = "git-mismatch"' not in src
