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
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import doc_drift_common as common  # noqa: E402
import doc_drift_fixes as fixes  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "docs/"]


class TestThePairFormIsRepairedNotOnlyDetected:
    """AC3 and AC4."""

    @property
    def _pattern(self):
        return common._MCP_COUNT_PAIR_PATTERN[0]

    @pytest.mark.parametrize(
        "before,after",
        [
            pytest.param("(145 project + 7 brain)", "(146 project + 7 brain)", id="parenthesised"),
            pytest.param(
                "**145 project + 7 brain = 152 tools**",
                "**146 project + 7 brain = 152 tools**",
                id="bare_pair_inside_bold",
            ),
            pytest.param("145 project + 7 brain", "146 project + 7 brain", id="no_punctuation"),
        ],
    )
    def test_the_stale_half_is_rewritten(self, before, after):
        result, changed = fixes._fix_pair(before, self._pattern, 146, 7)
        assert changed is True
        assert result == after

    def test_the_correct_half_is_left_alone(self):
        """Each half is judged on its own: a pair whose second number is already
        right must not be 'fixed' into the same value it already had."""
        text = "(145 project + 7 brain)"
        result, _ = fixes._fix_pair(text, self._pattern, 146, 7)
        assert result.count("7 brain") == 1
        assert "7 brain" in result

    def test_an_already_correct_pair_is_not_touched(self):
        text = "the (146 project + 7 brain) pair"
        result, changed = fixes._fix_pair(text, self._pattern, 146, 7)
        assert changed is False
        assert result == text

    def test_a_width_change_does_not_corrupt_the_second_number(self):
        """The offsets come from the ORIGINAL match. Replacing the first group
        first shifts everything after it, so 99 -> 146 would land the second
        substitution in the wrong place if the two were applied left to right.
        145 -> 146 would never have caught this: the widths match."""
        result, changed = fixes._fix_pair("(99 project + 7 brain)", self._pattern, 146, 12)
        assert changed is True
        assert result == "(146 project + 12 brain)"


class TestTheRepairRespectsTheSameBoundariesAsTheScan:
    """AC5. A fixer that edits where the scanner does not look would rewrite
    examples and frozen history — the opposite of keeping documents true."""

    def test_a_pair_inside_a_fenced_block_is_untouched(self):
        text = "before\n```\n(145 project + 7 brain)\n```\nafter\n"
        result, changed = fixes._fix_pair(text, common._MCP_COUNT_PAIR_PATTERN[0], 146, 7)
        assert changed is False
        assert result == text

    def test_a_pair_outside_the_fence_is_still_repaired(self):
        """PREMISE. If the guard above passed because nothing is ever repaired,
        it would assert nothing at all."""
        text = "```\ncode\n```\n(145 project + 7 brain)\n"
        result, changed = fixes._fix_pair(text, common._MCP_COUNT_PAIR_PATTERN[0], 146, 7)
        assert changed is True
        assert "(146 project + 7 brain)" in result


class TestEveryDetectedFamilyHasARepairer:
    """AC6. The rule that keeps this from happening again, checked by machine
    rather than promised in a comment."""

    def test_the_pair_pattern_reaches_the_fixer(self):
        source = (_REPO / "scripts" / "doc_drift_fixes.py").read_text(encoding="utf-8")
        assert "_MCP_COUNT_PAIR_PATTERN" in source, (
            "the pair form is detected by the scanner and repaired by nobody — "
            "the exact gap that cost about fifteen manual edits for one integer"
        )

    @pytest.mark.parametrize(
        "family",
        [
            "_MCP_COUNT_PATTERNS",
            "_MCP_COUNT_PAIR_PATTERN",
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
