"""A detector without a repairer forces by hand the work it exists to automate.

MEASURED (session #234). Raising the MCP tool count from 145 to 146 left EIGHT
references of the form `(145 project + 7 brain)` across seven files, and
`gen_doc_constants.py --write` finished RED:

    drift remains after --write; a ref is outside the known patterns.
    Fix it by hand or widen the scanner.

The scanner had known that form since review #208. The repairer never learned
it: `_MCP_COUNT_PAIR_PATTERN` was imported by `doc_drift_scanners` and by
nothing else. So a number that lives in one generated file had to be edited by
hand in seven documents — about fifteen manual edits for one changed integer.

WORSE THAN THE LABOUR: a scan that reports drift it cannot fix reads, to anyone
running `--write`, as "the drift is covered". It is not.

The pair form itself is gone: the brain server left with the Notion transport
(decision #358), so `(N project + M brain)` is no longer a count the repository
computes and neither side carries the pattern. The rule below still holds for
every family that remains.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import doc_drift_common as common  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "docs/"]


class TestEveryDetectedFamilyHasARepairer:
    """AC6. The rule that keeps this from happening again, checked by machine
    rather than promised in a comment."""

    @pytest.mark.parametrize(
        "family",
        [
            "_MCP_COUNT_PATTERNS",
            "_TEST_COUNT_PATTERNS",
            "_CODE_COUNT_PATTERNS",
        ],
    )
    def test_each_count_family_is_known_to_both_sides(self, family):
        """Named one by one rather than derived from a list, because a
        derivation from the same module would pass by construction and prove
        nothing about the two sides agreeing."""
        scanner = (_REPO / "scripts" / "doc_drift_scanners.py").read_text(encoding="utf-8")
        fixer = (_REPO / "scripts" / "doc_drift_fixes.py").read_text(encoding="utf-8")
        assert hasattr(common, family), f"{family} left doc_drift_common"
        assert family in scanner, f"{family} is not scanned"
        assert family in fixer, f"{family} is scanned but never repaired"


class TestTheSplitDescribesItself:
    """AC7. `doc_drift_scanners` was corrected to "four-module split" and this
    one was missed — the same self-description drift the whole file guards."""

    def test_the_tables_module_does_not_claim_to_be_the_third_of_three(self):
        text = (_REPO / "scripts" / "doc_drift_tables.py").read_text(encoding="utf-8")
        head = text[:1200]
        assert "Third module" not in head, (
            "the split is four modules (common, scanners, fixes, tables); the "
            "docstring still counts three"
        )
