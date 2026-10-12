"""WHO did the work, as content of a signed receipt rather than an assertion.

THE GAP, MEASURED (session #239). A verify receipt is signed with the PROJECT
key from `.tausik/keys/project.pub`. It answers "which gates passed on which
state of the code" and says nothing about who ran them. Meanwhile the whole
quality story rests on separation of duties: an external reviewer on a DIFFERENT
model, and with P8 also "the test author is not the implementer". All of it was
ASSERTED and none of it attestable — one signature, one project.

WHAT THE NUMBERS SAID, and they are harder than the filing was. Across 1,686
receipts not one carries any actor field. Of 1,574 tasks, `claimed_by` is NULL
in every single one. Only 29 tasks record both a starting and a closing model,
and in NONE of them do the two differ. So on the verify path separation of
duties does not merely lack attestation — it does not happen, and the mechanism
below has to SHOW that rather than paint over it.

WHAT THIS RECORDS AND WHAT IT DOES NOT, said here because the difference is the
whole discipline. The receipt records the actor OF THE VERIFICATION RUN. It does
NOT say who wrote the test and who wrote the code — that is P8's subject and it
is out of scope. Offering this field as evidence for that claim would be
presenting a checkable thing in place of an unchecked one, which is precisely
the class this release exists to remove.

NO IDENTITY REGISTRY AND NO CERTIFICATE AUTHORITY. The filing forbids both, and
the design honours it structurally rather than by intent: the actor is CONTENT
of the project-signed receipt, not a second signer. A second key would mean
managing per-agent key material, which is the thing that was ruled out.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "DIFFERENT",
    "SAME",
    "UNKNOWN",
    "actor_of",
    "build_actor",
    "compare",
]

#: Three outcomes, never two. A receipt carrying no actor is not a receipt by a
#: different actor, and collapsing the two would report absence of data as proof
#: of separation — the exact inversion this module exists to prevent.
SAME = "same"
DIFFERENT = "different"
UNKNOWN = "unknown"

#: The key the receipt stores the actor under.
FIELD = "actor"


def build_actor(
    *,
    session_id: int | str | None = None,
    model_id: str | None = None,
    model_version: str | None = None,
    role: str | None = None,
) -> dict[str, Any] | None:
    """The actor block, or None when nothing is known.

    None rather than a dict of nulls: `missing_v3_fields` already taught this
    codebase that presence must be judged by VALUE, and a block of empty fields
    reads as "an actor was recorded" to every check that looks for the key.
    """
    block = {
        "session_id": str(session_id) if session_id is not None else None,
        "model_id": model_id or None,
        "model_version": model_version or None,
        "role": role or None,
    }
    if not any(block.values()):
        return None
    return block


def actor_of(receipt: dict[str, Any] | None) -> dict[str, Any] | None:
    """The actor block of a receipt, or None for one that carries none.

    A v3 receipt is not malformed for lacking it — 1,686 of them exist and stay
    valid. It simply cannot answer the question.
    """
    if not isinstance(receipt, dict):
        return None
    block = receipt.get(FIELD)
    return block if isinstance(block, dict) and any(block.values()) else None


def _identity(block: dict[str, Any]) -> tuple[str, str, str]:
    """What makes two actors the same one.

    The SESSION is the identity, and the model is part of it: the same session
    cannot be two actors, and the same model in two sessions is two runs by
    agents that could have differed in everything a run can differ in. The role
    is deliberately NOT part of the identity — one agent changing hats is still
    one agent, and treating a role change as a different actor is how a
    separation of duties gets claimed without one.
    """
    return (
        str(block.get("session_id") or ""),
        str(block.get("model_id") or ""),
        str(block.get("model_version") or ""),
    )


def compare(left: dict[str, Any] | None, right: dict[str, Any] | None) -> str:
    """SAME | DIFFERENT | UNKNOWN for two receipts.

    UNKNOWN whenever either side carries no actor, and that is the common case
    today by construction: every receipt written before this schema has none.
    A caller that wants "separation held" must require DIFFERENT explicitly —
    `!= SAME` would count every legacy receipt as separated.
    """
    a, b = actor_of(left), actor_of(right)
    if a is None or b is None:
        return UNKNOWN
    return SAME if _identity(a) == _identity(b) else DIFFERENT
