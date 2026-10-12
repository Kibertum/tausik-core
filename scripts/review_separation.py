"""SENAR Rule 4 on the RECORD, not only in the invitation (github#157).

l3-dispatch-does-not-carry-the-author-model (1.10). An L3 review record closed
the task's review gate on the reviewer's word alone: the invitation named the
author's family at best, and `review record` stored only free notes. A reviewer
that did not check would certify its own work. Now an L3 record names both
models and is refused when they are the same family, or when either cannot be
established — separation that cannot be shown is not assumed.

The models go into notes (`author_model=… reviewer_model=…`), not into new
columns: memory #136 keeps the reviews table as it is.
"""

from __future__ import annotations

import re

import model_profiles
from model_routing import _model_family


_OPENAI_MODEL = re.compile(r"^gpt-\d+(?:\.\d+)?(?:-(?:luna|terra|sol|astra))?$")
# Same shape for GLM generations: a released id carries its number, optionally
# one hyphenated variant word (glm-4.5-air). The registry's starter lineup
# cannot track every point release (glm-5.2 shipped after it), so an
# unrecognized-but-well-formed generation must not silently read as "unknown
# family" — that would refuse every honest review record on the host running it.
_GLM_MODEL = re.compile(r"^glm-\d+(?:\.\d+)?(?:-[a-z][a-z0-9-]*)?$")


def review_model_family(model_id: str | None) -> str | None:
    """Review-separation family across supported model providers.

    The historical Claude tier tokens remain stable. Known profile models use
    vendor plus abstract rank. A bare released GPT or GLM generation is
    recognized by its exact normalized id; invented values such as ``gpt-x``
    or ``glm-x`` remain unknown.
    """
    claude_tier = _model_family(model_id)
    if claude_tier is not None:
        return f"claude:{claude_tier}"
    normalized = model_profiles.normalize_model_id(model_id)
    hit = model_profiles.reverse_index(model_profiles.DEFAULT_FAMILIES).get(normalized)
    if hit is not None:
        return f"{hit[0]}:{hit[1]}"
    if _OPENAI_MODEL.fullmatch(normalized):
        return f"openai:{normalized}"
    if _GLM_MODEL.fullmatch(normalized):
        return f"glm:{normalized}"
    return None


def resolve_author_model(explicit: str | None) -> str | None:
    """The author's model: the flag, else the live transcript of the session
    that runs the command — the author's own session records the review."""
    if explicit:
        return explicit
    try:
        from risk_l3_trigger import _author_model

        return _author_model()
    except Exception:  # noqa: BLE001 — unknown author is refused by the caller
        return None


def l3_refusal(author_model: str | None, reviewer_model: str | None) -> str | None:
    """Why an L3 record must not be written, or None when separation is shown."""
    if not reviewer_model:
        return "L3 needs --reviewer-model: the model that ran the review (SENAR Rule 4)."
    if review_model_family(reviewer_model) is None:
        return (
            f"reviewer model {reviewer_model!r} is not a recognised model family: "
            "independence cannot be shown (SENAR Rule 4)."
        )
    if review_model_family(author_model) is None:
        return (
            "the author's model is unknown: pass --author-model <id> "
            "(the model that wrote the code; SENAR Rule 4)."
        )
    if review_model_family(author_model) == review_model_family(reviewer_model):
        return (
            f"reviewer {reviewer_model} and author {author_model} are the same family: "
            "a model cannot validate its own work (SENAR Rule 4). Re-run the review on "
            "a different model."
        )
    return None


def models_note(author_model: str, reviewer_model: str) -> str:
    return f"author_model={author_model} reviewer_model={reviewer_model}"
