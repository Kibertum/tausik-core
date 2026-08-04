"""MCP tool-surface scoping — SENAR Rule 2 at the MCP surface itself.

mcp-scope-tools-exposure (borrow onyx). TAUSIK has 150+ MCP tools and tasks
already carry a `scope_tools` ACL (scripts/scope_acl.py) — but that ACL is
enforced only on writes. onyx exposes to the agent not every server tool but a
curated subset. This module does the same: when a task is active and declares a
non-empty `scope_tools`, the MCP server exposes to the agent only the union of
(declared scope_tools ∪ an always-safe core); the rest are hidden from the
tool-list. That narrows both the attack surface and the token cost of the tool
definitions in the system prompt.

Fail-open BY CONSTRUCTION — symmetric to scope_write_gate's legacy freedom
(l26-hook-contract-review). Any of these expose ALL tools:
  - feature flag `mcp.scope_tools_exposure` is off (the default);
  - no task is active;
  - NO active task declared a non-empty scope_tools (legacy freedom — the
    saving must never silently break a project that never opted in);
  - any error while resolving the scope (never raise, never hide on error).

Hiding is a UX / token optimization, NOT the security barrier. A hidden tool
invoked directly still passes the existing scope enforcement (the write-gate and
any call-time checks are untouched); this module only shapes the advertised
tool-list. The gate remains the barrier — see AC4 of the task.

Boundary (documented, not hidden): `list_tools()` computes the scoped set at
call time, so the agent gets the scoped surface whenever the host (re)fetches
the tool-list — i.e. on every server connect with a task already active. Live
re-scoping the *instant* a task starts mid-session would need a
`notifications/tools/list_changed` emit from the (threaded, sync) call_tool
path; that coordination is left to the deferred-loading track
(l26-tool-token-cost). This module and that one are orthogonal: one shapes the
list, the other changes when the host loads it — they do not conflict (AC6).
"""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("tausik.mcp.scope")

# Survival core: tools the agent must never be able to lock itself out of.
# Without these, a narrow scope_tools could strand the agent with no way to
# inspect, switch, close, or verify a task — so they are exposed unconditionally
# whenever scoping is active (AC2). Two families cover the bulk. NOTE: taking the
# whole `tausik_task_*` family for simplicity also always exposes its mutating
# members (task_delete/move/update/unclaim). That is deliberate — lifecycle must
# stay reachable — and hiding is not the barrier for them anyway: those are writes
# that answer to scope_write_gate, which this module does not touch.
SAFE_CORE_PREFIXES = ("tausik_task_", "tausik_session_")
# ...plus these singletons (status / search / verify / housekeeping):
SAFE_CORE_EXACT = frozenset(
    {
        "tausik_status",
        "tausik_health",
        "tausik_doctor",
        "tausik_self_check",
        "tausik_verify",
        "tausik_update_claudemd",
        "tausik_search",
        "tausik_memory_search",
        "tausik_snippet_search",
        "tausik_spec_search",
        "tausik_adapt_search",
    }
)


def is_safe_core(name: str) -> bool:
    """True iff `name` is always exposed regardless of scope_tools."""
    return name in SAFE_CORE_EXACT or name.startswith(SAFE_CORE_PREFIXES)


def scoped_tool_names(all_names: list[str], declared_tools: set[str]) -> set[str]:
    """Names to expose: (declared ∪ always-safe-core), intersected with what the
    server actually offers. Declared names the server does not offer are dropped
    (a typo in scope_tools never invents a tool)."""
    return {n for n in all_names if n in declared_tools or is_safe_core(n)}


def _feature_enabled() -> bool:
    """config `mcp.scope_tools_exposure`, default False (opt-in). Unreadable
    config or any error → disabled (fail-open: expose all tools)."""
    try:
        from project_config import load_config

        node = load_config().get("mcp", {})
        return bool(isinstance(node, dict) and node.get("scope_tools_exposure"))
    except Exception:  # noqa: BLE001 — best-effort: a config error must never hide tools
        return False


def _active_declared_tools(svc: Any) -> set[str] | None:
    """Union of `scope_tools` across active tasks that declared a non-empty one.

    Returns None to signal *legacy freedom* — no active task, or NO active task
    declared a non-empty scope_tools. An empty set is never returned: a task that
    declared `[]` (explicit "no tools") still can't strand itself because the
    safe-core is unioned in by the caller; but such a task counts as *declared*,
    so it does restrict the surface to the safe-core.

    Symmetric to scope_write_gate (l26-hook-contract-review AC3): an undeclared
    co-active task contributes nothing and does not, by itself, nullify a
    sibling's ACL — legacy freedom applies only when nobody declared anything.
    """
    from scope_acl import parse_task_acl

    actives = svc.task_list(status="active")
    declared: set[str] = set()
    any_declared = False
    for task in actives:
        # "Declared" is decided on the RAW DB value, not the parsed list: an
        # explicit `[]` ("no extra tools") and a NULL ("never declared") both parse
        # to an empty list, but only the latter is legacy freedom. scope_write_gate
        # makes the same distinction on `raw is not None`; mirror it here so `[]`
        # restricts the surface to the safe-core instead of silently exposing all.
        raw = task.get("scope_tools")
        if raw is None or raw == "":
            continue  # undeclared — contributes nothing, does not grant freedom
        any_declared = True
        declared.update(parse_task_acl(task)["tools"])
    return declared if any_declared else None


def expose_tools(tools: list[dict], svc: Any) -> list[dict]:
    """Server entry point: the tool dicts to advertise for the current state.

    Fail-open everywhere — never raises, never returns an empty list, never
    hides a tool on error. Only when the feature is on AND some active task
    declared a non-empty scope_tools does this narrow the list to
    (union of declared ∪ safe-core).
    """
    try:
        if not _feature_enabled():
            return tools
        declared = _active_declared_tools(svc)
        if declared is None:  # legacy freedom
            return tools
        allowed = scoped_tool_names([t["name"] for t in tools], declared)
        filtered = [t for t in tools if t["name"] in allowed]
        # Belt-and-suspenders: safe-core guarantees non-empty, but never strand.
        return filtered or tools
    except Exception:  # noqa: BLE001 — fail-open: a scoping error must never hide tools
        _log.warning("mcp tool-scope: failing open (exposing all tools)", exc_info=True)
        return tools
