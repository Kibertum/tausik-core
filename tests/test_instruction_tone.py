"""The shipped instructions describe; they do not command or plead.

MEASURED FIRST, AND IT CORRECTED THE TASK THAT ORDERED IT. The task was filed
saying the generated instructions were built on caps and imperatives. They were
not: the body carried seven markers across 159 lines — one `MUST`, four
`Always`/`Never`, one `non-negotiable`, one `strictly` — and is written in English
throughout. The caps-and-`ЖЁСТКИЕ` description fits this repository's own
hand-written CLAUDE.md, which is not what ships to anyone. Cursor's "cut two thirds
of the system prompt" does not transfer to a body that was already this dense.

So the work was seven edits, each labelled with its reason, rather than a rewrite:

  delete   "Follow these instructions strictly." — a capable model follows what it
           is given; the sentence is the category the source says to cut.
  rewrite  "Hard Constraints (non-negotiable)" — "Hard" already said it.
  rewrite  "Never raw SQLite" — into the consequence: raw writes go past the
           projections and the audit trail. A reader who knows why looks for no
           way round.
  delete   "Always request user confirmation." — repeats "ask before commit/push".
  rewrite  "you MUST … FIRST" — into where the recorded answer is.
  rewrite  "Never your host's own memory" — into the fact that nothing reads it back.
  rewrite  "Always respond in the user's language" — kept as a statement, NOT
           deleted: that models default to the user's language cannot be shown from
           here, and the cost of being wrong is answers in the wrong language.

WHAT THIS FILE GUARDS GOING FORWARD is the property, not the seven: zero emphasis
markers, and no sentence anywhere asking the model to spend less. The second half
matters more — a harness that asks for thrift gets an agent reluctant to take on
ambitious work, and that is paid on exactly the tasks worth doing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _sub in ("bootstrap", "scripts"):
    if str(_REPO / _sub) not in sys.path:
        sys.path.insert(0, str(_REPO / _sub))

import bootstrap_templates as bt  # noqa: E402

CROSSCUTTING_SCOPE = ["bootstrap/"]

#: Emphasis that literal models spiral on, and the softer forms that carry the same
#: imperative. `Never`/`Always` are listed with an initial capital because that is
#: how they appear at the head of a rule; the lowercase words inside prose are
#: ordinary English and are not the subject.
_EMPHASIS = re.compile(
    r"\b(MUST|NEVER|ALWAYS|IMPORTANT|DO NOT|Always|Never|non-negotiable|strictly)\b"
)

#: Asking the model to spend less. Checked over the whole body, because the trap is
#: easy to step into anywhere and its cost lands on ambitious tasks.
_THRIFT = (
    "save tokens",
    "conserve token",
    "fewer comments",
    "be concise",
    "be brief",
    "minimise output",
    "minimize output",
    "keep it short",
    "as few as possible",
    "не трать токен",
    "экономь",
    "меньше комментариев",
)


@pytest.fixture(scope="module")
def body() -> str:
    """The standard-tier body, through the real assembler."""
    return bt.build_full_body("proj", ["python"], "Claude", ".claude", context_tier="standard")


class TestNoEmphasisSurvives:
    def test_the_body_carries_no_emphasis_marker(self, body):
        offenders = sorted({m.group(0) for m in _EMPHASIS.finditer(body)})
        assert not offenders, (
            f"emphasis returned: {offenders}. Literal model families spiral on it, "
            "and it says nothing a description cannot."
        )

    def test_the_detector_would_catch_a_relapse(self):
        """Zero means nothing unless the check can refuse."""
        assert _EMPHASIS.search("You MUST do this")
        assert _EMPHASIS.search("Always confirm first")
        assert _EMPHASIS.search("these are non-negotiable")

    def test_ordinary_lowercase_prose_is_not_the_subject(self):
        """A rule against the word `never` in any position would forbid English."""
        assert not _EMPHASIS.search("a gate never crashes the commit it guards")
        assert not _EMPHASIS.search("this must hold for every host")


class TestNothingAsksTheModelToSpendLess:
    """The half with the higher cost: it is paid on the tasks worth doing."""

    @pytest.mark.parametrize("plea", _THRIFT)
    def test_no_thrift_request_anywhere_in_the_body(self, body, plea):
        """Одной проверкой на всё тело, а не отдельно по константам: тело уже
        включает жёсткие правила, и вторая проверка того же текста покрывала бы
        один путь дважды."""
        assert plea not in body.lower()
        assert plea not in bt.HARD_CONSTRAINTS.lower()


class TestTheRulesThemselvesSurvivedTheEdit:
    """Tone was the subject; the rules were not. A quieter file that lost a rule
    would be a worse file."""

    @pytest.mark.parametrize(
        "phrase",
        [
            pytest.param("No code without a task", id="rule_1"),
            pytest.param("QG-0 Context Gate", id="qg0"),
            pytest.param("QG-2 Implementation Gate", id="qg2"),
            pytest.param("No direct DB access", id="db"),
            pytest.param("Git: ask before commit/push", id="git"),
            pytest.param("Max 500 lines per file", id="filesize"),
            pytest.param("Code is written in English", id="code_style"),
        ],
    )
    def test_the_rule_is_still_stated(self, body, phrase):
        assert phrase in body

    @pytest.mark.parametrize(
        ("phrase", "why"),
        [
            pytest.param(
                "audit trail",
                "the DB imperative was replaced by its consequence, not dropped",
                id="db_rule_says_why",
            ),
            pytest.param(
                "Use user's language.",
                "deleting it would have been one line cheaper and wrong: that a model "
                "defaults to the user's language cannot be shown from here",
                id="response_language_kept_as_a_statement",
            ),
        ],
    )
    def test_the_rewrite_kept_what_mattered(self, body, phrase, why):
        assert phrase in body, why


class TestTheBodyStaysWithinItsBudget:
    def test_it_does_not_bloat_inside_a_line(self, body):
        """The tone edit took 15,013 characters to 14,998 — quieter and no longer.
        The number was then re-based to 15228 when the compaction contract gained its
        seventh item, which was paid for in LINES (the file sits at 180 of its
        180-line budget) rather than in characters.

        A third re-base was ATTEMPTED and abandoned, and the attempt is worth more
        than the line would have been: "no code without a need" was written into the
        hard constraints, and `test_line_count_in_range` refused it because the file
        already sits at its 180-line ceiling. A new rule is now a TRADE against an
        existing one, not an addition. The ordering it carried reaches the agent from
        the task-start prompt instead (scripts/code_necessity.py).

        A FIFTH re-base, to 15431, carries decision #404: the owner's instruction that code
        and comments are written in English. The rule it replaced said the opposite in as many
        words -- docstrings and comments could take any language -- so this was a CORRECTION of
        a shipped rule rather than an addition, and it cost 203 characters to say the three
        things it now says: the identifier half, the prose half, and the boundary that keeps
        the rule off the user's reply.

        A FOURTH re-base, to 15228, was TAKEN rather than refused, and the reason is
        the difference: the owner ordered the answer shape into the shipped rules, so
        the rule was not optional and the question was only what it displaced. It was
        paid for first — the three workflow bullets that restated what each skill does,
        the model-selection paragraph that `task start` already prints, the code fence
        around the one-line pipeline, and the `## Response Language` section whose one
        sentence became a bullet of the shape. That covered 700 of the 750 characters;
        the remaining 50 moved the ceiling. The contract itself ships WHOLE: a first
        pass compressed it and silently dropped three of its elements, which
        `test_response_contract_shape` caught.

        So this is the weaker of two guards and says so: the 180-line budget in
        test_bootstrap_generate is the binding one, and this one only catches text
        growing inside lines the line count cannot see. Each re-base names what was
        bought, because a budget raised without a reason is not a budget.
        """
        assert len(body) <= 15431

    def test_it_is_still_within_the_line_budget(self, body):
        """The same 80-180 bound `test_bootstrap_generate` holds the file to."""
        assert 80 <= len(body.splitlines()) <= 180
