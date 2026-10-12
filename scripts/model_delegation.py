"""When the cheap model should do the work: delegation, because switching is not available.

THE MEASUREMENT. Of 218 closed tasks carrying a model id, 195 ran on the premium tier —
including 47 rated `simple` and 90 rated `medium`, where the recommendation was a cheaper
model. The recommendation prints at every `task start` and is followed almost never, which is
this project's own definition of a rule that is switched off.

WHY IT STAYED ADVICE, and the constraint is real: the host does not switch models
programmatically, so `task start` can only ask. Decision #183 settled that the adherence
metric is CALIBRATION, not compliance, exactly for that reason — a recommendation that differs
from the running model was nobody's violation.

WHAT CHANGES THE PREMISE: a SUBAGENT is started with a model chosen by the caller. That is a
programmatic choice, and it moves both multipliers of the price at once —

* the cheaper tier costs less per token, and
* a subagent begins with a FRESH context, while the session that spawned it is carrying
  half a million tokens of history re-sent on every one of its own calls.

The second is the larger and the one nobody counts. Measured on this project: the median call
sits at roughly 500,000 tokens of re-sent prefix against about 42,000 at a session's start.

WHAT IS NOT DELEGATED. The closure. Verification, the evidence and `task done` stay with the
agent that owns the task — a receipt signed by a worker nobody reviewed is the failure QG-2
exists to prevent. The subagent does the work and reports; the owner checks and closes.
"""

from __future__ import annotations

from typing import Final, NamedTuple

#: Tiers that may be handed to a cheaper model. `complex` never is: the recommendation there
#: points UP, and delegating it would buy tokens with the thing the project sells.
DELEGATABLE: Final[frozenset[str]] = frozenset({"simple"})

#: Measured starting context of a session against the median call, both on this project. The
#: ratio is the part of delegation nobody counts — the model tier is the visible saving.
FRESH_CONTEXT_TOKENS: Final[int] = 42_000
CARRIED_CONTEXT_TOKENS: Final[int] = 500_000


class Advice(NamedTuple):
    """``delegate`` is the verdict; ``reason`` says why, in one line, for a human."""

    delegate: bool
    model: str | None
    reason: str


def context_multiple() -> int:
    """How many times more prefix a carried session re-sends than a fresh subagent."""
    return max(1, round(CARRIED_CONTEXT_TOKENS / FRESH_CONTEXT_TOKENS))


def advise(
    complexity: str | None,
    recommended_model: str | None,
    active_tier: int | None = None,
    recommended_tier: int | None = None,
) -> Advice:
    """Should this task be handed to a subagent on the recommended model?

    Only when the tier says the work is simple AND the session is running something more
    expensive than the work needs. Both halves matter: delegating while already on the
    recommended model buys nothing but a round-trip, and delegating complex work buys tokens
    at the cost of the result.
    """
    tier = (complexity or "").strip().lower()
    if tier not in DELEGATABLE:
        return Advice(
            False,
            None,
            f"complexity '{tier or 'unset'}' is not delegated — the recommendation for it "
            "does not point at a cheaper model",
        )
    if not recommended_model:
        return Advice(False, None, "no recommended model to delegate to")
    if active_tier is not None and recommended_tier is not None and active_tier <= recommended_tier:
        return Advice(
            False,
            recommended_model,
            "already at or below the recommended tier — delegating would buy a round-trip "
            "and nothing else",
        )
    return Advice(
        True,
        recommended_model,
        f"simple work on a premium session: hand it to a subagent on {recommended_model}. "
        f"It also starts with a FRESH context — this session re-sends about "
        f"{context_multiple()}x more prefix on every call. The closure stays here: "
        f"verification, evidence and `task done` are not delegated.",
    )


def banner_line(advice: Advice) -> str | None:
    """One line for `task start`, or None when there is nothing to say."""
    if not advice.delegate:
        return None
    return f"  ↪ DELEGATE: {advice.reason}"
