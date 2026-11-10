"""Public facade for the deterministic 1.11.8 adherence contract."""

from adherence_evidence import build_evidence, run_negative_control, scan_canary
from adherence_policy import (
    EVENT_FIELDS,
    RESULTS,
    SENTINEL_NAMES,
    ContractError,
    Verdict,
    artifact_hash,
    policy_artifact,
)
from adherence_registry import (
    _READ_ROUTES,
    _classification,
    _hook_route,
    discover_dispatch_inventory,
    registry_artifact,
)
from adherence_runtime import AdherenceRecorder, active_recorder, append_sink_events, evaluate

__all__ = [
    "AdherenceRecorder",
    "ContractError",
    "EVENT_FIELDS",
    "RESULTS",
    "SENTINEL_NAMES",
    "Verdict",
    "active_recorder",
    "append_sink_events",
    "artifact_hash",
    "build_evidence",
    "discover_dispatch_inventory",
    "evaluate",
    "policy_artifact",
    "registry_artifact",
    "run_negative_control",
    "scan_canary",
    "_READ_ROUTES",
    "_classification",
    "_hook_route",
]
