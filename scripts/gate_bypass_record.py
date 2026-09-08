"""A direct edit of a task artifact is a RECORDED gate bypass (SENAR 1.4 §8.6(j)).

Editing a task's artifact by a route no gate stands in front of — including a
direct edit by the supervisor — admits the effect QG-0 declared without a
positive verdict. §8.6(h) already classifies that as a bypass regardless of
intent. The standard does NOT forbid it: it is a REGULATED EXCEPTION, and the
legitimate cases stay open (an incident while agent capacity is unavailable, an
environment where the agent does not run). What it requires is a record.

NO NEW ENTITY. The standard is explicit that the record rides the Gate Bypass
(3.13) we already have, and we already have the machinery: `hook_supervision`
writes one `events` row per bypass and the metrics aggregate by action. What was
missing, measured before anything was changed:

* the §8.6(j) VECTOR — the seven existing ones all describe supervision being
  switched OFF, not an edit made around it;
* the four fields 3.13 requires — rationale, risk acceptance, remediation plan,
  senior approval — which had nowhere to live but one free-text `details`, where
  they can be neither required, nor told apart from prose, nor counted.

So the fields are encoded INTO that one field as JSON, which makes the record a
superset of what was there: an old row still reads, and a new one can be counted.

THREE STATES, NOT TWO. A record is `complete` (every field present), `incomplete`
(structured but missing something), or `unstructured` (free text, the shape every
row written before this existed). Collapsing the last two would either accuse
every historical row of being incomplete or quietly count it as complete; both
are claims the data does not support.

THE BOUNDARY IS THE TASK ARTIFACT. An exercise outside a task is not a bypass —
there is no declared effect to admit. Work that was handed in IS one. Get this
wrong in the widening direction and the mechanism starts calling everything a
bypass, which is how a mechanism gets switched off.
"""

from __future__ import annotations

import json
from typing import Any

#: The §8.6(j) vector, joining the seven that already exist. Named here so the
#: metrics can single it out: bypass frequency (§8.6(i)) and metric 8 are NESTED
#: figures, and the standard says in as many words that they SHALL NOT be added.
DIRECT_EDIT_VECTOR = "direct_edit"

#: What Gate Bypass (3.13) requires of every record. Order is the order a person
#: answers them in: why, what could go wrong, how it gets undone, who agreed.
BYPASS_FIELDS: tuple[str, ...] = (
    "rationale",
    "risk_accepted",
    "remediation",
    "approved_by",
)

#: The one field without which a record says nothing at all. A bypass with no
#: reason is the form filled in without looking that AC6 exists to prevent.
REQUIRED_FIELD = "rationale"

COMPLETE = "complete"
INCOMPLETE = "incomplete"
UNSTRUCTURED = "unstructured"


class BypassRecordRefused(ValueError):
    """The record was rejected. Never raised for an edit — only for a RECORD."""


def encode(fields: dict[str, str]) -> str:
    """The four fields as the `details` of one supervision row."""
    return json.dumps(
        {k: v for k, v in fields.items() if k in BYPASS_FIELDS and str(v).strip()},
        ensure_ascii=False,
        sort_keys=True,
    )


def decode(details: str | None) -> dict[str, str] | None:
    """The structured record, or None when the row carries free text.

    None is the honest answer for every row written before this existed: it says
    "not structured", which is different from "structured and missing fields".
    """
    if not details:
        return None
    try:
        parsed = json.loads(details)
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    known = {k: str(v) for k, v in parsed.items() if k in BYPASS_FIELDS}
    return known or None


def completeness(details: str | None) -> str:
    """`complete`, `incomplete` or `unstructured` — see the module docstring."""
    record = decode(details)
    if record is None:
        return UNSTRUCTURED
    missing = [f for f in BYPASS_FIELDS if not record.get(f, "").strip()]
    return INCOMPLETE if missing else COMPLETE


def missing_fields(details: str | None) -> list[str]:
    """Which of the four are absent. Empty for a complete record."""
    record = decode(details) or {}
    return [f for f in BYPASS_FIELDS if not record.get(f, "").strip()]


def build(task_slug: str | None, **fields: str) -> str:
    """Validate and encode a §8.6(j) record. Raises rather than writing a stub.

    `task_slug` is the boundary: with no task there is no declared effect to
    admit, so there is nothing to record and the caller is told so instead of
    being handed a row that would inflate the count.
    """
    if not (task_slug or "").strip():
        raise BypassRecordRefused(
            "a direct edit is a bypass of a TASK's gates (§8.6(j)); with no task "
            "there is no declared effect to admit, so there is nothing to record"
        )
    if not str(fields.get(REQUIRED_FIELD, "")).strip():
        raise BypassRecordRefused(
            f"a bypass record needs a {REQUIRED_FIELD}: Gate Bypass (3.13) is a "
            "regulated exception, and a record without a reason is the form "
            "filled in without looking. Legitimate cases exist — an incident "
            "while agent capacity is unavailable, an environment where the agent "
            "does not run — and naming one takes a sentence."
        )
    return encode(fields)


def split_nested(summary: dict[str, Any]) -> dict[str, Any]:
    """Separate metric 8 from the bypass frequency it sits INSIDE.

    §8.6(i) frequency counts every bypass; metric 8 counts the manual
    interventions among them. The standard says SHALL NOT add them, and the
    reason is practical: summed, the threshold fires on a team doing nothing
    wrong. Returned as one dict that names the containment instead of leaving
    two numbers side by side for a reader to add.
    """
    by_action = dict(summary.get("by_action") or {})
    total = int(summary.get("total") or 0)
    manual = int(by_action.get(f"bypass_{DIRECT_EDIT_VECTOR}", 0))
    return {
        "total": total,
        "manual_intervention": manual,
        "other": total - manual,
        "nested": True,
        "by_action": by_action,
    }
