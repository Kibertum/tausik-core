"""Prose inside code is English, and the remainder is a ratchet rather than a campaign.

THE RULE IS THE OWNER'S (decision #404) and it supersedes half of convention #745. That one
settled that identifiers must be ASCII and said, in as many words, that docstrings and
comments could take any language; the shipped template said the same. So the rule the owner
had asked for repeatedly existed nowhere, and the file a new project is handed argued against
it.

TWO NUMBERS BECAUSE THEY CARRY DIFFERENT PRICES. Prose costs only the rewrite. Identifiers do
not: 83 evidence citations in 21 closed tasks point at Cyrillic pytest node ids, journals are
append-only, and renaming would turn live evidence into unresolvable references. The exemption
was priced before it was declared, and the two counts are kept apart here so it cannot quietly
grow into the prose number.

NO MASS TRANSLATION. 5,348 lines in one pass is the size of edit this project refuses to make
without a task per unit of meaning; the ratchet lets the number fall as files are touched for
their own reasons and refuses to let it rise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import prose_language as pgl  # noqa: E402

NEWLINE = chr(10)
CYR_A = chr(0x0430)  # a Cyrillic letter, built rather than written: see the module's own note
WORD = CYR_A * 4


@pytest.fixture
def tree(tmp_path):
    """A source tree with prose, an identifier, and a clean file."""

    def build(files: dict[str, str]):
        for rel, body in files.items():
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        return str(tmp_path)

    return build


class TestProseAndIdentifiersAreCountedApart:
    def test_a_comment_is_prose(self, tree):
        root = tree({"scripts/a.py": f"x = 1  # {WORD}\n"})
        got = pgl.count(root, roots=("scripts",))
        assert got.prose_lines == 1 and got.files == 1 and got.identifiers == 0

    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            pytest.param(f'"""{WORD}."""' + NEWLINE + "x = 1" + NEWLINE, 1, id="docstring"),
            pytest.param(f'x = "{WORD}"' + NEWLINE, 1, id="string_literal"),
            pytest.param(
                f'"""{WORD}' + NEWLINE + WORD + NEWLINE + '"""' + NEWLINE, 2, id="two_lines"
            ),
        ],
    )
    def test_prose_is_counted_wherever_it_sits(self, tree, body, expected):
        """Docstring, literal, and a docstring spanning lines: the unit is the LINE, because
        that is what a reader scrolls past and what a translation rewrites."""
        root = tree({"scripts/a.py": body})
        assert pgl.count(root, roots=("scripts",)).prose_lines == expected

    def test_a_defined_name_is_an_identifier_and_not_double_counted(self, tree):
        """The def line carries the name AND the prose character; counting it in both would
        make the exemption look like prose and hide it from the rule it is exempt from."""
        root = tree({"tests/t.py": f"def test_{WORD}():\n    pass\n"})
        got = pgl.count(root, roots=("tests",))
        assert got.identifiers == 1 and got.prose_lines == 0

    def test_a_clean_file_counts_as_nothing_and_not_as_a_file(self, tree):
        root = tree({"scripts/a.py": "# plain english\nx = 1\n"})
        got = pgl.count(root, roots=("scripts",))
        assert got == pgl.Count(0, 0, 0)

    def test_the_detector_does_not_count_its_own_pattern(self):
        """It did on the first run: `ruff format` collapsed the escape form into literal
        characters. A detector that is its own finding is the class this project keeps
        catching, so the pattern is built with `chr()`."""
        assert pgl.count_file(str(_REPO / "scripts" / "prose_language.py")) == (0, 0)

    def test_an_unparseable_file_is_not_this_check_s_finding(self, tree):
        """Something else in the tree fails on it first; reporting it here would send the
        reader to the wrong place."""
        root = tree({"scripts/broken.py": f"def (:\n  # {WORD}\n"})
        assert pgl.count(root, roots=("scripts",)) == pgl.Count(0, 0, 0)

    def test_pycache_is_not_source(self, tree):
        root = tree({"scripts/__pycache__/a.py": f"# {WORD}\n"})
        assert pgl.count(root, roots=("scripts",)).prose_lines == 0


class TestGrowthIsTheSignal:
    def _gates(self, tmp_path, node):
        (tmp_path / "tausik").mkdir(exist_ok=True)
        (tmp_path / "tausik" / "gates.json").write_text(
            json.dumps({pgl.GATES_KEY: node}), encoding="utf-8"
        )

    def test_more_prose_than_the_baseline_warns_and_names_the_decision(self, tmp_path, tree):
        tree({"scripts/a.py": f"# {WORD}\n# {WORD}\n"})
        self._gates(tmp_path, {"prose_lines": 1, "identifiers": 0})
        level, detail, _ = pgl.check(str(tmp_path))
        assert level == "warn" and "GREW" in detail and "#404" in detail

    def test_more_identifiers_than_the_baseline_warns_too(self, tmp_path, tree):
        tree({"tests/t.py": f"def test_{WORD}():\n    pass\n"})
        self._gates(tmp_path, {"prose_lines": 99, "identifiers": 0})
        level, detail, _ = pgl.check(str(tmp_path))
        assert level == "warn" and "identifiers" in detail

    def test_shrinking_passes_and_asks_for_the_lower_number(self, tmp_path, tree):
        tree({"scripts/a.py": f"# {WORD}\n"})
        self._gates(tmp_path, {"prose_lines": 50, "identifiers": 5})
        level, detail, _ = pgl.check(str(tmp_path))
        assert level == "ok" and "shrank" in detail and "gates.json" in detail

    def test_no_baseline_prints_the_numbers_to_record(self, tmp_path, tree):
        tree({"scripts/a.py": f"# {WORD}\n"})
        level, detail, _ = pgl.check(str(tmp_path))
        assert level == "absent" and "prose_lines 1" in detail


class TestTheExemptionSurvivesAndIsPriced:
    def test_the_recorded_baseline_keeps_the_identifiers_apart(self):
        base = pgl.baseline(str(_REPO))
        assert base, "the live repository must carry a recorded baseline"
        assert base["identifiers"] == 269
        assert base["prose_lines"] > base["identifiers"]

    def test_the_reason_names_the_price_rather_than_a_preference(self):
        """AC-4: identifiers stay because renaming breaks live evidence, not because anyone
        prefers them. A number with no price behind it is the next thing somebody raises."""
        note = pgl.baseline(str(_REPO)).get("_comment", "")
        assert "83 evidence citations" in note and "append-only" in note
        assert "only shrink" in note

    def test_the_live_tree_is_not_above_its_baseline(self):
        level, detail, _ = pgl.check(str(_REPO))
        assert level == "ok", detail


class TestTheShippedRuleSaysIt:
    def test_the_generated_instructions_ask_for_english_code(self):
        """The template used to say the opposite in as many words, which is why the owner
        could ask repeatedly and find nothing had changed."""
        sys.path.insert(0, str(_REPO / "bootstrap"))
        from bootstrap_templates import CODE_STYLE

        assert "written in English" in CODE_STYLE
        assert "any language" not in CODE_STYLE

    def test_it_does_not_reach_the_user_s_reply(self):
        """The boundary matters as much as the rule: answers stay in the user's language."""
        sys.path.insert(0, str(_REPO / "bootstrap"))
        from bootstrap_templates import CODE_STYLE

        assert "user's language" in CODE_STYLE

    def test_this_project_states_it_too(self):
        """The needle is BUILT, not written: a test that spells the rule out in the very
        script the rule is about would add a line to the number it guards — which it did,
        and the ratchet caught it on the next run."""
        text = (_REPO / "CLAUDE.md").read_text(encoding="utf-8")
        needle = "".join(chr(c) for c in (0x430, 0x43D, 0x433, 0x43B))  # 'angl' in Cyrillic
        assert "404" in text and needle in text.lower()
