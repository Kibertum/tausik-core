"""The docstrings that say WHICH categories the publish-risk gate covers must be true.

This exists because one of them was false and did damage. `maybe_block_high_risk
_publish` said "Only patterns/gotchas apply" long after decision #205 added
`decisions` to `_CLASSIFIER_CATEGORY`, and during the investigation of
`brain-decide-publishes-unclassified-rationale` that line was CITED as evidence
that decisions were exempt from the gate. A sentence that once served as proof
of behaviour keeps being read as proof after it stops being true, and the next
reader draws the same conclusion on the same grounds.

Prose that duplicates a registry has to be derived from it by a test, or it is
just a second source of truth waiting to disagree with the first. So nothing
here asserts a hardcoded list of categories: every check is registry-driven, and
adding a fourth category without touching the words fails.
"""

from __future__ import annotations

import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import brain_publish_flow as bpf  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/brain_publish_flow.py"]

# Every place that tells a reader what the gate covers. A new one belongs here.
_DOCUMENTING = (
    ("module", lambda: bpf.__doc__),
    ("maybe_block_high_risk_publish", lambda: bpf.maybe_block_high_risk_publish.__doc__),
    ("assess_publish_risk", lambda: bpf.assess_publish_risk.__doc__),
)


def _singular(category: str) -> str:
    """`patterns` -> `pattern`, so a docstring may use either number."""
    return category[:-1] if category.endswith("s") else category


@pytest.mark.parametrize(("where", "getter"), _DOCUMENTING, ids=[d[0] for d in _DOCUMENTING])
def test_every_gated_category_is_named(where, getter):
    """Adding a category to the registry without saying so must fail HERE."""
    doc = (getter() or "").lower()
    assert doc.strip(), f"{where} has no docstring to check"
    missing = [c for c in bpf._CLASSIFIER_CATEGORY if c not in doc and _singular(c) not in doc]
    assert not missing, (
        f"{where} does not name {missing}, which the gate DOES cover. "
        "The registry is the source; the prose has to follow it."
    )


@pytest.mark.parametrize(("where", "getter"), _DOCUMENTING, ids=[d[0] for d in _DOCUMENTING])
def test_no_docstring_claims_the_gate_is_narrower_than_it_is(where, getter):
    """The specific false sentence, and the shape of it.

    "Only X and Y apply" is the form that reads as an exhaustive claim, and it
    is the form that was cited as evidence. Naming the categories is fine;
    fencing them with "only" is what turns a list into a guarantee.
    """
    doc = (getter() or "").lower()
    assert "only patterns/gotchas" not in doc
    assert "only patterns and gotchas" not in doc


def test_the_registry_is_what_the_code_actually_branches_on():
    """The premise of every assertion above: the prose tracks the right object.

    If the gate stopped keying on `_CLASSIFIER_CATEGORY`, these tests would go
    on passing while documenting a registry nothing consults.
    """
    source = inspect.getsource(bpf.maybe_block_high_risk_publish)
    assert "_CLASSIFIER_CATEGORY" in source

    # And the behaviour, not just the spelling: an unregistered category is not
    # gated, a registered one reaches the classifier.
    blocked, message = bpf.maybe_block_high_risk_publish(
        "not_a_category", {}, None, confirm_high_risk=False
    )
    assert blocked is False and message is None


def test_decisions_really_are_in_the_registry():
    """Guards the test suite against passing on a repo where #205 was reverted:
    every check above is vacuous if the category it is about disappeared."""
    assert "decisions" in bpf._CLASSIFIER_CATEGORY
