"""SENAR Rule 4 External Validation — pick a reviewer distinct from the author.

Rule 4 (Separation of Duties) demands that a high-risk closure be reviewed by
a model *different* from the one that wrote the code, and that the reviewer
SHALL NOT have write access. The two halves are enforced in different places:

  - **No write access** — the named `tausik-external-reviewer` subagent ships
    with a read-only tool allowlist (Read/Grep/Bash; no Write/Edit). The
    harness, not this module, enforces it.
  - **Different model** — this module. Given the author's model it recommends
    a reviewer *family* that is not the author's, so the adversarial pass is a
    genuine second opinion rather than the same model grading its own work.

Wired into risk_l3_trigger: when a measured-high closure escalates to L3, the
remediation names the subagent and the recommended reviewer model.
"""

from __future__ import annotations

from model_routing import _model_family

# Reviewer preference when we must pick a family different from the author.
# Opus first: the adversarial pass wants the strongest reasoning available;
# fable is reserved as the only fallback when the author is already on opus.
_REVIEWER_PREFERENCE = ("opus", "fable", "sonnet", "haiku")

_DISPLAY = {"haiku": "Haiku", "sonnet": "Sonnet", "opus": "Opus", "fable": "Fable"}


def recommend_reviewer_model(author_model: str | None) -> str:
    """Return a reviewer model *family* guaranteed distinct from the author's.

    Separation of duties: the result is never the author's own family. When
    the author family is unknown we still return the strongest reviewer
    (opus) — "unknown" cannot collide with a named family, so independence
    holds.
    """
    author = _model_family(author_model)
    for family in _REVIEWER_PREFERENCE:
        if family != author:
            return family
    return _REVIEWER_PREFERENCE[0]


def is_separate_duty(author_model: str | None, reviewer_model: str | None) -> bool:
    """True only when the reviewer is a recognised family unlike the author's.

    An unrecognised reviewer family returns False — we cannot prove the
    reviewer is independent, so the caller should warn rather than trust it.
    """
    reviewer = _model_family(reviewer_model)
    if reviewer is None:
        return False
    return reviewer != _model_family(author_model)


def reviewer_hint(author_model: str | None) -> str:
    """One-line separation-of-duties hint naming the subagent and model."""
    family = recommend_reviewer_model(author_model)
    display = _DISPLAY.get(family, family)
    author_family = _model_family(author_model)
    author_disp = (
        _DISPLAY.get(author_family, "the author model") if author_family else "the author model"
    )
    return (
        f"Delegate to the @tausik-external-reviewer subagent on {display} "
        f"(a different model than {author_disp} — SENAR Rule 4 separation of "
        f"duties; the reviewer is read-only)."
    )
