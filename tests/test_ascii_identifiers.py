"""Product identifiers stay ASCII; prose stays in whatever language reads best.

MEASURED, session #277. Cyrillic identifiers in `scripts`, `bootstrap`, `harness`:
zero. In `tests`: 271 across 20 files. The owner observes consumer projects
declaring Russian variable names, and those two numbers name the mechanism — the
product tree has none, so the house style an agent copies is the one it sees in
the tests.

WHY THE TESTS ARE A DECLARED REMAINDER RATHER THAN A CLEANUP. Renaming the 271
would break 83 evidence citations across 21 tasks that point at Cyrillic pytest
node ids. The task journal is append-only, so those citations cannot be rewritten
with them; turning working evidence into unresolvable references is the exact harm
this project keeps a detector for. The remainder may only shrink.

THIS FILE IS DELIBERATELY NAMED IN ASCII, docstrings and all. It is the first test
written after the rule, and a rule whose own guard breaks it is a rule nobody
follows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import ascii_identifiers as ai  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "bootstrap/", "harness/", "tests/"]

_PRODUCT_TREES = ("scripts", "bootstrap", "harness")


@pytest.fixture(scope="module")
def ratchet() -> dict:
    node = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
    return node["ascii_identifiers"]


class TestProductTreeHoldsAtZero:
    """The ratchet that matters: product code is what a consumer copies."""

    def test_no_non_ascii_names_in_product_code(self, ratchet):
        found = ai.scan_tree(_REPO, _PRODUCT_TREES)
        assert ai.count(found) <= ratchet["product_names"], ai.report(found)

    def test_the_baseline_is_zero_and_says_so(self, ratchet):
        assert ratchet["product_names"] == 0

    def test_the_scan_actually_reads_the_tree(self):
        """A scan that inspects nothing reports zero, which is the quietest way to
        switch a ratchet off."""
        names = ai._names(
            __import__("ast").parse(
                (_REPO / "scripts" / "ascii_identifiers.py").read_text(encoding="utf-8")
            )
        )
        assert len(names) > 30


class TestProseIsNotTheSubject:
    """A rule that also policed prose would be switched off the first day: the
    rationale in this project's docstrings is written in Russian on purpose."""

    @pytest.mark.parametrize(
        "src",
        [
            pytest.param(
                'def handler():\n    """Проверка отказа: причина названа."""\n', id="docstring"
            ),
            pytest.param("value = 1  # замер смены #277: было 271\n", id="comment"),
            pytest.param('MESSAGE = "имён вне ASCII нет"\n', id="string_literal"),
        ],
    )
    def test_prose_in_any_language_passes(self, src):
        """One claim, three carriers. Separate tests would say the same thing
        three times, which the dedupe ratchet reads as covering one path twice."""
        assert ai.offenders_in_source(src) == []


class TestTheGuardCanGoRed:
    """Zero means nothing unless the check can refuse."""

    @pytest.mark.parametrize(
        ("src", "what"),
        [
            pytest.param("def проверка():\n    pass\n", "function", id="function"),
            pytest.param("class Проверка:\n    pass\n", "class", id="class"),
            pytest.param("def f(значение):\n    pass\n", "argument", id="argument"),
            pytest.param("итог = 1\n", "assignment", id="assignment"),
            pytest.param("for шаг in range(3):\n    pass\n", "for target", id="for"),
            pytest.param("import os as ос\n", "import alias", id="alias"),
            pytest.param(
                "try:\n    pass\nexcept ValueError as ошибка:\n    pass\n", "except", id="except"
            ),
        ],
    )
    def test_each_binding_form_is_caught(self, src, what):
        assert ai.offenders_in_source(src), f"{what} slipped through"

    def test_non_cyrillic_non_ascii_is_caught_too(self):
        """Listing alphabets would mean missing the next one: a Greek or accented
        name breaks a trace exactly the same way."""
        assert ai.offenders_in_source("def naïve():\n    pass\n")
        assert ai.offenders_in_source("def ταυ():\n    pass\n")

    def test_a_read_is_not_a_declaration_but_a_write_is(self):
        """Counting every USE would report one offence as many, and the fix list
        would point at files that declare nothing. Both halves are asserted
        together: "reads are ignored" is only meaningful beside "writes are not".
        """
        assert ai.offenders_in_source("print(имя)\n") == []
        assert [n for n, _ in ai.offenders_in_source("имя = 1\n")] == ["имя"]

    def test_a_broken_file_does_not_stop_the_tree_walk(self, tmp_path):
        """Проверяется ОБХОД, а не разбор одной строки: файл, который и без нас не
        собирается, не должен уносить с собой всё дерево. Иначе проверку стиля
        выключат вместе с настоящей поломкой."""
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "broken.py").write_text("def (:\n", encoding="utf-8")
        (tmp_path / "pkg" / "bad_name.py").write_text("итог = 1\n", encoding="utf-8")
        found = ai.scan_tree(tmp_path, ("pkg",))
        assert list(found) == ["pkg/bad_name.py"]
        assert ai.count(found) == 1


class TestTestTreeIsADeclaredRemainder:
    """Not indulgence — a measurement. See the module docstring."""

    def test_the_remainder_does_not_grow(self, ratchet):
        found = ai.scan_tree(_REPO, ("tests",))
        assert ai.count(found) <= ratchet["test_names"], (
            "non-ASCII test names GREW: "
            f"{ai.count(found)} > {ratchet['test_names']}. New tests are named in "
            "ASCII; the remainder shrinks as these tests die out.\n" + ai.report(found, limit=4)
        )

    def test_the_reason_is_recorded_next_to_the_number(self, ratchet):
        """A number without its reason reads, six months on, as someone giving up."""
        comment = ratchet["_baseline_comment"]
        assert "83" in comment and "append-only" in comment
        assert "may only shrink" in comment or "может только уменьшаться" in comment

    def test_this_file_obeys_the_rule_it_guards(self):
        found = ai.offenders_in_source(Path(__file__).read_text(encoding="utf-8"))
        names = [n for n, _ in found]
        assert not names, f"the guard breaks its own rule: {names}"


class TestReportNamesTheFix:
    """A refusal that gives only a count sends the reader hunting."""

    def test_report_carries_file_line_and_name(self):
        found = {"scripts/x.py": [("итог", 12)]}
        text = ai.report(found)
        assert "scripts/x.py" in text and "итог" in text and "12" in text

    def test_empty_report_says_so_plainly(self):
        assert "нет" in ai.report({})
