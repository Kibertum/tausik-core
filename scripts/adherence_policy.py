"""Immutable adherence policy vocabulary and canonical hashing."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Final

SENTINEL_NAMES: Final[tuple[str, ...]] = (
    "invalid_execution_lease",
    "incomplete_task_package",
    "missing_continuity",
    "missing_memory_preflight",
    "unoverridden_dead_end_repeat",
    "premature_stop",
    "incorrect_handoff_resume",
    "absent_execution_lease_event",
    "absent_task_package_event",
    "absent_continuity_event",
    "absent_memory_preflight_event",
    "absent_stop_decision_event",
    "absent_handoff_resume_event",
    "absent_entire_action",
    "duplicate_event_id",
    "reordered_events",
)

POLICY_VERSION: Final[int] = 1
EVENT_SCHEMA_VERSION: Final[int] = 1

EVENT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "action_id",
        "boundary",
        "event_id",
        "kind",
        "lease_id",
        "package_fingerprint",
        "policy_version",
        "result",
        "route",
        "schema_version",
        "sequence",
        "task_id",
        "thread_id",
    }
)

RESULTS: Final[dict[str, tuple[str, ...]]] = {
    "execution_lease": ("valid", "missing", "ambiguous", "stale", "wrong_thread"),
    "task_package": ("complete", "missing", "overflow", "revision_conflict", "stale"),
    "continuity": ("satisfied", "missing"),
    "memory_preflight": ("valid", "missing", "error", "conflict", "stale"),
    "dead_end_repeat": ("overridden", "unoverridden"),
    "stop_decision": ("safe", "premature"),
    "handoff_resume": ("correct", "incorrect"),
}

PASSING_RESULT: Final[dict[str, str]] = {
    "execution_lease": "valid",
    "task_package": "complete",
    "continuity": "satisfied",
    "memory_preflight": "valid",
    "dead_end_repeat": "overridden",
    "stop_decision": "safe",
    "handoff_resume": "correct",
}

RATE_METRICS: Final[dict[str, tuple[str, str]]] = {
    "valid_execution_leases": ("execution_lease", "valid"),
    "complete_task_packages": ("task_package", "complete"),
    "required_continuity": ("continuity", "satisfied"),
    "protected_memory_preflights": ("memory_preflight", "valid"),
    "correct_hard_ceiling_handoff_resumes": ("handoff_resume", "correct"),
}

ZERO_COUNT_METRICS: Final[dict[str, tuple[str, str]]] = {
    "active_dead_end_repeats_without_override": ("dead_end_repeat", "unoverridden"),
    "premature_stops": ("stop_decision", "premature"),
}

_HEX_SHA = re.compile(r"^[0-9a-f]{40}$")
_OPAQUE_ID = re.compile(r"^(?:action|event|lease|package|task|thread)-[0-9a-f]{16}$")


class ContractError(ValueError):
    """The supplied event stream cannot be judged by the frozen contract."""


@dataclass(frozen=True)
class Verdict:
    """Acceptance result plus exact metric evidence."""

    accepted: bool
    metrics: dict[str, dict[str, object]]


def policy_artifact() -> dict[str, object]:
    """Return the JSON-safe, versioned policy artifact."""

    return {
        "canonicalization_version": 1,
        "change_rule": "version-bump-and-L3-review",
        "event_fields": sorted(EVENT_FIELDS),
        "event_schema_version": EVENT_SCHEMA_VERSION,
        "metric_specs": {
            "rates": {name: list(spec) for name, spec in sorted(RATE_METRICS.items())},
            "zero_counts": {name: list(spec) for name, spec in sorted(ZERO_COUNT_METRICS.items())},
        },
        "passing_results": dict(sorted(PASSING_RESULT.items())),
        "policy_version": POLICY_VERSION,
        "results": {kind: list(values) for kind, values in sorted(RESULTS.items())},
        "sentinels": list(SENTINEL_NAMES),
        "thresholds": {
            **{name: "100%" for name in RATE_METRICS},
            **{name: 0 for name in ZERO_COUNT_METRICS},
        },
    }


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def artifact_hash(value: object) -> str:
    """Hash a JSON artifact with the canonical encoding used by release evidence."""

    return hashlib.sha256(_canonical_bytes(value)).hexdigest()
