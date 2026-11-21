"""Record a review_infrastructure_blocked receipt without burning an L3 round.

TB-009: when the host cannot mechanically provide a read-only file review,
the operator must not spend one of the two defect-repair rounds on that fact.
This receipt is durable evidence; ``current_round`` and cohort ``state`` stay
where they were.
"""

from __future__ import annotations

import json
from typing import Any

from review_l3_preflight import RECEIPT_KIND, L3Capability, load_preflight


def _now() -> str:
    from tausik_utils import utcnow_iso

    return utcnow_iso()


def record_infrastructure_blocked(
    svc: Any,
    cohort_id: int,
    *,
    round_number: int,
    packet_digest: str,
    reason: str,
    code: str,
    detail: str | None = None,
) -> dict[str, Any]:
    """Persist an infrastructure refusal for the intended round; do not advance it."""
    if round_number not in (1, 2):
        raise ValueError("round must be 1 or 2")
    reason = (reason or "").strip()
    code = (code or "").strip()
    if not reason or not code:
        raise ValueError("reason and code must be non-empty")
    packet_digest = (packet_digest or "").strip()
    if not packet_digest:
        raise ValueError("packet_digest must be non-empty")

    from review_cohort import _cohort

    cohort = _cohort(svc.be, cohort_id)
    state = str(cohort["state"])
    current = int(cohort["current_round"] or 0)
    if round_number != current + 1:
        raise ValueError(
            f"infrastructure-blocked expects round {current + 1} "
            f"(current_round={current}); got {round_number}"
        )
    if round_number == 1 and state != "open":
        raise ValueError(f"round 1 infrastructure receipt requires state=open, got {state}")
    if round_number == 2 and state != "round1_red":
        raise ValueError(f"round 2 infrastructure receipt requires state=round1_red, got {state}")

    from review_cohort import _round2_members, cohort_status

    # Same packet the operator already holds from open/status — do not invent another.
    status = cohort_status(svc, cohort_id, issue_packet=True)
    packet = status.get("packet")
    if not isinstance(packet, dict) or packet.get("round") != round_number:
        raise ValueError("no issued packet for this round — run cohort-status first")
    if packet.get("packet_digest") != packet_digest:
        raise ValueError(
            "packet_digest does not match the issued packet — "
            "present the digest from cohort-open/status"
        )
    members = list(status.get("members") or json.loads(cohort["members_json"]))
    if round_number == 2:
        required, _carried = _round2_members(svc, cohort)
        members = required

    stamp = _now()
    with svc.be.transaction():
        # Re-read under the write lock: a concurrent record must not race us.
        live = _cohort(svc.be, cohort_id)
        if int(live["current_round"] or 0) != current or str(live["state"]) != state:
            raise ValueError("cohort state changed while recording infrastructure refusal")
        svc.be._conn.execute(
            "INSERT INTO review_cohort_infrastructure_events("
            "cohort_pk, round_number, receipt_kind, code, reason, detail, "
            "packet_digest, recorded_at) VALUES(?,?,?,?,?,?,?,?)",
            (
                int(cohort["id"]),
                round_number,
                RECEIPT_KIND,
                code,
                reason,
                detail,
                packet_digest,
                stamp,
            ),
        )
        # Explicitly do NOT update current_round / state — that is the whole point.

    return {
        "cohort_id": cohort_id,
        "state": state,
        "rounds": f"{current}/2",
        "receipt_kind": RECEIPT_KIND,
        "code": code,
        "reason": reason,
        "detail": detail,
        "round": round_number,
        "packet_digest": packet_digest,
        "budget_preserved": True,
        "members": members,
        "green": 0,
        "advisory": 0,
        "accepted_risk": 0,
        "red": 0,
        "carried": 0,
    }


def attach_preflight(out: dict[str, Any], capability: L3Capability | None = None) -> dict[str, Any]:
    """Add capability + delegation hints to an open/status payload."""
    cap = capability if capability is not None else load_preflight()
    out = dict(out)
    out["l3_capability"] = cap.as_dict()
    packet = out.get("packet")
    author = None
    if isinstance(packet, dict):
        tasks = packet.get("tasks") or []
        models = {
            str(t.get("author_model") or t.get("started_model_id") or "")
            for t in tasks
            if isinstance(t, dict)
        }
        models.discard("")
        if len(models) == 1:
            author = next(iter(models))
        elif models:
            author = "mixed — pass --author-model per record"
    from external_reviewer import reviewer_hint

    out["delegation"] = reviewer_hint(author)
    if cap.enforced and not cap.ok:
        out["next"] = (
            f"INFRASTRUCTURE blocked ({cap.code}): do NOT cohort-record a product "
            f"red/green. Record `{RECEIPT_KIND}` via "
            f"`review cohort-infrastructure-blocked` so round budget is preserved. "
            f"{cap.detail}"
        )
    return out


def refuse_record_if_blocked(svc: Any) -> None:
    """Raise when an enforced preflight says the host cannot review files."""
    cap = load_preflight()
    if cap.enforced and not cap.ok:
        raise ValueError(
            f"{RECEIPT_KIND}: {cap.code} — {cap.detail}. "
            "Do not consume a cohort round; use "
            "`tausik review cohort-infrastructure-blocked` instead."
        )
