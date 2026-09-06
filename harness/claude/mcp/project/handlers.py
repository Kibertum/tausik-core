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
import threading
from typing import Any, Callable

# Ensure scripts dir is in path (once, at import time)
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import handlers_adapt as _adapt  # noqa: E402 — path must be set first
import handlers_actz as _actz  # noqa: E402 — path must be set first
import handlers_at as _at  # noqa: E402 — path must be set first
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


# ONE TOOL CALL AT A TIME. The server runs every call on its own thread
# (`asyncio.to_thread(handle_tool, ...)`) over ONE process-wide ProjectService
# whose connection is opened `check_same_thread=False`. That means two
# overlapping calls share the connection, the open transaction, and the single
# `_in_tx` flag every write consults. Measured, both directions, in
# tests/test_concurrent_dispatch_shares_a_transaction.py: a second call's
# `commit_tx` makes the first call's half-written change durable, and a second
# call's plain write joins the first call's transaction and disappears with its
# rollback. Neither raises: the losing call is told it succeeded.
#
# RLock, not Lock: `handle_tool` is re-entered by nothing today, but a handler
# that dispatches a second tool by name would deadlock on a plain Lock, and
# that is a silent hang rather than an error.
#
# WHY HERE AND NOT DEEPER, since two other placements were weighed:
#   * inside `SQLiteBackend.transaction()` -- REJECTED, it does not cover the
#     defect. The measured second case never calls `transaction()` at all: it
#     is a plain `epic_add`, and `_ex` commits only when `_in_tx` is False, so
#     it silently joins whatever transaction is open. A lock the losing path
#     never takes is not a fix.
#   * a connection per thread -- REJECTED as a rewrite of the DB access model
#     for a defect whose whole measured surface is this one dispatch path, and
#     it would trade this bug for cross-connection SQLite write contention.
# Serialising the WHOLE call also covers the bare-write case above, which is
# why it beats any per-write lock further down.
#
# THE PRICE, MEASURED RATHER THAN GUESSED. The lock itself is free: an
# uncontended acquire+release is 0.13 us against ~5300 us for one real
# `tausik_status` dispatch — 1/40000th of a call, below the run-to-run variance
# of the benchmark that produced both numbers (2000 calls each way).
#
# What actually costs is the SERIALISATION, and only when calls contend:
# `_task_done_report` holds its transaction across a full gate pass, so a
# concurrent tool call waits that long. That is the honest cost of one shared
# connection, and a wait is what the silent data loss above is being traded
# for. Non-MCP threads are NOT covered and do not need to be today: the only
# other threads in the server are the state-prewarm daemon, which never writes,
# and the session_open watchdog, whose sections open no transaction.
_DISPATCH_LOCK = threading.RLock()


def handle_tool(svc: Any, name: str, args: dict) -> str:
    """Dispatch tool call to service method. Returns text result."""
    with _DISPATCH_LOCK:
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
    _actz.ACTZ_HANDLERS,
    _at.AT_HANDLERS,
):
    _DISPATCH.update(_domain)


def _dispatch_tool(svc: Any, name: str, args: dict) -> str:
    """Internal dispatch — called by handle_tool wrapper."""
    handler = _DISPATCH.get(name)
    if handler:
        return handler(svc, args)
    return f"Unknown tool: {name}"
