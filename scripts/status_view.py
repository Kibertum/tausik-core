"""One status model, two renderers — the shared source for `tausik status`.

status-cli-mcp-divergence: `cmd_status` (CLI) and `_handle_status` (MCP) both
formatted `svc.get_status()`, but each surfaced a DIFFERENT subset of signals —
the CLI gave risk / RENAR / epics / calibration / capacity / skill-set warning
and hid open explorations and audit-overdue; the MCP handler did the exact
opposite. A human on the CLI and an agent on MCP saw two different projects,
which defeats the point of a shared dashboard.

`build_status_view` gathers EVERY signal into one structured dict; the two
`render_status_*` functions differ only in output shape (the CLI prints line by
line, the MCP handler returns a joined string). Both draw the same signal set,
so the two channels can no longer diverge.

It also fixes the CLI's own copy of `mcp-config-read-paths-ignore-project-handle`:
`cmd_status` resolved `load_config()` THREE times off the process cwd and never
threaded `tausik_dir`. The view reads config exactly once, scoped to the svc's
own project directory — the same fix the MCP side already carries.
"""

from __future__ import annotations

import os
from typing import Any


def _skill_set_warning(project_root: str | None) -> str | None:
    """One-line nudge when the deployed skills dir is well above the v1.4 default.

    Best-effort and filesystem-only: a failure must never break `status`. Reused
    verbatim from the CLI's former `_maybe_print_skill_set_warning`, now surfaced
    on both channels so the two dashboards agree.
    """
    try:
        from ide_utils import get_skills_dir

        skills_dir = get_skills_dir(project_root or os.getcwd())
    except Exception:  # noqa: BLE001 — a warning must never break `status`
        skills_dir = os.path.join(".claude", "skills")
    if not os.path.isdir(skills_dir):
        return None
    try:
        deployed = [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))]
    except OSError:
        return None
    n = len(deployed)
    # Default 12 + brain conditional + small slack for explicitly installed.
    if n <= 14:
        return None
    return (
        f"Skills: {n} deployed (v1.4 default = 12 core + 1 conditional). "
        "Re-bootstrap to shrink: `python bootstrap/bootstrap.py --ide claude` "
        "(use `--include-official` to keep registry stubs). Per-skill: "
        "`tausik skill activate <name>`."
    )


def build_status_view(
    svc: Any,
    *,
    verbose: bool = False,
    tausik_dir: str | None = None,
    include_rich: bool = True,
) -> dict[str, Any]:
    """Gather every status signal into one structured dict for either renderer.

    `data` is `svc.get_status()` enriched IN PLACE with the keys
    `format_status_compact_json` reads (session minutes, session_max_minutes,
    exploration, audit_overdue_sessions), so the compact JSON path is identical
    on both channels. The rich-only signals (risk / RENAR / epics / calibration /
    capacity / skill warning) sit alongside it. Every enrichment is best-effort:
    a failing signal degrades to None, never raises.

    ``include_rich=False`` is the compact-JSON hot path (`--compact`, and the
    `/start` compound RPC): it still enriches `data` (cheap, and needed by the
    compact formatter) but skips the extra DB queries and the skills filesystem
    scan behind the rich-only signals, which the compact output never renders.
    """
    from project_config import (
        DEFAULT_SESSION_CAPACITY_CALLS,
        DEFAULT_SESSION_MAX_MINUTES,
        load_config,
    )

    data = svc.get_status()

    # Read config ONCE, scoped to the svc's own project (not the process cwd).
    td = tausik_dir
    if td is None and hasattr(svc, "tausik_dir"):
        try:
            td = svc.tausik_dir()
        except Exception:  # noqa: BLE001 — fall back to ambient config on any resolve error
            td = None
    cfg = load_config(td)
    max_min = cfg.get("session_max_minutes", DEFAULT_SESSION_MAX_MINUTES)
    cap = cfg.get("session_capacity_calls", DEFAULT_SESSION_CAPACITY_CALLS)

    session = data.get("session")

    # Report the limit this session is ACTUALLY held to, not the configured base.
    # `session extend` records its new limit as an event; the Rule 9.2 warning
    # resolved it that way, the DISPLAY did not — so a user who extended to 300
    # kept reading "61m / 180m" while the threshold that actually fires used 300.
    # Same number, two formulas.
    #
    # Resolved ONCE here and handed to the warning, rather than each side
    # resolving it for itself: `effective_session_limit` scans the session's
    # events, and this function runs on the compact hot path behind `/start`,
    # where a duplicate scan is exactly the kind of cost this codebase keeps
    # taking back out.
    effective_max = max_min
    if session:
        try:
            from service_session_metrics import effective_session_limit

            effective_max = effective_session_limit(svc.be, session["id"], max_min)
        except Exception:  # noqa: BLE001 — never fail status on limit resolution
            effective_max = max_min
    data["session_max_minutes"] = effective_max

    duration_warning = svc.session_check_duration(max_min, effective_limit=effective_max)

    # Session active/wall minutes (SENAR Rule 9.2 metric is active; wall is
    # informational). Enrich `data` so the compact JSON carries them too.
    active_min = wall_min = active_sec = 0
    if session:
        try:
            active_sec = svc.session_active_seconds()
            active_min = svc.session_active_minutes()
            wall_min = svc.session_wall_minutes()
        except Exception:  # noqa: BLE001 — never fail status on metric calc
            active_sec = active_min = wall_min = 0
        data["active_minutes"] = active_min
        data["active_seconds"] = active_sec
        data["wall_minutes"] = wall_min

    # SENAR 5.1 open exploration + 9.5 audit overdue — enrich `data` so the
    # compact path emits them (previously only the MCP handler did this, so the
    # CLI compact silently dropped both).
    exploration: dict | None = None
    try:
        exploration = svc.exploration_current()
    except Exception:  # noqa: BLE001 — never fail status on metric calc
        exploration = None
    if exploration:
        data["exploration"] = exploration
    audit_overdue = 0
    try:
        audit_overdue = int(svc.audit_overdue_sessions())
    except Exception:  # noqa: BLE001 — never fail status on metric calc (incl. sqlite errors)
        audit_overdue = 0
    if audit_overdue:
        data["audit_overdue_sessions"] = audit_overdue

    if not include_rich:
        # Compact hot path: `data` is enriched (counts, session minutes,
        # exploration, audit) which is all the compact JSON reads. Skip the
        # rich-only DB queries + skills scan entirely.
        return {
            "data": data,
            "verbose": verbose,
            "max_min": effective_max,
            "duration_warning": duration_warning,
            "session_metrics": (
                {"active_min": active_min, "wall_min": wall_min, "active_sec": active_sec}
                if session
                else None
            ),
            "risk_line": None,
            "renar_line": None,
            "epics_count": len(data.get("epics") or []),
            "calibration": None,
            "capacity": None,
            "skill_warning": None,
            "exploration": exploration,
            "audit_overdue": audit_overdue,
        }

    # Rich-only closure risk — only when scored rows exist.
    risk_line: str | None = None
    try:
        from risk_metrics import format_risk_status_line, risk_summary

        _risk = risk_summary(svc.be._conn)
        if _risk:
            risk_line = format_risk_status_line(_risk)
    except Exception:  # noqa: BLE001 — best-effort: display-only, never breaks status
        risk_line = None

    # RENAR adoption level (display-only).
    renar_line: str | None = None
    try:
        from renar_conformance import current_level, format_status_line

        renar_line = format_status_line(current_level(svc.be._conn))
    except Exception:  # noqa: BLE001 — best-effort: display-only, never breaks status
        renar_line = None

    # Calibration drift (estimation bias).
    calibration: dict | None = None
    try:
        calibration = svc.get_metrics().get("calibration_drift")
    except Exception:  # noqa: BLE001 — best-effort: display-only, never breaks status
        calibration = None

    # Session capacity (tool-call budget) — only when a session is active.
    capacity: dict | None = None
    if session:
        try:
            capacity = svc.be.session_capacity_summary(cap)
        except Exception:  # noqa: BLE001 — best-effort: display-only, never breaks status
            capacity = None

    project_root = os.path.dirname(td) if td else None
    skill_warning = _skill_set_warning(project_root)

    return {
        "data": data,
        "verbose": verbose,
        # The EFFECTIVE limit, same as `data["session_max_minutes"]` above — the
        # text renderer prints this one, and printing the base here while the
        # compact JSON carried the effective value would just move the
        # contradiction rather than fix it.
        "max_min": effective_max,
        "duration_warning": duration_warning,
        "session_metrics": (
            {"active_min": active_min, "wall_min": wall_min, "active_sec": active_sec}
            if session
            else None
        ),
        "risk_line": risk_line,
        "renar_line": renar_line,
        "epics_count": len(data.get("epics") or []),
        "calibration": calibration,
        "capacity": capacity,
        "skill_warning": skill_warning,
        "exploration": exploration,
        "audit_overdue": audit_overdue,
    }


def _tasks_line(data: dict[str, Any]) -> str:
    counts = data["task_counts"]
    total = sum(counts.values())
    done = counts.get("done", 0)
    parts = [f"Tasks: {done}/{total} done"]
    for st in ("planning", "active", "blocked", "review"):
        if counts.get(st):
            parts.append(f"{counts[st]} {st}")
    return parts[0] + (", " + ", ".join(parts[1:]) if len(parts) > 1 else "")


def _session_line(view: dict[str, Any]) -> str:
    data = view["data"]
    session = data.get("session")
    if not session:
        return "Session: none active"
    m = view["session_metrics"] or {"active_min": 0, "wall_min": 0}
    max_min = view["max_min"]
    if view.get("verbose"):
        active, wall = m["active_min"], m["wall_min"]
        idle = f", {round((1 - active / wall) * 100)}% idle" if wall > 0 and active < wall else ""
        return f"Session: #{session['id']} (active {active}m / {max_min}m, wall {wall}m{idle})"
    return f"Session: #{session['id']} (active {m['active_min']}m / {max_min}m)"


def status_primary_lines(view: dict[str, Any]) -> list[str]:
    """The ordered signal lines shared by both channels (no warnings)."""
    data = view["data"]
    lines = [_tasks_line(data)]
    if view["risk_line"]:
        lines.append(view["risk_line"])
    if view["renar_line"]:
        lines.append(view["renar_line"])
    lines.append(_session_line(view))
    if view["epics_count"]:
        lines.append(f"Epics: {view['epics_count']}")
    drift = view["calibration"]
    if drift:
        lines.append(
            f"Calibration: {drift['label']} "
            f"(actual/budget={drift['avg_ratio']}, n={drift['samples']})"
        )
    cap = view["capacity"]
    if cap:
        marker = " ⚠ overshoot" if cap["remaining"] < 0 else ""
        lines.append(
            f"Capacity: {cap['used']}/{cap['capacity']} used, "
            f"{cap['planned_active']} planned, {cap['remaining']} remaining{marker}"
        )
    return lines


def status_warning_lines(view: dict[str, Any]) -> list[str]:
    """The ordered warning lines shared by both channels."""
    warnings: list[str] = []
    if view["duration_warning"]:
        warnings.append(view["duration_warning"])
    exp = view["exploration"]
    if exp:
        elapsed = exp.get("elapsed_min", "?")
        over = " — OVER LIMIT" if exp.get("over_limit") else ""
        warnings.append(
            f"Open exploration #{exp.get('id')}: {exp.get('title', '')} ({elapsed}m{over})"
        )
    if view["audit_overdue"]:
        warnings.append(
            f"SENAR Rule 9.5: {view['audit_overdue']} sessions since last audit. "
            "Run /review then audit mark."
        )
    if view["skill_warning"]:
        warnings.append(view["skill_warning"])
    return warnings


def render_status_cli(view: dict[str, Any]) -> str:
    """Human render for the CLI: one signal per line, warnings prefixed."""
    out = list(status_primary_lines(view))
    out.extend(f"  WARNING: {w}" for w in status_warning_lines(view))
    return "\n".join(out)


def render_status_mcp(view: dict[str, Any]) -> str:
    """Agent render for the MCP handler: same signals, ⚠-prefixed warnings."""
    out = list(status_primary_lines(view))
    out.extend(f"⚠ {w}" for w in status_warning_lines(view))
    return "\n".join(out)
