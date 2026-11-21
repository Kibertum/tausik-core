"""Host-neutral DYNAMIC projection refresh with an explicit target.

Canonical session/task/handoff state lives in the DB. Instruction files
(CLAUDE.md, AGENTS.md, Cursor rules, …) are optional projections. A refresh
without `--target` is refused; a file without DYNAMIC markers is hand-maintained
and is never overwritten.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Literal

from claudemd_writer import (
    CLAUDEMD_SIBLING_BASENAME,
    _MARKER_END,
    _MARKER_START,
    apply_dynamic_section,
)
from ide_utils import IDE_REGISTRY

OutcomeStatus = Literal[
    "updated",
    "unchanged",
    "target_required",
    "unknown_target",
    "missing",
    "hand_maintained",
    "error",
]


@dataclass(frozen=True)
class RefreshOutcome:
    status: OutcomeStatus
    target: str | None
    path: str | None
    message: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def ownership_of(path: str) -> Literal["missing", "hand_maintained", "managed"]:
    if not os.path.isfile(path):
        return "missing"
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return "missing"
    if _MARKER_START not in text or _MARKER_END not in text:
        return "hand_maintained"
    return "managed"


def resolve_target_path(project_dir: str, target: str) -> str | None:
    """Map a host-neutral target id to a path under project_dir."""
    key = (target or "").strip().lower()
    if key in ("agents", "agents.md"):
        return os.path.join(project_dir, CLAUDEMD_SIBLING_BASENAME)
    if key in IDE_REGISTRY:
        rel = IDE_REGISTRY[key]["rules_file"]
        return os.path.join(project_dir, rel)
    if key in ("claude.md",):
        return os.path.join(project_dir, "CLAUDE.md")
    return None


def refresh_target(
    project_dir: str,
    target: str | None,
    dynamic_content: str,
    *,
    dry_run: bool = False,
) -> RefreshOutcome:
    """Apply DYNAMIC content to one explicit target. Never picks a default file."""
    if not target or not str(target).strip():
        return RefreshOutcome(
            "target_required",
            None,
            None,
            "context refresh requires --target "
            f"(one of: {', '.join(sorted(IDE_REGISTRY))}, agents)",
        )
    path = resolve_target_path(project_dir, target)
    if path is None:
        return RefreshOutcome(
            "unknown_target",
            target,
            None,
            f"unknown target {target!r}; known: {', '.join(sorted(IDE_REGISTRY))}, agents",
        )
    kind = ownership_of(path)
    if kind == "missing":
        return RefreshOutcome("missing", target, path, f"file not found: {path}")
    if kind == "hand_maintained":
        return RefreshOutcome(
            "hand_maintained",
            target,
            path,
            f"hand-maintained or unmanaged (no {_MARKER_START}): {path} — not modified",
        )
    msg, changed = apply_dynamic_section(path, dynamic_content, dry_run)
    if msg.startswith("Error reading "):
        return RefreshOutcome("error", target, path, msg)
    if "marker not found" in msg:
        return RefreshOutcome("hand_maintained", target, path, msg)
    return RefreshOutcome(
        "updated" if changed else "unchanged",
        target,
        path,
        msg,
    )


def outcome_is_success(outcome: RefreshOutcome) -> bool:
    return outcome.status in ("updated", "unchanged")


def dump_outcome(outcome: RefreshOutcome) -> str:
    return json.dumps(outcome.as_dict(), ensure_ascii=False)
