"""Structured identity and policy for one verification run.

``verification_runs.command`` remains useful audit text, but it is not an
authority.  Replay and presentation rights live in dedicated columns and are
written from the same descriptor that supplies the receipt identity.  Rows
which predate this descriptor have NULL columns and are legacy audit records:
no reader may infer rights by parsing their command text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

REPLAYABLE = "replayable"
NON_REPLAYABLE = "non_replayable"
PRESENTABLE_ONCE = "single_use"
NOT_PRESENTABLE = "none"

_REPLAY_POLICIES = {REPLAYABLE, NON_REPLAYABLE}
_PRESENTATION_POLICIES = {PRESENTABLE_ONCE, NOT_PRESENTABLE}


@dataclass(frozen=True)
class VerificationRunDescriptor:
    """Immutable structured contract shared by every proof reader."""

    trigger: str
    files: tuple[str, ...]
    gate_signature: str
    replay_policy: str
    presentation_policy: str

    def __post_init__(self) -> None:
        if not self.trigger or not self.gate_signature:
            raise ValueError("verification descriptor requires trigger and gate signature")
        if self.replay_policy not in _REPLAY_POLICIES:
            raise ValueError(f"unknown replay policy: {self.replay_policy}")
        if self.presentation_policy not in _PRESENTATION_POLICIES:
            raise ValueError(f"unknown presentation policy: {self.presentation_policy}")
        if tuple(sorted(set(self.files))) != self.files:
            raise ValueError("verification descriptor files must be sorted and unique")

    @classmethod
    def create(
        cls,
        *,
        trigger: str,
        files: list[str],
        gate_signature: str,
        replayable: bool,
        presentable_once: bool,
    ) -> VerificationRunDescriptor:
        return cls(
            trigger=trigger,
            files=tuple(sorted(set(files))),
            gate_signature=gate_signature,
            replay_policy=REPLAYABLE if replayable else NON_REPLAYABLE,
            presentation_policy=PRESENTABLE_ONCE if presentable_once else NOT_PRESENTABLE,
        )

    def files_json(self) -> str:
        return json.dumps(self.files, ensure_ascii=True, separators=(",", ":"))


def descriptor_from_row(run: dict[str, Any]) -> VerificationRunDescriptor | None:
    """Read a complete descriptor, or refuse legacy/corrupt structured state."""
    values = (
        run.get("run_trigger"),
        run.get("run_files_json"),
        run.get("gate_signature"),
        run.get("replay_policy"),
        run.get("presentation_policy"),
    )
    if any(value is None for value in values):
        return None
    try:
        raw_files = json.loads(str(values[1]))
        if not isinstance(raw_files, list) or not all(isinstance(item, str) for item in raw_files):
            return None
        return VerificationRunDescriptor(
            trigger=str(values[0]),
            files=tuple(raw_files),
            gate_signature=str(values[2]),
            replay_policy=str(values[3]),
            presentation_policy=str(values[4]),
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def legacy_descriptor_refusal(run_id: Any, task_slug: str) -> str:
    return (
        f"verify-handle: run #{run_id} has no complete structured proof descriptor "
        "(legacy or corrupt row). Command text grants no replay or presentation rights. "
        f"Re-run `tausik verify --task {task_slug}`."
    )
