"""Light backlog when the project file says governance_profile=memory-only.

Session start and verify are not the default path. A task close skips
gates unless the caller sets full_path. A full profile never enters these
branches: an absent or any other value stays on the existing path.
"""

from __future__ import annotations

import json
from typing import Any

DEFERRED_TOOLS = frozenset({"tausik_session_start", "tausik_verify"})

#: Tools that stay usable under memory-only (light backlog, canon B).
LIGHT_BACKLOG_TOOLS = frozenset(
    {
        "tausik_memory_brief",
        "tausik_task_add",
        "tausik_task_list",
        "tausik_task_show",
        "tausik_task_log",
        "tausik_task_done",
        "tausik_task_quick",
        "tausik_memory_add",
        "tausik_memory_search",
        "tausik_decide",
        "tausik_search",
        "tausik_status",
        "tausik_doctor",
        "tausik_tool_schema",
    }
)

_DISABLED_REASON = (
    "governance_profile=memory-only: {tool} is not the default path. "
    "Light backlog tools stay available. "
    "Pass full_path=true only when the owner asks for the full path."
)

_ANNOTATION = "[profile=disabled] "

#: Stub for deferred advertise (not properties:{} — see mcp_tool_tiers).
_DEFER_SCHEMA: dict[str, Any] = {"type": "object", "additionalProperties": True}


def profile_from_mapping(cfg: dict | None) -> str:
    """Return memory-only only for that exact token. Anything else is full."""
    raw = (cfg or {}).get("governance_profile", "full")
    if isinstance(raw, str) and raw.strip().lower() == "memory-only":
        return "memory-only"
    return "full"


def profile_of_dir(tausik_dir: str | None) -> str:
    """Read the project file only. No directory means the full path."""
    if not tausik_dir:
        return "full"
    try:
        from project_config import load_project_config

        return profile_from_mapping(load_project_config(tausik_dir))
    except Exception:  # noqa: BLE001 — a profile read must not change the full path
        return "full"


def gates_are_skipped(svc: Any, full_path: bool) -> bool:
    """True when this close must not run verify or gates."""
    if full_path:
        return False
    try:
        tausik_dir = svc.tausik_dir()
    except Exception:  # noqa: BLE001 — unknown project stays on the full path
        return False
    return profile_of_dir(tausik_dir) == "memory-only"


def advertise_do_dont() -> dict[str, Any]:
    """do/dont lists for agent_brief and advertise annotations (same source)."""
    return {
        "do": sorted(LIGHT_BACKLOG_TOOLS),
        "dont": sorted(DEFERRED_TOOLS),
        "backlog_policy": "B",
    }


def annotate_advertise(tools: list[dict], svc: Any) -> list[dict]:
    """Annotate/defer SENAR write-path tools when the project is memory-only.

    Fail-open: any error returns the input list unchanged. Full profile is a
    no-op. Does not remove tools — call_tool still reaches them; deferred_reply
    refuses the body unless full_path=true.
    """
    try:
        tausik_dir = svc.tausik_dir() if svc is not None else None
    except Exception:  # noqa: BLE001 — unknown project keeps the full advertise
        return tools
    if profile_of_dir(tausik_dir) != "memory-only":
        return tools
    out: list[dict] = []
    for tool in tools:
        name = tool.get("name", "")
        if name not in DEFERRED_TOOLS:
            if name == "tausik_task_done":
                desc = tool.get("description") or ""
                note = " memory-only: closes without gates unless full_path=true."
                if note.strip() not in desc:
                    tool = {**tool, "description": desc.rstrip() + note}
            out.append(tool)
            continue
        desc = tool.get("description") or ""
        if not desc.startswith(_ANNOTATION):
            desc = _ANNOTATION + desc
        out.append(
            {
                **tool,
                "description": desc,
                "inputSchema": dict(_DEFER_SCHEMA),
            }
        )
    return out


def measure_advertise_bytes(tools: list[dict]) -> int:
    """UTF-8 size of the serialized advertise list (for before/after journals)."""
    return len(json.dumps(tools, ensure_ascii=False).encode("utf-8"))


def deferred_reply(svc: Any, name: str, args: dict | None) -> str | None:
    """JSON refusal for a deferred tool, or None when the call may run."""
    if name not in DEFERRED_TOOLS:
        return None
    if (args or {}).get("full_path") is True:
        return None
    if not gates_are_skipped(svc, False):
        return None
    return json.dumps(
        {
            "ok": False,
            "profile": "memory-only",
            "annotation": "profile=disabled",
            "tool": name,
            "reason": _DISABLED_REASON.format(tool=name),
        },
        ensure_ascii=False,
    )


def try_light_close(svc: Any, slug: str) -> dict[str, Any] | None:
    """Close without gates, or None when the profile is full.

    A planning task may close: the light backlog does not require QG-0.
    An already-done task is refused before any write.
    """
    if not gates_are_skipped(svc, False):
        return None
    from tausik_utils import ServiceError, utcnow_iso

    task = svc._require_task(slug)
    if task["status"] == "done":
        raise ServiceError(f"Task '{slug}' is already done")
    now = utcnow_iso()
    note = "LIGHT CLOSE: governance_profile=memory-only. Verify and gates were not run."
    with svc.be.transaction():
        svc.be.task_update(slug, status="done", completed_at=now, updated_at=now)
        svc.be.task_append_notes(slug, note)
    try:
        svc._cascade_done(slug)
    except Exception:  # noqa: BLE001,S110 — the task row is already closed
        pass
    try:
        from state_triggers import auto_export_entity

        auto_export_entity(svc, "tasks", slug)
    except Exception:  # noqa: BLE001,S110 — export is best-effort, as on the full path
        pass
    message = f"Task '{slug}' completed without gates (governance_profile=memory-only)."
    return {
        "ok": True,
        "slug": slug,
        "profile": "memory-only",
        "gates_skipped": True,
        "gates": [],
        "gates_passed": None,
        "blocking_failures": [],
        "warnings": [],
        "message": message,
        "reason": "governance_profile=memory-only: task_done did not run verify or gates",
    }


def memory_only_status_view(data: dict[str, Any]) -> dict[str, Any]:
    """Status view with the SENAR/RENAR walls left out."""
    payload = dict(data)
    payload["governance_profile"] = "memory-only"
    payload.pop("audit_overdue_closures", None)
    payload.pop("metric_targets_crossed", None)
    payload.pop("exploration", None)
    return {
        "data": payload,
        "verbose": False,
        "max_min": None,
        "duration_warning": None,
        "session_metrics": None,
        "risk_line": None,
        "renar_line": None,
        "epics_count": len(payload.get("epics") or []),
        "calibration": None,
        "capacity": None,
        "skill_warning": None,
        "exploration": None,
        "audit_overdue": 0,
        "metric_crossings": [],
        "update_line": None,
        "governance_profile": "memory-only",
    }


def memory_only_compact(data: dict[str, Any]) -> dict[str, Any]:
    """Compact status: backlog counts and the profile, nothing else."""
    counts = data["task_counts"]
    return {
        "governance_profile": "memory-only",
        "backlog_policy": "B",
        "tasks_done": counts.get("done", 0),
        "tasks_total": sum(counts.values()),
        "tasks_planning": counts.get("planning", 0),
        "tasks_active": counts.get("active", 0),
        "tasks_blocked": counts.get("blocked", 0),
        "tasks_review": counts.get("review", 0),
        "tasks_obsolete": counts.get("obsolete", 0),
        "epics": len(data.get("epics") or []),
    }
