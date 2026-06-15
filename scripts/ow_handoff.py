"""Orchestrator-worker handoff contract + worker skill profile (v15-ow-subagent-profile).

The deterministic structured payload the orchestrator hands to a worker
sub-agent (via the Agent tool) and that the worker echoes back. Pure functions,
no I/O — so the contract is identical on both ends (round-trip = identity).
"""

from __future__ import annotations

import json
from typing import Any

# Trimmed worker skill profile: just enough to execute + verify a scoped task,
# omitting orchestrator-only skills (plan / explore / brain / interview).
WORKER_SKILLS: tuple[str, ...] = ("task", "test", "debug", "review", "commit")

# Task fields carried in the contract (interpretation + scope the worker needs).
_CONTRACT_FIELDS: tuple[str, ...] = (
    "slug",
    "goal",
    "acceptance_criteria",
    "scope",
    "scope_exclude",
)


def build_handoff_contract(
    task: dict[str, Any], delegation: dict[str, Any] | None
) -> dict[str, Any]:
    """Build the deterministic handoff contract from a task row + delegation record.

    Missing optional fields degrade to "" (never KeyError). The result is the
    exact payload the orchestrator passes and the worker echoes back.
    """
    contract: dict[str, Any] = {f: (task.get(f) or "") for f in _CONTRACT_FIELDS}
    contract["model"] = (delegation or {}).get("model") or ""
    contract["skills"] = list(WORKER_SKILLS)
    return contract


def serialize_contract(contract: dict[str, Any]) -> str:
    """Deterministic JSON (sorted keys) — round-trips to an identical dict."""
    return json.dumps(contract, sort_keys=True, ensure_ascii=False)
