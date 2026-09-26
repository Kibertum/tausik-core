"""The rules a consumer receives say what shape the code should have.

MEASURED, session #277, and the measurement is what started the task: neither
`bootstrap_templates.py` nor `bootstrap_templates_tiers.py` contained a single
mention of identifier language or of where a working note belongs — zero matches
for `ascii`, `identifier`, `naming`, `латиниц`, `имена`. The owner's observation
that consumer projects declare Russian variable names had nothing in the shipped
instructions to contradict it.

WHY THE SECTION IS ITS OWN AND NOT UNDER HARD CONSTRAINTS. Neither rule refuses
anything: the first is a `doctor` row, the second a line printed at closure.
Filing them with the non-negotiables would be the kind of small untruth this
project spends its tests preventing.

WHAT THIS FILE ALSO GUARDS, and it is the easier thing to get wrong: that nothing
added here asks the model to conserve tokens or write less. A harness that said so
got an agent reluctant to take on ambitious work, which costs more than any prose
it saves.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _sub in ("bootstrap", "scripts"):
    if str(_REPO / _sub) not in sys.path:
        sys.path.insert(0, str(_REPO / _sub))

import bootstrap_templates as bt  # noqa: E402


def _body() -> str:
    """Сгенерированное тело правил стандартного тира.

    Через настоящий сборщик, а не склейкой констант: проверяется, что секция
    ВОШЛА в сборку, а склейка вручную доказала бы только существование строки.
    """
    return bt.build_full_body("proj", ["python"], "Claude", ".claude")


CROSSCUTTING_SCOPE = ["bootstrap/"]

#: Phrasings that turn a description into a plea. Checked against the WHOLE set of
#: generated instructions, not only the new section: the trap is easy to step into
#: anywhere, and the cost falls on ambitious tasks rather than on prose.
_CONSERVATION_PLEAS = (
    "save tokens",
    "conserve token",
    "fewer comments",
    "be concise",
    "minimise output",
    "minimize output",
    "keep it short",
    "не трать токен",
    "экономь",
    "меньше комментариев",
)

#: Emphasis that literal models spiral on. The house style already avoids it; this
#: keeps the new section from reintroducing it.
_SHOUTING = ("MUST ", "NEVER ", "IMPORTANT", "DO NOT ", "ALWAYS ")


class TestBothRulesAreStated:
    @pytest.mark.parametrize(
        ("phrase", "why"),
        [
            pytest.param("Identifiers are ASCII", "the naming rule itself", id="naming_rule"),
            pytest.param("goes to `memory add`", "where a note belongs", id="note_destination"),
            pytest.param(
                "Identifier style", "the doctor row, so the rule can be found", id="doctor_row"
            ),
        ],
    )
    def test_the_section_states_it(self, phrase, why):
        """One claim per phrase, one test over all of them: three separate methods
        with a single `in` assertion each cover one path three times, which is what
        the dedupe ratchet is for."""
        assert phrase in bt.CODE_STYLE, why

    def test_each_reason_sits_in_the_same_bullet_as_its_rule(self):
        """Colocation, not mere presence. A reason parked at the end of the section
        belongs to no rule in particular, and the reader who doubts one rule will
        not go looking for its why three lines down.
        """
        bullets = [b for b in bt.CODE_STYLE.split("\n- **") if b.strip()][1:]
        assert len(bullets) == 2, "expected exactly two rules"
        naming = next(b for b in bullets if "ASCII" in b)
        note = next(b for b in bullets if "memory add" in b)
        assert "breaks quietly" in naming
        assert "paid for on every read" in note

    def test_the_invariant_is_explicitly_out_of_scope(self):
        """Without this the rule reads as "write fewer comments", which is the
        instruction this project declines to give."""
        assert "invariant" in bt.CODE_STYLE.lower()
        assert "is not the target" in bt.CODE_STYLE


class TestNothingAsksTheModelToDoLess:
    """The trap named in the source of this work, and the one with the highest
    cost: it is paid on ambitious tasks, where it is hardest to notice."""

    @pytest.mark.parametrize("plea", _CONSERVATION_PLEAS)
    def test_no_conservation_plea_in_the_new_section(self, plea):
        assert plea not in bt.CODE_STYLE.lower()

    @pytest.mark.parametrize("plea", _CONSERVATION_PLEAS)
    def test_no_conservation_plea_in_the_whole_instruction_set(self, plea):
        generated = _body()
        assert plea not in generated.lower()

    @pytest.mark.parametrize("shout", _SHOUTING)
    def test_the_new_section_does_not_shout(self, shout):
        assert shout not in bt.CODE_STYLE


class TestHardConstraintsAreNotBlurred:
    """AC-4. A new section must not dilute what actually refuses."""

    @pytest.mark.parametrize(
        "phrase",
        [
            pytest.param("No code without a task", id="rule_1"),
            pytest.param("QG-0 Context Gate", id="qg0"),
            pytest.param("QG-2 Implementation Gate", id="qg2"),
            pytest.param("No direct DB access", id="db"),
            pytest.param("ask before commit/push", id="git"),
        ],
    )
    def test_the_hard_rule_survives(self, phrase):
        assert phrase in bt.HARD_CONSTRAINTS

    def test_the_style_section_is_separate_from_the_hard_ones(self):
        """Neither style rule refuses anything, and saying otherwise in the file a
        fresh agent reads first would teach it to distrust the rest."""
        assert "Identifiers are ASCII" not in bt.HARD_CONSTRAINTS
        assert "non-negotiable" not in bt.CODE_STYLE


class TestTheRulesReachTheGeneratedFile:
    """AC-5. A section in a constant nobody assembles is not a shipped rule."""

    def test_the_section_is_assembled_into_claude_md(self):
        generated = _body()
        assert "Identifiers are ASCII" in generated
        assert "goes to `memory add`" in generated

    def test_it_sits_next_to_the_hard_constraints(self):
        """Order is not decoration: a rule about the shape of code is read while
        the reader is still reading rules, not after the command reference."""
        generated = _body()
        assert generated.index("Hard Constraints") < generated.index("Code Style")
        assert generated.index("Code Style") < generated.index("## Workflow")

    def test_a_freshly_generated_project_carries_it(self, tmp_path):
        """Через настоящий генератор в чистый каталог — то есть ровно тем путём,
        которым правила попадают к потребителю. Проверка константы доказала бы
        существование строки, а не то, что потребитель её увидит."""
        from bootstrap_generate import generate_claude_md

        generate_claude_md(str(tmp_path), "proj", ["python"], "standard", "off")
        text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Identifiers are ASCII" in text
        assert "goes to `memory add`" in text

    def test_this_repository_uses_a_hand_written_claude_md(self):
        """Замер, а не пропуск: собственный CLAUDE.md здесь написан руками и
        сгенерированной секции НЕ содержит. Сказать это вслух дешевле, чем
        оставить пропущенный тест, который читается как несделанная работа."""
        text = (_REPO / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Hard Constraints" not in text


class TestTheSectionStaysCheap:
    """It is injected into every session, so its own length is a line item."""

    def test_the_section_is_under_a_declared_ceiling(self):
        limit = 2000
        assert len(bt.CODE_STYLE) < limit, (
            f"{len(bt.CODE_STYLE)} chars — two rules grew into an essay; the "
            "reason belongs in the docs page, the rule belongs here"
        )

    def test_it_says_two_rules_and_ships_two(self):
        assert bt.CODE_STYLE.count("\n- **") == 2
