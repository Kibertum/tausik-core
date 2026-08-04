"""TAUSIK MCP handlers — dispatch tool calls to ProjectService.

This module owns the DISPATCH, not the handlers. It used to own both: 1345
lines and 77 handler functions covering every domain the framework has, which
is why it needed a named exemption from the file-size gate to stay green.
mcp-handlers-god-module-split cut it along the section comments it already
carried — the boundaries were documented here long before they were enforced.

Each domain module owns its handlers AND the slice of the dispatch table that
names them, exported as `<DOMAIN>_HANDLERS` and merged below. That convention
was already in place for handlers_spec.py / handlers_adapt.py / handlers_skill.py;
the split extended it to the rest rather than inventing a second pattern.

What stays here is what is genuinely about dispatch: the tool-call counter, the
`handle_tool` entry point, the merged table, and the three small surfaces
(exploration, audit, FTS maintenance) that are one handler each and have no
domain to be the second member of.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable

# Ensure scripts dir is in path (once, at import time)
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import handlers_adapt as _adapt  # noqa: E402 — path must be set first
import handlers_cq as _cq  # noqa: E402
import handlers_hierarchy as _hierarchy  # noqa: E402
import handlers_knowledge as _knowledge  # noqa: E402
import handlers_role as _role  # noqa: E402
import handlers_session as _session  # noqa: E402
import handlers_skill as _skill  # noqa: E402 — skill + maintenance handlers
import handlers_spec as _spec  # noqa: E402
import handlers_stack as _stack  # noqa: E402
import handlers_status as _status  # noqa: E402
import handlers_task as _task  # noqa: E402
import handlers_verification as _verification  # noqa: E402


_CHECKPOINT_THRESHOLD = 40

# Type alias for dispatch handlers: (svc, args) -> str
_Handler = Callable[[Any, dict], str]


def _increment_tool_counter(svc: Any) -> str:
    """Increment tool call counter atomically. Returns warning if threshold reached."""
    try:
        # Atomic increment via backend public API
        svc.be.meta_increment("tool_call_count")
        val = svc.be.meta_get("tool_call_count") or "0"
        count = int(val)
        if count == _CHECKPOINT_THRESHOLD:
            return (
                f"\n⚠ SENAR Rule 9.3: {count} tool calls since last checkpoint. "
                f"Consider /checkpoint to save context."
            )
        if count > _CHECKPOINT_THRESHOLD and count % 10 == 0:
            return f"\n⚠ SENAR Rule 9.3: {count} tool calls! /checkpoint overdue."
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        import logging

        logging.getLogger("tausik.counter").debug("tool counter error: %s", e)
    return ""


def handle_tool(svc: Any, name: str, args: dict) -> str:
    """Dispatch tool call to service method. Returns text result."""
    # SENAR Rule 9.3: track tool call count for checkpoint reminder
    checkpoint_warning = _increment_tool_counter(svc)
    result = _dispatch_tool(svc, name, args)
    return result + checkpoint_warning if checkpoint_warning else result


# ---------------------------------------------------------------------------
# Single-handler surfaces — no domain module of their own to belong to
# ---------------------------------------------------------------------------


def _do_explore_current(svc: Any, args: dict) -> str:
    exp = svc.exploration_current()
    if not exp:
        return "No active exploration."
    elapsed = "?"
    if exp.get("started_at"):
        from datetime import datetime, timezone

        try:
            started = datetime.fromisoformat(exp["started_at"].replace("Z", "+00:00"))
            elapsed = str(int((datetime.now(timezone.utc) - started).total_seconds() / 60))
        except (ValueError, TypeError):
            pass
    limit = exp.get("time_limit_min", 30)
    return f"Exploration: {exp['title']} ({elapsed}/{limit} min)"


def _do_audit_check(svc: Any, args: dict) -> str:
    result = svc.audit_check()
    return result or "Audit is up to date."


def _do_fts_optimize(svc: Any, args: dict) -> str:
    results = svc.fts_optimize()
    return "\n".join(f"{t}: {s}" for t, s in results.items())


# ---------------------------------------------------------------------------
# Dispatch table: tool name -> handler(svc, args)
# ---------------------------------------------------------------------------

_DISPATCH: dict[str, _Handler] = {
    # --- Exploration ---
    "tausik_explore_start": lambda svc, args: svc.exploration_start(
        args["title"], args.get("time_limit", 30)
    ),
    "tausik_explore_end": lambda svc, args: svc.exploration_end(
        args.get("summary"), args.get("create_task", False)
    ),
    "tausik_explore_current": _do_explore_current,
    # --- Audit ---
    "tausik_audit_check": _do_audit_check,
    "tausik_audit_mark": lambda svc, args: svc.audit_mark(),
    # --- Skills (handlers in handlers_skill.py) ---
    "tausik_skill_list": lambda svc, args: _skill.handle_skill_list(),
    "tausik_skill_activate": lambda svc, args: _skill.handle_skill_activate(svc, args["name"]),
    "tausik_skill_deactivate": lambda svc, args: _skill.handle_skill_deactivate(svc, args["name"]),
    "tausik_skill_install": lambda svc, args: _skill.handle_skill_install(args["name"]),
    "tausik_skill_uninstall": lambda svc, args: _skill.handle_skill_uninstall(args["name"]),
    "tausik_skill_repo_add": lambda svc, args: _skill.handle_skill_repo_add(
        args["url"], force=bool(args.get("force"))
    ),
    "tausik_skill_repo_remove": lambda svc, args: _skill.handle_skill_repo_remove(args["name"]),
    "tausik_skill_repo_list": lambda svc, args: _skill.handle_skill_repo_list(),
    "tausik_skill_catalog": lambda svc, args: _skill.handle_skill_catalog(
        repo_name=args.get("repo"),
        as_json=bool(args.get("as_json", False)),
    ),
    # --- Maintenance (handler in handlers_skill.py) ---
    "tausik_update_claudemd": lambda svc, args: _skill.handle_update_claudemd(svc),
    "tausik_fts_optimize": _do_fts_optimize,
}

# Domain modules, each owning its handlers and the slice of the table naming
# them. Merged rather than re-declared here so adding a tool touches ONE file:
# the domain it belongs to. A name collision between two domains would be
# silently won by the last merge, which is what tests/test_mcp_dispatch_surface.py
# exists to refuse.
for _domain in (
    _task.TASK_HANDLERS,
    _session.SESSION_HANDLERS,
    _status.STATUS_HANDLERS,
    _knowledge.KNOWLEDGE_HANDLERS,
    _hierarchy.HIERARCHY_HANDLERS,
    _stack.STACK_HANDLERS,
    _role.ROLE_HANDLERS,
    _verification.VERIFICATION_HANDLERS,
    _cq.CQ_HANDLERS,
    _spec.SPEC_HANDLERS,
    _adapt.ADAPT_HANDLERS,
):
    _DISPATCH.update(_domain)


def _dispatch_tool(svc: Any, name: str, args: dict) -> str:
    """Internal dispatch — called by handle_tool wrapper."""
    handler = _DISPATCH.get(name)
    if handler:
        return handler(svc, args)
    return f"Unknown tool: {name}"
