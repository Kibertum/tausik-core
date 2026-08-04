"""MCP handlers for the session domain — the session row and the /start envelope.

Split out of handlers.py by mcp-handlers-god-module-split. Follows the
convention already set by handlers_spec.py / handlers_adapt.py: the module owns
its handlers AND the slice of the dispatch table that names them, and
handlers.py merges it with `_DISPATCH.update(...)`.

`session_open` lives here rather than in handlers_status.py even though it
composes two status handlers: it is the /start entry point, its watchdog and
its projection allowlists exist to protect THAT call, and every one of them is
meaningless outside it.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Callable

from handlers_render import render_list
from handlers_status import _handle_self_check, _handle_status


def _do_session_current(svc: Any, args: dict) -> str:
    s = svc.session_current()
    return f"Session #{s['id']} started {s['started_at']}" if s else "No active session."


def _do_session_list(svc: Any, args: dict) -> str:
    sessions = svc.session_list(args.get("limit", 10))
    return render_list(
        sessions,
        lambda s: f"#{s['id']} [{s.get('ended_at', 'active')}] {(s.get('summary') or '')[:60]}",
        "No sessions.",
    )


def reset_checkpoint_counter(svc: Any) -> None:
    """Clear the SENAR Rule 9.3 tool-call counter — a HYGIENE operation.

    v2-session-split-and-drop: this used to be four unnamed lines inside
    `_do_session_handoff`, so writing a continuity document also reset the
    agent's context-budget counter. That is the two halves of "session" in one
    function: the handoff is about the WORK, the counter is about the AGENT.

    It stays best-effort — a counter that cannot be cleared must not stop a
    checkpoint from being recorded — but it is now a named operation a caller
    invokes on purpose, so a future caller that wants one without the other can
    have it.
    """
    try:
        svc.be.meta_set("tool_call_count", "0")
    except Exception:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        pass


def _do_session_handoff(svc: Any, args: dict) -> str:
    """Save the handoff, then reset the checkpoint counter.

    Both still happen on this path, and deliberately: `tausik_session_handoff`
    is what /checkpoint and /end call, and a checkpoint IS the moment the
    counter should restart. What changed is that the two are now separate,
    named, and ordered — the continuity write happens FIRST and its result is
    what the caller sees, so a counter failure can no longer be mistaken for a
    handoff failure.
    """
    result = svc.session_handoff(args["handoff"])
    reset_checkpoint_counter(svc)
    return result


def _do_session_last_handoff(svc: Any, args: dict) -> str:
    ho = svc.session_last_handoff()
    return json.dumps(ho, indent=2, ensure_ascii=False) if ho else "No handoff found."


def _section_with_timeout(label: str, fn: Callable[[], Any], timeout: float = 6.0) -> Any:
    """Run a session_open sub-section under a hard watchdog.

    Each /start sub-call (DB read/write, self_check subprocess) is best-effort.
    Historically they were wrapped only in try/except, so a sub-call that BLOCKS
    rather than raises (a slow/wedged DB write, a self_check subprocess that
    hangs past its own timeout, a pathologically large project) would freeze the
    whole compound RPC — and the IDE sits on "Generating…" forever. This runs the
    sub-call in a daemon thread and joins with `timeout`; on timeout the section
    returns `{"error": "<label> timed out after Ns"}` so /start degrades to a
    visible, self-diagnosing dashboard instead of hanging. The connection is
    opened check_same_thread=False, so cross-thread DB use here is safe.
    """
    box: dict[str, Any] = {}

    def _run() -> None:
        try:
            box["r"] = fn()
        except Exception as e:  # noqa: BLE001 — surfaced as the section's error
            box["e"] = e

    t = threading.Thread(target=_run, name=f"session_open:{label}", daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return {"error": f"{label} timed out after {timeout:g}s (section wedged — /start degraded)"}
    if "e" in box:
        return {"error": str(box["e"])}
    return box.get("r")


# --- session_open envelope projection ---------------------------------------
# session_open is the ONE call /start Phase 1 makes, so every byte it returns is
# paid on every session. Both producers it composes are full-fidelity by design
# (`session_current` returns the whole row, `self_check.collect` returns the whole
# diagnostic), and forwarding them verbatim made the envelope 49 KB — past the
# host's tool-result ceiling, so the compound RPC built to replace five calls
# degraded into a file dump that cost MORE than the five. 90% of that was never
# rendered: 26 KB of module→mtime telemetry the dashboard does not read, plus a
# \u-escaped duplicate of the handoff this same envelope already returns parsed.
# So the envelope PROJECTS both sections down to what /start Phase 3 renders.
# Allowlists, not denylists: a heavy field added upstream later must not silently
# re-inflate this payload.
#
# It is also a data-minimisation boundary. /start runs unattended every session,
# so anything here is shipped to the model transcript automatically. The dropped
# fields are absolute host paths (which carry the developer's directory layout,
# client names included) and machine mtime fingerprints. Full telemetry stays one
# EXPLICIT `tausik_self_check` call away — opt-in diagnostics, minimal by default.
_SESSION_ENVELOPE_KEYS = ("id", "started_at", "ended_at", "model_id", "model_version")
_SELF_CHECK_ENVELOPE_KEYS = (
    "server",
    "pid",
    "startup_time_iso",
    "watched_modules_count",
    "drift_detected",
    "stale_modules",
    "sibling_mcp_count",
    "sibling_mcp_pids",
    "sibling_introspection_error",
    "sibling_warning",
    "remediation",
)
# Kept per stale module: enough to name the culprit and justify "restart your IDE".
# `path` is dropped — it is the absolute host path, and the basename in `module`
# already identifies which module went stale.
_STALE_MODULE_KEYS = ("module", "reason", "delta_seconds")


def _project(section: Any, keys: tuple[str, ...]) -> Any:
    """Narrow a section dict to `keys`. Error sections pass through untouched.

    A section that failed carries only {"error": ...} (see `_section_with_timeout`);
    projecting that to an allowlist would erase the very diagnostic /start needs to
    render a degraded dashboard, so it is returned as-is.
    """
    if not isinstance(section, dict) or "error" in section:
        return section
    return {k: section[k] for k in keys if k in section}


def _project_self_check(section: Any) -> Any:
    """Project the self_check section, including its nested stale_modules entries."""
    out = _project(section, _SELF_CHECK_ENVELOPE_KEYS)
    if not isinstance(out, dict) or "error" in out:
        return out
    stale = out.get("stale_modules")
    if isinstance(stale, list):
        out["stale_modules"] = [_project(m, _STALE_MODULE_KEYS) for m in stale]
    return out


def _handle_session_open(svc: Any, args: dict | None = None) -> str:
    """v14b-session-open-compound-rpc — single envelope for /start Phase 1.

    Replaces 5 sequential MCP calls (session_start + status compact +
    last_handoff + task_list active+blocked + self_check) with one
    round-trip. Each sub-section is best-effort AND watchdog-bounded via
    `_section_with_timeout`: a sub-call that hangs (not just raises) surfaces
    as an "error" key for that section so /start renders a degraded dashboard
    rather than freezing on "Generating…". On self_check.drift_detected the
    agent still falls back to CLI per /start SKILL.md.
    """
    args = args or {}

    # 1. Session — start (idempotent) + current dict snapshot.
    def _session() -> Any:
        svc.session_start()  # text return ignored — we rebuild from session_current
        return svc.session_current()

    session_data = _section_with_timeout("session", _session)

    # 2. Status (compact JSON identical to tausik_status compact:true).
    status_data = _section_with_timeout(
        "status", lambda: json.loads(_handle_status(svc, {"compact": True}))
    )

    # 3. Last handoff (None if absent — caller distinguishes from error).
    handoff = _section_with_timeout("handoff", lambda: svc.session_last_handoff())

    # 4. Active + blocked tasks. Each task slimmed to slug/title/status.
    def _slim(t: dict) -> dict:
        return {"slug": t["slug"], "title": t["title"], "status": t["status"]}

    def _tasks() -> Any:
        return {
            "active": [_slim(t) for t in svc.task_list(status="active")],
            "blocked": [_slim(t) for t in svc.task_list(status="blocked")],
        }

    tasks = _section_with_timeout("tasks", _tasks)
    if isinstance(tasks, dict) and "error" in tasks and "active" not in tasks:
        tasks = {"active": [], "blocked": [], "error": tasks["error"]}

    # 5. Self-check (re-use existing handler — already serialized).
    self_check_data = _section_with_timeout("self_check", lambda: json.loads(_handle_self_check()))

    # 6. Sync suggestion (state-git-triggers): does the tausik/ tree carry state the
    # DB lacks (e.g. after a git pull)? Content-based dry-run; None when there is no
    # tree or no divergence. Best-effort + watchdog-bounded like every section above,
    # and near-zero cost by default (returns None immediately when tausik/ is absent).
    def _sync_suggested() -> Any:
        from state_triggers import import_suggested

        return import_suggested(svc)

    # Budgeted above the 6s default ON PURPOSE: unlike the other sections this one
    # is inherently O(tree) — it reads and parses every projected entity — and 6s
    # was tight enough that the cold first call (the only one /start makes) timed
    # out every session. `prewarm` at MCP startup makes the common case ~1s; this
    # covers the race where a tool call lands before that thread finishes. It does
    # NOT reinstate the hang the watchdog was added for: the bound is still hard,
    # and this section is computed LAST, so every other dashboard signal is already
    # in hand if it does trip.
    sync_suggested = _section_with_timeout("sync_suggested", _sync_suggested, timeout=20.0)

    # Project both full-fidelity sections down to the rendered set. The session row
    # is narrowed AFTER the handoff section is built, so the handoff still ships —
    # once, parsed, under its own key — instead of twice with one copy \u-escaped.
    return json.dumps(
        {
            "session": _project(session_data, _SESSION_ENVELOPE_KEYS),
            "status": status_data,
            "handoff": handoff,
            "tasks": tasks,
            "self_check": _project_self_check(self_check_data),
            "sync_suggested": sync_suggested,
        },
        indent=2,
        ensure_ascii=False,
        default=str,
    )


SESSION_HANDLERS = {
    "tausik_session_current": _do_session_current,
    "tausik_session_list": _do_session_list,
    "tausik_session_start": lambda svc, args: svc.session_start(),
    "tausik_session_end": lambda svc, args: svc.session_end(args.get("summary")),
    "tausik_session_extend": lambda svc, args: svc.session_extend(args.get("minutes", 60)),
    "tausik_session_handoff": _do_session_handoff,
    "tausik_session_last_handoff": _do_session_last_handoff,
    "tausik_session_open": lambda svc, args: _handle_session_open(svc, args),
}
