"""The response contract lives in ONE place now, and this holds it complete.

`ANSWER_SHAPE` (bootstrap/bootstrap_templates.py) is what every generated rules file
carries, whatever `output_mode` says. It used to have a twin: a vendored
`i-have-adhd` SKILL.md carrying the same contract as a skill the user could invoke, and
this file was a PARITY test against drift between the two. The vendored copy is gone —
its ideas are restated in the directive as ours, and a skill nobody invoked was never
the discipline it looked like. So the subject changed from "the two agree" to "the one
is complete": every part of the shape, every exception and every pre-send deletion has
to be named here, because there is no second document to lose it from.

IT USED TO READ `CAVEMAN_DIRECTIVE`, and that made every assertion here
conditional on a mode that is off by default: with `output_mode: off` the file
proved the contract of a block nobody was shipped. Measured while it read that
way — median final answer 522 words against a budget of 200, worse than the 396
measured before the contract existed at all. The contract moved to the block that
always ships; the parity check follows it.
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
    ANSWER_SHAPE,
    ANSWER_SHAPE_MAX_CHARS,
    build_full_body,
)

CROSSCUTTING_SCOPE = ["bootstrap/"]

# ONE DOCUMENT NOW. This was a PARITY test: the same contract lived in the always-
# shipped directive and in a vendored `i-have-adhd` SKILL.md, and two copies drift.
# The vendored copy is gone — its ideas are restated in the directive as ours — so
# parity has no second side. What survives is the table: every term the contract
# names has to be IN the directive, because the directive is now the only place a
# term can be lost from.
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


@pytest.fixture(scope="module")
def directive() -> str:
    return ANSWER_SHAPE


# --- every term of the contract, in the one place that carries it ----------------


@pytest.mark.parametrize(
    ("family", "name", "rx"), NAMED_TERMS, ids=[f"{f}:{n}" for f, n, _ in NAMED_TERMS]
)
def test_the_directive_carries_the_named_term(family, name, rx, directive):
    """Four shape parts, five exceptions, four pre-send deletions and the
    first/last-line frame. Each is named in the block that ships every session —
    there is no second document to carry it if this one drops it."""
    pattern = re.compile(rx, re.I | re.S)
    assert pattern.search(directive), f"directive lost {family} {name!r}"


def test_the_shape_keeps_its_order(directive):
    """done → verified by → left → your call: the order IS the contract, and a
    reshuffle is a different contract wearing the same words."""
    positions = [re.search(SHAPE_PARTS[p], directive, re.I).start() for p in SHAPE_PARTS]
    assert positions == sorted(positions), f"shape order is {positions}"


def test_exactly_five_exceptions_in_the_shape(directive):
    """Named, not judged: the list is closed. A sixth exception is a decision,
    not an edit; a fourth is a lost exception."""
    line = [ln for ln in directive.splitlines() if ln.startswith("- EXCEPTIONS")]
    assert len(line) == 1, directive
    block = directive.split("- EXCEPTIONS", 1)[1].split("\n- ", 1)[0]
    assert block.count(";") == 4, block


# --- one lever, not two ---------------------------------------------------------


def test_the_contract_ships_with_the_mode_off():
    """The point of the split: an agent gets the contract without opting into anything.

    `output_mode: caveman` still exists and still compresses prose; what it no longer owns
    is the shape, the record's protection and the exceptions, because those are not an
    economy measure.
    """
    body = build_full_body(
        project_name="p",
        stacks=["python"],
        agent_name="Claude",
        ide_subdir=".claude",
        ide="claude",
        output_mode="off",
    )
    assert "## Answer shape" in body
    assert "done → verified by → left → your call" in body


def test_the_ceiling_is_the_measured_size_not_a_round_number():
    """The block is paid for on every session, so its ceiling is where it actually sits.

    A ceiling with headroom is an invitation; this one has to be re-based deliberately,
    which is the moment somebody asks whether the new line earns its place.
    """
    assert len(ANSWER_SHAPE) == ANSWER_SHAPE_MAX_CHARS, (
        len(ANSWER_SHAPE),
        ANSWER_SHAPE_MAX_CHARS,
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


def test_a_directive_missing_a_shape_part_is_caught(directive):
    """The detector must be able to SEE. With one document left, a table that matched
    anything would pass for ever while the contract quietly emptied — so a directive
    with a part cut out has to fail the same table."""
    stripped = directive.replace("verified by", "").replace("your call", "")
    assert not re.search(SHAPE_PARTS["verified by"], stripped), "the negative is not a negative"
    assert not re.search(SHAPE_PARTS["your call"], stripped)


def test_the_vendored_twin_is_gone_and_stays_gone(directive):
    """It was carried under someone else's licence, had to be kept in sync, and gave no
    discipline because a skill is invoked and nobody invoked it. Its return would bring
    all three back."""
    assert (
        not (_ROOT / "harness" / "skills" / "i-have-adhd").exists()
        if hasattr(_ROOT, "exists")
        else not os.path.isdir(os.path.join(_ROOT, "harness", "skills", "i-have-adhd"))
    )
    for rx in EXCEPTIONS.values():
        assert re.search(rx, directive, re.I), "the exceptions survived the removal"
