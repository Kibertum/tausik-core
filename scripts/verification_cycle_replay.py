"""Deterministic equivalence check for a frozen adjacent verification replay."""

from __future__ import annotations

from typing import Any


def _same_observation(left: dict[str, Any], right: dict[str, Any]) -> bool:
    fields = ("verdict", "counts", "failures", "evidence")
    return all(left.get(field) == right.get(field) for field in fields)


def evaluate_replay(replay: dict[str, Any]) -> dict[str, Any]:
    """Return whether one compound model return preserves the complete pair.

    The evaluator is intentionally strict: an aggregate topology count is not
    provenance, adaptive/dependent rounds are not removable, and every original
    verdict, count, failure and evidence address must survive the compound path.
    """
    topology = replay.get("topology") or {}
    pair = replay.get("pair") or {}
    before = pair.get("before") or []
    after = pair.get("compound_preserves") or []
    reasons: list[str] = []

    if topology.get("sequence") != ["verification", "verification"]:
        reasons.append("topology does not identify a verification-to-verification pair")
    if not isinstance(topology.get("occurrences"), int) or topology["occurrences"] < 1:
        reasons.append("topology has no observed occurrence")
    if not topology.get("source_sha256"):
        reasons.append("topology snapshot has no content identity")
    rounds = pair.get("rounds")
    if not (
        isinstance(rounds, list)
        and len(rounds) == 2
        and all(type(value) is int for value in rounds)
        and rounds[1] == rounds[0] + 1
    ):
        reasons.append("candidate rounds are not adjacent")
    if len(before) != 2 or any(row.get("kind") != "verification" for row in before):
        reasons.append("candidate does not contain two verification observations")
    relationship = pair.get("relationship")
    if relationship in {"adaptive", "dependent"}:
        reasons.append(f"{relationship} pair cannot remove a model-return boundary")
    elif relationship != "independent":
        reasons.append("pair independence is unknown")

    after_by_id = {str(row.get("id")): row for row in after}
    missing: list[str] = []
    mismatched: list[str] = []
    for original in before:
        result_id = str(original.get("id"))
        preserved = after_by_id.get(result_id)
        if preserved is None:
            missing.append(result_id)
        elif not _same_observation(original, preserved):
            mismatched.append(result_id)
    if missing:
        reasons.append("compound result omits: " + ", ".join(missing))
    if mismatched:
        reasons.append("compound result changes: " + ", ".join(mismatched))
    if len(after_by_id) != len(after):
        reasons.append("compound result contains duplicate observation ids")
    if len(after) != len(before):
        reasons.append("compound result changes the observation count")

    equivalent = not missing and not mismatched and len(after) == len(before)
    eligible = not reasons and equivalent
    return {
        "eligible": eligible,
        "claim_reduction": eligible,
        "before_model_returns": 2,
        "after_model_returns": 1,
        "missing_result_ids": missing,
        "mismatched_result_ids": mismatched,
        "reasons": reasons,
    }
