"""SENAR Rule 4 External Validation — one model family per environment (1.11.6).

Rule 4 (Separation of Duties) demands that an under-evidenced closure be
reviewed by an EXTERNAL reviewer: a fresh, isolated context with no write
access. Since 1.11.6 the reviewer runs on the SAME model family as the author
— the host's own model. Pulling another family for the adversarial pass
(Codex from a GLM host, Claude from Codex) is prohibited; the separation is
the isolated read-only context, not the model. The two halves are enforced in
different places:

  - **No write access** — the named `tausik-external-reviewer` subagent ships
    with a read-only tool allowlist (Read/Grep; no Write/Edit). The
    harness, not this module, enforces it.
  - **Same family** — this module. Given the author's model it names the
    reviewer the host already runs, so the delegation hint can never direct
    the caller to another family.

Wired into risk_l3_trigger: when a measured-high closure escalates to L3, the
remediation names the subagent and the author's exact model id.
"""

from __future__ import annotations

from model_routing import _model_family

import model_profiles
from review_separation import vendor_family

_DISPLAY = {"haiku": "Haiku", "sonnet": "Sonnet", "opus": "Opus", "fable": "Fable"}


def recommend_reviewer_model(author_model: str | None) -> str:
    """The reviewer for an L3 pass: the author's own family — never another.

    One family per environment (1.11.6): the recommendation is the model this
    host already runs. A Claude tier maps to itself; a released GPT/GLM id maps
    to its normalized id. An unrecognized author yields a named placeholder —
    the hint then tells the caller to pass --author-model rather than guess a
    family that may not be the host's.
    """
    tier = _model_family(author_model)
    if tier is not None:
        return tier
    if vendor_family(author_model) is not None:
        return model_profiles.normalize_model_id(author_model)
    return "the model this host already runs"


def is_separate_duty(author_model: str | None, reviewer_model: str | None) -> bool:
    """True only when the reviewer is a recognised model of the author's family.

    1.11.6: separation is the isolated context; the reviewer's family must be
    the SAME as the author's — pulling another family is prohibited. An
    unrecognised reviewer still returns False: a record that cannot name a
    real reviewer cannot claim the external pass happened, so the caller
    should warn rather than trust it.
    """
    reviewer_vendor = vendor_family(reviewer_model)
    if reviewer_vendor is None:
        return False
    return reviewer_vendor == vendor_family(author_model)


def reviewer_hint(author_model: str | None) -> str:
    """One-line one-family delegation hint naming the subagent and models."""
    reviewer = recommend_reviewer_model(author_model)
    display = _DISPLAY.get(reviewer, reviewer)
    # github#157: the invitation carries the author's exact id, so the reviewer
    # records it instead of reconstructing it from commit trailers.
    author_id = author_model or "unknown — pass --author-model"
    return (
        f"Delegate to the @tausik-external-reviewer subagent on {display} — the "
        f"SAME model family as the author (one family per environment, 1.11.6); "
        f"SENAR Rule 4 separation of duties holds by the isolated read-only "
        f"context, and pulling another model family is prohibited. "
        f"Author model: {author_id}. Record with "
        f"--author-model and --reviewer-model: a cross-family L3 is refused."
    )
