"""Exact protected-action identity under an attested host."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from memory_preflight_classification import (
    PROTECTED_KINDS,
    binding_payload,
    classify_action,
    normalize_host_shell_tool,
)
from memory_preflight_errors import MemoryPreflightError


def action_binding(
    tool_name: str, tool_input: Mapping[str, Any], kind: str, *, host_instance: str | None = None
) -> tuple[str, str]:
    if kind not in PROTECTED_KINDS:
        raise MemoryPreflightError("PROTECTED_KIND_UNKNOWN", f"unsupported kind {kind!r}")
    bound_tool = normalize_host_shell_tool(tool_name)
    # Codex reports PowerShell execution as Bash. Other hosts retain dialect binding.
    if host_instance == "codex" and bound_tool in {"Bash", "PowerShell"}:
        bound_tool = "Bash"
    observed = classify_action(tool_name, tool_input)
    if observed != kind:
        raise MemoryPreflightError(
            "PROTECTED_KIND_MISMATCH",
            f"trusted identifier classifies as {observed!r}, not {kind!r}",
        )
    payload = json.dumps(
        binding_payload(tool_name, tool_input),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    payload_hash = hashlib.sha256(payload.encode()).hexdigest()
    target = bound_tool.strip().lower()
    action_id = hashlib.sha256(f"{kind}\0{target}\0{payload_hash}".encode()).hexdigest()
    return action_id, payload_hash
