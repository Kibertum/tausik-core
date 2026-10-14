"""SENAR Rule 4 on the RECORD, not only in the invitation (github#157).

l3-dispatch-does-not-carry-the-author-model (1.10). An L3 review record closed
the task's review gate on the reviewer's word alone: the invitation named the
author's family at best, and `review record` stored only free notes. A reviewer
that did not check would certify its own work. So the record names both models.

1.11.6 inverted the boundary this module enforces: ONE model family per
environment. Pulling another family for review — Codex from a GLM host, Claude
from Codex — is prohibited; the separation of duties is the isolated read-only
context, not the model. A record is therefore refused when the reviewer is
from ANOTHER family than the author. Same-family (including the author's own
model) is the recordable form; both ids stay on the record.

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


def vendor_family(model_id: str | None) -> str | None:
    """The one-family-per-environment family (1.11.6): vendor granularity.

    ``claude:opus`` and ``claude:sonnet`` are ONE family here, and so are
    ``glm-4.5`` and ``glm-5.2`` — "Claude host runs only Claude, Codex only
    GPT, z.ai only GLM". ``review_model_family`` stays id-granular because the
    record must still prove BOTH identities are real models; this coarse form
    is what the same-family rule compares.
    """
    if _model_family(model_id) is not None:
        return "claude"
    normalized = model_profiles.normalize_model_id(model_id)
    hit = model_profiles.reverse_index(model_profiles.DEFAULT_FAMILIES).get(normalized)
    if hit is not None:
        return hit[0]
    if _OPENAI_MODEL.fullmatch(normalized):
        return "openai"
    if _GLM_MODEL.fullmatch(normalized):
        return "glm"
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
    """Why an L3 record must not be written, or None when the rule is shown.

    1.11.6: one model family per environment. The refusal fires when the
    reviewer is from ANOTHER family than the author — pulling another family
    for review is prohibited — or when either model cannot be established.
    """
    if not reviewer_model:
        return "L3 needs --reviewer-model: the model that ran the review (SENAR Rule 4)."
    if review_model_family(reviewer_model) is None:
        return (
            f"reviewer model {reviewer_model!r} is not a recognised model family: "
            "the record must name a real reviewer (SENAR Rule 4)."
        )
    if review_model_family(author_model) is None:
        return (
            "the author's model is unknown: pass --author-model <id> "
            "(the model that wrote the code; SENAR Rule 4)."
        )
    if vendor_family(author_model) != vendor_family(reviewer_model):
        return (
            f"reviewer {reviewer_model} is from another model family than author "
            f"{author_model}: one model family per environment (1.11.6) — pulling "
            "another family for review is prohibited. Re-run the review on the "
            "author's own family in an isolated read-only context (SENAR Rule 4)."
        )
    return None


def models_note(author_model: str, reviewer_model: str) -> str:
    return f"author_model={author_model} reviewer_model={reviewer_model}"
