"""Budgeted memory-only agent brief — one call, no session.

Uses advertise_do_dont() as the do/dont source. Optional fields may truncate
under max_bytes; required profile fields never silently drop.
"""

from __future__ import annotations

import json
from typing import Any

from memory_only_backlog import advertise_do_dont, profile_of_dir

DEFAULT_MAX_BYTES = 8192
MIN_MAX_BYTES = 512
MAX_MAX_BYTES = 65_536

#: Where owner agreements, facts, stop-doing and drafts go (canon B).
DECIDE_VS_MEMORY = {
    "owner_choice": ("tausik_decide — binding owner agreement; include rejected alternatives"),
    "observed_fact": ("tausik_memory_add type=context|pattern — observed fact with provenance"),
    "stop_doing": (
        "tausik_memory_add type=dead_end|gotcha — or tausik_dead_end; what failed and why"
    ),
    "weekly_draft": (
        "light task under backlog_policy=B, or a decide/memory note — not a SENAR ritual"
    ),
    "task_slug_on_memory_add": (
        "optional under memory-only; do not invent a task just to attach memory"
    ),
    "no_task_before_decide_or_memory": True,
}


def _json_bytes(payload: dict[str, Any]) -> int:
    return len(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def _set_exact_size(package: dict[str, Any]) -> None:
    size = _json_bytes(package)
    while package.get("bytes") != size:
        package["bytes"] = size
        size = _json_bytes(package)


def build_agent_brief(
    svc: Any,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    """Return a package-shaped brief. Never starts or extends a session."""
    if type(max_bytes) is not int or not MIN_MAX_BYTES <= max_bytes <= MAX_MAX_BYTES:
        raise ValueError(f"max_bytes must be {MIN_MAX_BYTES}..{MAX_MAX_BYTES}")
    try:
        tausik_dir = svc.tausik_dir() if svc is not None else None
    except Exception:  # noqa: BLE001 — unknown project still gets a truthful brief
        tausik_dir = None
    profile = profile_of_dir(tausik_dir)
    surface = advertise_do_dont()
    if profile == "memory-only":
        next_hint = (
            "Call tausik_memory_search / tausik_decisions_list before guessing; "
            "use light task tools from do[]; skip session_start and verify unless "
            "the owner asks for full_path."
        )
        dont = list(surface["dont"])
        do = list(surface["do"])
        # Self must appear in do once registered.
        if "tausik_memory_brief" not in do:
            do = sorted({*do, "tausik_memory_brief"})
    else:
        next_hint = (
            "governance_profile=full: open work with tausik_session_open / "
            "tausik_task_start as usual. This brief is the memory-only playbook."
        )
        do = []
        dont = []
    required = {
        "governance_profile": profile,
        "backlog_policy": surface["backlog_policy"] if profile == "memory-only" else None,
        "do": do,
        "dont": dont,
        "decide_vs_memory": dict(DECIDE_VS_MEMORY),
        "next_hint": next_hint,
        "session_created": False,
    }
    package: dict[str, Any] = {
        "schema_version": 1,
        "max_bytes": max_bytes,
        "required": required,
        "optional": {
            "playbook": "search → decide/memory_add → light task only when a trail helps",
        },
        "overflow": False,
        "omitted": [],
    }
    _set_exact_size(package)
    if package["bytes"] <= max_bytes:
        return package
    # Drop optional first; required fields stay even if over budget (explicit overflow).
    package["optional"] = {}
    package["overflow"] = True
    package["omitted"] = ["optional"]
    _set_exact_size(package)
    if package["bytes"] > max_bytes:
        package["overflow_reason"] = "required_fields_exceed_budget"
    return package


def serialize_agent_brief(svc: Any, *, max_bytes: int = DEFAULT_MAX_BYTES) -> str:
    return json.dumps(
        build_agent_brief(svc, max_bytes=max_bytes),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
