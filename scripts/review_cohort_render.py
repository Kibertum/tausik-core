"""CLI/MCP text rendering for bounded L3 cohort responses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def cohort_summary(out: Mapping[str, Any]) -> str:
    """Compact shared CLI/MCP rendering: one denominator and one next action."""
    lines = [
        f"L3 cohort: {len(out.get('members') or [])} tasks · "
        f"green {out.get('green', 0)} · advisory {out.get('advisory', 0)} · "
        f"accepted-risk {out.get('accepted_risk', 0)} · red {out.get('red', 0)} · "
        f"carried {out.get('carried', 0)} · rounds {out.get('rounds', '0/2')}",
        f"Cohort #{out.get('cohort_id')} · state {out.get('state')}",
    ]
    if out.get("receipt_kind"):
        lines.append(
            f"Receipt: {out.get('receipt_kind')} ({out.get('code')}) — "
            f"budget preserved={out.get('budget_preserved')}"
        )
    if out.get("delegation"):
        lines.append(str(out["delegation"]))
    cap = out.get("l3_capability")
    if isinstance(cap, Mapping) and cap.get("enforced") and not cap.get("ok"):
        lines.append(f"L3 capability blocked: {cap.get('code')} — {cap.get('detail')}")
    if out.get("next"):
        lines.append(str(out["next"]))
    packet = out.get("packet")
    if isinstance(packet, Mapping) and not out.get("next"):
        lines.append(
            f"Next: run L3 round {packet.get('round')} for "
            + ", ".join(str(item.get("slug")) for item in packet.get("tasks") or [])
        )
    if out.get("owner_action"):
        lines.append("Owner action: " + str(out["owner_action"]) + ".")
    return "\n".join(lines)
