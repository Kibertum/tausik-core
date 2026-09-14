"""The response contract lives in two places and must say the same thing.

`CAVEMAN_DIRECTIVE` (bootstrap/bootstrap_templates.py) is what `output_mode:
caveman` writes into the rules file; `harness/skills/i-have-adhd/SKILL.md` is
the same contract as a skill the user turns on by hand. Each names the four
parts of the shape, the five exceptions and the four pre-send deletions. When
one of them is edited and the other is not, a fresh agent gets two contracts —
so this file fails on the first divergence rather than letting the two drift.
"""

from __future__ import annotations

import os
import re
import sys

import pytest

_ROOT = os.path.join(os.path.dirname(__file__), "..")
for _p in (os.path.join(_ROOT, "bootstrap"), os.path.join(_ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bootstrap_templates import (  # noqa: E402
    CAVEMAN_DIRECTIVE,
    CAVEMAN_DIRECTIVE_MAX_CHARS,
    build_full_body,
)

CROSSCUTTING_SCOPE = ["bootstrap/", "harness/skills/i-have-adhd/"]

SKILL_PATH = os.path.join(_ROOT, "harness", "skills", "i-have-adhd", "SKILL.md")

# Each family is a regex both documents must satisfy. The wording differs on
# purpose (telegraphic in the directive, prose in the skill); the NAME of every
# part does not.
SHAPE_PARTS = {
    "done": r"\bdone\b",
    "verified by": r"verified by",
    "left": r"\bleft\b",
    "your call": r"your call",
}
EXCEPTIONS = {
    "explanation requested": r"explanation",
    "destructive needs confirmation": r"destructive",
    "three failed debugging turns": r"three failed debugging turns",
    "genuine ambiguity": r"ambiguity",
    "rule would delete the answer": r"answer itself",
}
PRE_SEND_DELETIONS = {
    "intent announcement": r"announc",
    "closing recap": r"closing",
    "side branch": r"side ?(branch|bar)",
    "empty hedge": r"hedge",
}
PRE_SEND_FRAME = {
    "first line = next action": r"first.*next action|next action.*first",
    "last line = current state": r"last.*current state|current state.*last",
}

# Every term both documents must carry, as (family, name, regex): one claim,
# one test, one row per term — a fresh agent reads the failing id as
# `shape:verified by`, not as the third of four look-alike functions.
NAMED_TERMS = [
    (family, name, rx)
    for family, table in (
        ("shape", SHAPE_PARTS),
        ("exception", EXCEPTIONS),
        ("pre-send", PRE_SEND_DELETIONS),
        ("frame", PRE_SEND_FRAME),
    )
    for name, rx in table.items()
]


def _skill() -> str:
    with open(SKILL_PATH, encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def skill() -> str:
    return _skill()


@pytest.fixture(scope="module")
def directive() -> str:
    return CAVEMAN_DIRECTIVE


# --- the same contract in both places -----------------------------------------


@pytest.mark.parametrize(
    ("family", "name", "rx"), NAMED_TERMS, ids=[f"{f}:{n}" for f, n, _ in NAMED_TERMS]
)
def test_both_documents_carry_the_named_term(family, name, rx, directive, skill):
    """Four shape parts, five exceptions, four pre-send deletions and the
    first/last-line frame: each is named in the directive AND in the skill."""
    pattern = re.compile(rx, re.I | re.S)
    assert pattern.search(directive), f"directive lost {family} {name!r}"
    assert pattern.search(skill), f"SKILL.md lost {family} {name!r}"


def test_the_shape_keeps_its_order_in_both(directive, skill):
    """done → verified by → left → your call: the order is the contract, a
    reshuffle is a different contract."""
    for name, text in (("directive", directive), ("SKILL.md", skill)):
        # the skill's Shape section names the order once; the rules re-use the
        # words elsewhere, so measure inside the Shape paragraph only
        body = text.split("## Shape", 1)[1].split("## Rules", 1)[0] if name == "SKILL.md" else text
        positions = [re.search(SHAPE_PARTS[p], body, re.I).start() for p in SHAPE_PARTS]
        assert positions == sorted(positions), f"{name}: shape order is {positions}"


def test_exactly_five_exceptions_in_the_directive(directive):
    """Named, not judged: the list is closed. A sixth exception is a decision,
    not an edit; a fourth is a lost exception."""
    line = [ln for ln in directive.splitlines() if ln.startswith("- EXCEPTIONS")]
    assert len(line) == 1, directive
    block = directive.split("- EXCEPTIONS", 1)[1].split("\n- ", 1)[0]
    assert block.count(";") == 4, block


# --- one lever, not two ---------------------------------------------------------


def test_the_contract_rides_the_existing_directive_not_a_second_mode():
    """Same marker, same injection point, same config value: the shape costs
    zero new surface. A second `output_mode` value would be a second contract."""
    from bootstrap_config import OUTPUT_MODE_VALUES

    assert set(OUTPUT_MODE_VALUES) == {"off", "caveman"}
    assert CAVEMAN_DIRECTIVE.startswith("## Output economy (caveman mode)")
    body = build_full_body("proj", ["python"], "claude", ".claude", output_mode="caveman")
    assert body.count("## Output economy (caveman mode)") == 1
    assert "SHAPE" in body and "EXCEPTIONS" in body and "PRE-SEND" in body


def test_the_ceiling_moved_by_the_measured_amount_only():
    """888 is what the contract measures, not a round number with headroom:
    the ceiling is a guard against bloat, so headroom is exactly what it must
    not have."""
    assert len(CAVEMAN_DIRECTIVE) == CAVEMAN_DIRECTIVE_MAX_CHARS, (
        len(CAVEMAN_DIRECTIVE),
        CAVEMAN_DIRECTIVE_MAX_CHARS,
    )


def test_the_keep_lists_survived_the_rewrite(directive):
    """The two lists that predate the contract are what makes it safe to turn
    on: a shape that compressed code or AC evidence would be a regression."""
    for term in ("code", "shell commands", "tool output", "file paths", "error messages"):
        assert term in directive, term
    for term in (
        "acceptance-criteria evidence",
        "decisions",
        "SPEC/ADAPT",
        "task logs",
        "handoffs",
    ):
        assert term in directive, term


# --- negatives ------------------------------------------------------------------


def test_a_skill_without_the_shape_section_is_caught(tmp_path, monkeypatch):
    """The parity test must fail on the skill, not only on the directive: an
    edit that drops `## Shape` from SKILL.md is the drift this file exists for."""
    stripped = re.sub(r"## Shape.*?(?=## Rules)", "", _skill(), flags=re.S)
    assert not re.search(SHAPE_PARTS["verified by"], stripped), "the negative is not a negative"
    assert not re.search(SHAPE_PARTS["your call"], stripped)


def test_the_directive_names_no_exception_the_skill_lacks(directive, skill):
    """The exception list is copied by name; an exception that exists in only
    one place lets an agent argue from the other."""
    for exc, rx in EXCEPTIONS.items():
        assert bool(re.search(rx, directive, re.I)) == bool(re.search(rx, skill, re.I)), exc
