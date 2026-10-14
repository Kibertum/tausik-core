"""One strict transport contract for bounded L3 cohort actions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_ACTIONS = {"open", "status", "record", "decide"}
_DECISIONS = {"accept-risk", "manual-review", "repair-open"}


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return dict(value)


def _integer(value: Any, label: str, *, choices: set[int] | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    if choices is not None and value not in choices:
        raise ValueError(f"{label} must be one of {sorted(choices)}")
    return int(value)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{label} must be an array of non-empty strings")
    if nonempty and not value:
        raise ValueError(f"{label} must not be empty")
    return list(value)


def _only(payload: Mapping[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError("unknown cohort field(s): " + ", ".join(unknown))


def decode_cohort_request(raw: Any) -> dict[str, Any]:
    """Validate without coercion so CLI and MCP reject the same malformed input."""
    payload = _object(raw, "cohort request")
    action = _text(payload.get("action"), "action")
    if action not in _ACTIONS:
        raise ValueError("action must be open, status, record, or decide")
    json_output = payload.get("json", False)
    if not isinstance(json_output, bool):
        raise ValueError("json must be a boolean")

    if action == "open":
        _only(payload, {"action", "tasks", "story", "epic", "json"})
        selectors = [key for key in ("tasks", "story", "epic") if payload.get(key) is not None]
        if len(selectors) != 1:
            raise ValueError("open requires exactly one of tasks, story, or epic")
        out: dict[str, Any] = {"action": action, "json": json_output}
        key = selectors[0]
        out[key] = (
            _string_list(payload[key], "tasks", nonempty=True)
            if key == "tasks"
            else _text(payload[key], key)
        )
        return out

    if action == "status":
        _only(payload, {"action", "cohort_id", "json"})
        return {
            "action": action,
            "cohort_id": _integer(payload.get("cohort_id"), "cohort_id"),
            "json": json_output,
        }

    if action == "record":
        _only(
            payload,
            {
                "action",
                "cohort_id",
                "round",
                "results",
                "packet_digest",
                "author_model",
                "reviewer_model",
                "usage",
                "json",
            },
        )
        results = payload.get("results")
        if not isinstance(results, list) or any(not isinstance(item, Mapping) for item in results):
            raise ValueError("results must be an array of objects")
        usage = payload.get("usage")
        if usage is not None and not isinstance(usage, Mapping):
            raise ValueError("usage must be an object")
        return {
            "action": action,
            "cohort_id": _integer(payload.get("cohort_id"), "cohort_id"),
            "round": _integer(payload.get("round"), "round", choices={1, 2}),
            "results": [dict(item) for item in results],
            "packet_digest": _text(payload.get("packet_digest"), "packet_digest"),
            "author_model": _text(payload.get("author_model"), "author_model"),
            "reviewer_model": _text(payload.get("reviewer_model"), "reviewer_model"),
            "usage": dict(usage) if usage is not None else None,
            "json": json_output,
        }

    _only(
        payload,
        {"action", "cohort_id", "decision", "owner", "reason", "finding_refs", "json"},
    )
    decision = _text(payload.get("decision"), "decision")
    if decision not in _DECISIONS:
        raise ValueError("decision must be accept-risk, manual-review, or repair-open")
    return {
        "action": action,
        "cohort_id": _integer(payload.get("cohort_id"), "cohort_id"),
        "decision": decision,
        "owner": _text(payload.get("owner"), "owner"),
        "reason": _text(payload.get("reason"), "reason"),
        "finding_refs": _string_list(payload.get("finding_refs", []), "finding_refs"),
        "json": json_output,
    }


def execute_cohort_request(svc: Any, raw: Any) -> tuple[dict[str, Any], bool]:
    """Validate and execute the transport-neutral cohort request."""
    request = decode_cohort_request(raw)
    from review_cohort import (
        cohort_status,
        decide_review_cohort,
        open_review_cohort,
        record_review_round,
    )

    action = request["action"]
    if action == "open":
        out = open_review_cohort(
            svc,
            tasks=request.get("tasks"),
            story=request.get("story"),
            epic=request.get("epic"),
        )
    elif action == "status":
        out = cohort_status(svc, request["cohort_id"])
    elif action == "record":
        out = record_review_round(
            svc,
            request["cohort_id"],
            request["round"],
            request["results"],
            packet_digest=request["packet_digest"],
            author_model=request["author_model"],
            reviewer_model=request["reviewer_model"],
            usage=request["usage"],
        )
    else:
        out = decide_review_cohort(
            svc,
            request["cohort_id"],
            request["decision"],
            owner=request["owner"],
            reason=request["reason"],
            finding_refs=request["finding_refs"],
        )
    return out, request["json"]
