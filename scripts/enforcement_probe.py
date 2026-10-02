"""Capture one write probe in an explicitly marked disposable workspace.

The caller supplies the real host transport and task-state setup. Calling a hook
directly or using a fixture is not host evidence. This helper never changes trust,
permissions, or invokes another paid model session.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from enforcement_evidence import CASES, ROUTES


def capture_case(root: Path, route: str, case: str, invoke: Callable[[Path], dict]) -> dict:
    """Observe before/after bytes; failed invocation cannot manufacture protection."""
    root = root.resolve()
    if route not in ROUTES or case not in CASES:
        raise ValueError("Unsupported probe case")
    if not (root / ".tausik-probe-root").is_file():
        raise ValueError("Probe requires an explicitly marked disposable workspace")
    target = root / f"probe-{route}-{case}.txt"
    if target.is_symlink() or target.exists():
        raise ValueError("Probe target must be a new local file")
    before = hashlib.sha256(b"absent").hexdigest()
    try:
        outcome = invoke(target)
        if not isinstance(outcome, dict):
            raise ValueError("Invalid host probe response")
        result = {
            "result": "completed",
            "denied": outcome.get("denied"),
            "hook_fired": outcome.get("hook_fired"),
        }
    except Exception as exc:  # noqa: BLE001 — recorded as failed probe, never as successful denial
        result = {
            "result": "failed",
            "error": type(exc).__name__,
            "denied": None,
            "hook_fired": None,
        }
    if target.is_symlink():
        return {
            "result": "failed",
            "error": "symlink target",
            "denied": None,
            "hook_fired": None,
            "before_sha256": before,
            "after_sha256": None,
        }
    try:
        after = (
            hashlib.sha256(b"file:" + target.read_bytes()).hexdigest()
            if target.exists()
            else before
        )
    except OSError as exc:
        return {
            "result": "failed",
            "error": type(exc).__name__,
            "denied": None,
            "hook_fired": None,
            "before_sha256": before,
            "after_sha256": None,
        }
    return {**result, "before_sha256": before, "after_sha256": after}
