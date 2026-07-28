"""mcp-handlers-god-module-split — the MCP surface survives the split intact.

handlers.py used to declare all 77 handlers and one dispatch table in a single
1345-line module. It now merges a `<DOMAIN>_HANDLERS` dict from each domain
module. That refactor is only safe if two things hold, and neither is visible
by reading a diff:

  * every tool the schema declares still resolves to a handler, and no handler
    exists for a tool the schema never declares — a tool lost in the move would
    surface to the agent as "Unknown tool: ..." at call time, not at import;
  * no two domain modules claim the same tool name. `dict.update` resolves a
    collision silently in favour of whichever merged last, so a duplicated name
    would route to an arbitrary one of two handlers with no error anywhere.

Both are asserted against the SCHEMA (tools*.py), not against a hardcoded
count — a count would have to be edited every time a tool is added, and an
assertion you have to edit to keep green stops being an assertion.
"""

from __future__ import annotations

import os
import sys

import pytest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
_MCP_PROJECT = os.path.join(_REPO_ROOT, "harness", "claude", "mcp", "project")
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
sys.path.insert(0, _MCP_PROJECT)

import handlers  # noqa: E402
import handlers_cq  # noqa: E402
import handlers_hierarchy  # noqa: E402
import handlers_knowledge  # noqa: E402
import handlers_role  # noqa: E402
import handlers_session  # noqa: E402
import handlers_stack  # noqa: E402
import handlers_status  # noqa: E402
import handlers_task  # noqa: E402
import handlers_verification  # noqa: E402

# Every module that contributes a slice of the dispatch table, paired with the
# attribute holding it. Kept explicit so a new domain module that nobody merged
# fails this list rather than passing unnoticed.
_DOMAIN_TABLES = [
    (handlers_task, "TASK_HANDLERS"),
    (handlers_session, "SESSION_HANDLERS"),
    (handlers_status, "STATUS_HANDLERS"),
    (handlers_knowledge, "KNOWLEDGE_HANDLERS"),
    (handlers_hierarchy, "HIERARCHY_HANDLERS"),
    (handlers_stack, "STACK_HANDLERS"),
    (handlers_role, "ROLE_HANDLERS"),
    (handlers_verification, "VERIFICATION_HANDLERS"),
    (handlers_cq, "CQ_HANDLERS"),
]


def _declared_tool_names() -> set[str]:
    """Tool names the MCP schema declares, across every tools*.py in the package."""
    names: set[str] = set()
    for fname in sorted(os.listdir(_MCP_PROJECT)):
        if not (fname == "tools.py" or fname.startswith("tools_")):
            continue
        mod = __import__(fname[:-3])
        for attr in dir(mod):
            value = getattr(mod, attr)
            if not isinstance(value, list):
                continue
            for entry in value:
                if isinstance(entry, dict) and isinstance(entry.get("name"), str):
                    names.add(entry["name"])
    return names


def test_every_declared_tool_has_a_handler():
    declared = _declared_tool_names()
    assert declared, "no tool schemas found — the discovery above is broken, not the dispatch"

    missing = sorted(declared - set(handlers._DISPATCH))
    assert not missing, f"declared but unroutable (agent would get 'Unknown tool'): {missing}"


def test_no_handler_routes_a_tool_the_schema_never_declares():
    """A handler with no schema entry is dead weight the agent can never reach."""
    orphaned = sorted(set(handlers._DISPATCH) - _declared_tool_names())
    assert not orphaned, f"routed but undeclared: {orphaned}"


def test_no_two_domain_modules_claim_the_same_tool():
    """dict.update would resolve a collision silently — refuse it here instead."""
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for mod, attr in _DOMAIN_TABLES:
        for name in getattr(mod, attr):
            if name in seen:
                collisions.append(f"{name}: {seen[name]} and {mod.__name__}")
            else:
                seen[name] = mod.__name__
    assert not collisions, f"tool claimed by two domains: {collisions}"


@pytest.mark.parametrize("mod,attr", _DOMAIN_TABLES, ids=[m.__name__ for m, _ in _DOMAIN_TABLES])
def test_every_domain_table_is_merged_into_dispatch(mod, attr):
    """A domain module nobody merged is invisible: its tools just never resolve."""
    table = getattr(mod, attr)
    assert table, f"{mod.__name__}.{attr} is empty"
    unmerged = sorted(set(table) - set(handlers._DISPATCH))
    assert not unmerged, f"{mod.__name__} declares handlers that _DISPATCH never got: {unmerged}"


def test_every_dispatch_entry_is_callable_with_the_two_arg_contract():
    """The table is heterogeneous (bare functions and lambdas) — pin the shape."""
    import inspect

    bad = []
    for name, fn in handlers._DISPATCH.items():
        if not callable(fn):
            bad.append(f"{name}: not callable")
            continue
        params = inspect.signature(fn).parameters
        if len(params) != 2:
            bad.append(f"{name}: takes {len(params)} args, dispatch passes 2")
    assert not bad, bad
