"""Negative controls, content-addressed evidence and privacy scans."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Final, Mapping, Sequence, cast

from adherence_policy import (
    PASSING_RESULT,
    RESULTS,
    SENTINEL_NAMES,
    ContractError,
    _HEX_SHA,
    _OPAQUE_ID,
    artifact_hash,
    policy_artifact,
)
from adherence_registry import _route_by_name, registry_artifact
from adherence_runtime import _validated_events, evaluate

_EVALUATOR_SOURCES: Final[tuple[str, ...]] = (
    "adherence_contract.py",
    "adherence_policy.py",
    "adherence_registry.py",
    "adherence_runtime.py",
    "adherence_evidence.py",
)


def evaluator_source_hash() -> str:
    """Hash every source file that participates in the public evaluator."""

    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in sorted(_EVALUATOR_SOURCES):
        encoded_name = name.encode("utf-8")
        content = (root / name).read_bytes()
        digest.update(len(encoded_name).to_bytes(8, "big"))
        digest.update(encoded_name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _sentinel_streams(
    valid_events: Sequence[Mapping[str, object]],
) -> dict[str, list[dict[str, object]]]:
    checked = _validated_events(valid_events)
    failures = {
        "execution_lease": ("invalid_execution_lease", "missing"),
        "task_package": ("incomplete_task_package", "missing"),
        "continuity": ("missing_continuity", "missing"),
        "memory_preflight": ("missing_memory_preflight", "missing"),
        "dead_end_repeat": ("unoverridden_dead_end_repeat", "unoverridden"),
        "stop_decision": ("premature_stop", "premature"),
        "handoff_resume": ("incorrect_handoff_resume", "incorrect"),
    }
    streams: dict[str, list[dict[str, object]]] = {}
    for kind, (name, result) in failures.items():
        mutated = copy.deepcopy(checked)
        next(event for event in mutated if event["kind"] == kind)["result"] = result
        streams[name] = mutated

    for kind in RESULTS:
        if kind == "dead_end_repeat":
            continue
        missing = copy.deepcopy(checked)
        missing.remove(next(event for event in missing if event["kind"] == kind))
        for sequence, event in enumerate(missing, start=1):
            event["sequence"] = sequence
        streams[f"absent_{kind}_event"] = missing

    absent_action = copy.deepcopy(checked)
    removed_action = absent_action[0]["action_id"]
    absent_action = [event for event in absent_action if event["action_id"] != removed_action]
    for sequence, event in enumerate(absent_action, start=1):
        event["sequence"] = sequence
    streams["absent_entire_action"] = absent_action

    duplicate = copy.deepcopy(checked)
    duplicate[-1]["event_id"] = duplicate[0]["event_id"]
    streams["duplicate_event_id"] = duplicate

    reordered = copy.deepcopy(checked)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    streams["reordered_events"] = reordered
    return streams


def run_negative_control(valid_events: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Execute every frozen sentinel; success means all are rejected."""

    checked = _validated_events(valid_events)
    expected_actions = frozenset(str(event["action_id"]) for event in checked)
    streams = _sentinel_streams(checked)
    if tuple(streams) != SENTINEL_NAMES:
        raise ContractError("negative-control sentinel inventory drifted")
    results: list[dict[str, object]] = []
    for name, events in streams.items():
        try:
            accepted = evaluate(events, expected_actions=expected_actions).accepted
        except ContractError:
            accepted = False
        results.append({"accepted": accepted, "name": name, "rejected": not accepted})
    rejected = sum(bool(row["rejected"]) for row in results)
    expected = len(SENTINEL_NAMES)
    return {
        "accepted": expected - rejected,
        "executed": len(results),
        "expected": expected,
        "passed": len(results) == expected and rejected == expected,
        "rejected": rejected,
        "results": results,
    }


def build_evidence(
    events: Sequence[Mapping[str, object]],
    phase: str,
    commit_sha: str,
    integration_census: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Build content-addressed evidence without free-text event payloads."""

    if not events:
        raise ContractError("zero events cannot produce evidence")
    if phase not in {"negative-control", "acceptance"}:
        raise ContractError(f"unknown evidence phase: {phase}")
    if not _HEX_SHA.fullmatch(commit_sha):
        raise ContractError("commit_sha must be 40 lowercase hexadecimal characters")
    if not integration_census:
        raise ContractError("integration census is required for evidence")
    census = [dict(row) for row in integration_census]
    for row in census:
        if set(row) != {"action_id", "event_count", "event_sha256", "route", "status"}:
            raise ContractError("integration census fields differ from the closed schema")
        if not isinstance(row["action_id"], str) or not _OPAQUE_ID.fullmatch(row["action_id"]):
            raise ContractError("integration census action_id must be opaque")
        event_count = row["event_count"]
        if type(event_count) is not int or cast(int, event_count) < 0:
            raise ContractError("integration census event_count must be a non-negative integer")
        if not isinstance(row["event_sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", row["event_sha256"]
        ):
            raise ContractError("integration census event_sha256 must be canonical")
        if row["status"] != "executed" or str(row["route"]) not in _route_by_name():
            raise ContractError("integration census route or status is invalid")
    checked = _validated_events(events)
    verdict = evaluate(checked)
    fixture_sha256 = artifact_hash(checked)
    integration_census_sha256 = artifact_hash(census)
    by_action: dict[str, list[dict[str, object]]] = {}
    for event in checked:
        by_action.setdefault(str(event["action_id"]), []).append(event)
    census_actions = {str(row["action_id"]) for row in census}
    reconciled_rows: list[dict[str, object]] = []
    for row in census:
        action_events = by_action.get(str(row["action_id"]), [])
        matches = (
            cast(int, row["event_count"]) == len(action_events)
            and str(row["event_sha256"]) == artifact_hash(action_events)
            and bool(action_events)
            and all(event["route"] == row["route"] for event in action_events)
        )
        reconciled_rows.append(
            {
                "action_id": row["action_id"],
                "event_count": len(action_events),
                "matched": matches,
                "route": row["route"],
            }
        )
    census_reconciled = (
        all(bool(row["matched"]) for row in reconciled_rows) and set(by_action) == census_actions
    )
    evaluator_sha256 = evaluator_source_hash()
    evidence: dict[str, object] = {
        "base_commit_sha": commit_sha,
        "evaluator_sha256": evaluator_sha256,
        "fixture_sha256": fixture_sha256,
        "integration_census_sha256": integration_census_sha256,
        "phase": phase,
        "policy_sha256": artifact_hash(policy_artifact()),
        "registry_sha256": artifact_hash(registry_artifact()),
        "census_reconciliation": {
            "matched": sum(bool(row["matched"]) for row in reconciled_rows),
            "passed": census_reconciled,
            "rows": reconciled_rows,
            "total": len(reconciled_rows),
        },
    }
    evidence["contract_bundle_sha256"] = artifact_hash(
        {
            "evaluator_sha256": evaluator_sha256,
            "fixture_sha256": fixture_sha256,
            "integration_census_sha256": integration_census_sha256,
            "policy_sha256": evidence["policy_sha256"],
            "registry_sha256": evidence["registry_sha256"],
        }
    )
    if phase == "negative-control":
        report = run_negative_control(checked)
        evidence.update(
            {
                "accepted": bool(report["passed"]),
                "counts": {
                    "collected": report["executed"],
                    "deselected": 0,
                    "failed": report["accepted"],
                    "passed": report["rejected"],
                    "executed": report["executed"],
                    "expected": report["expected"],
                },
                "results": report["results"],
                "sentinel_sha256": artifact_hash(list(SENTINEL_NAMES)),
            }
        )
    else:
        passed = sum(event["result"] == PASSING_RESULT[str(event["kind"])] for event in checked)
        evidence.update(
            {
                "accepted": verdict.accepted and census_reconciled,
                "counts": {
                    "collected": len(checked),
                    "deselected": 0,
                    "failed": len(checked) - passed,
                    "passed": passed,
                },
                "metrics": verdict.metrics,
            }
        )
    evidence["content_sha256"] = artifact_hash(evidence)
    return evidence


_CANARY_SINKS: Final[tuple[str, ...]] = ("db", "stdout", "stderr", "json")


def scan_canary(sinks: Mapping[str, str], canary: str) -> list[str]:
    """Return evidence sinks that leaked the supplied privacy canary."""

    if set(sinks) != set(_CANARY_SINKS):
        raise ContractError(f"canary scan requires exactly these sinks: {_CANARY_SINKS}")
    if not canary:
        raise ContractError("canary must not be empty")
    needles = {
        canary,
        json.dumps(canary, ensure_ascii=True)[1:-1],
        base64.b64encode(canary.encode("utf-8")).decode("ascii"),
    }
    return [name for name in _CANARY_SINKS if any(needle in sinks[name] for needle in needles)]
