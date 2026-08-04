"""Tests for scripts/mcp_tool_scope.py (mcp-scope-tools-exposure).

AC coverage:
  1. active task + non-empty scope_tools → only (declared ∪ safe-core) exposed.
  2. always-safe-core exposed unconditionally when scoping active.
  3. NEGATIVE fail-open: feature off / no active task / undeclared scope_tools /
     resolver error → ALL tools exposed.
  4. NEGATIVE security: hiding is surface-only — the safe-core existence ratchet
     + the "filter never invents/removes a tool's identity" invariant document
     that call_tool/write-gate (the real barrier) are untouched by this module.
  5. token/size measurement: scoped tool-list is strictly smaller for a typical
     scope, recorded as a number.
  6. reconcile with l26-tool-token-cost: filter is a pure list-shaper, orthogonal
     to when the host loads the list (covered by construction; no conflict test
     needed — the module never touches loading).
"""

from __future__ import annotations

import json
import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
_MCP = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
)
if _MCP not in sys.path:
    sys.path.insert(0, _MCP)

import mcp_tool_scope as mts  # noqa: E402
from mcp_tool_scope import (  # noqa: E402
    SAFE_CORE_EXACT,
    expose_tools,
    is_safe_core,
    scoped_tool_names,
)


def _tools(*names: str) -> list[dict]:
    return [
        {"name": n, "description": f"{n} desc", "inputSchema": {"type": "object"}} for n in names
    ]


class _FakeSvc:
    """Minimal service stub — only task_list(status=...) is used."""

    def __init__(self, active: list[dict]):
        self._active = active

    def task_list(self, status=None, **_kw):
        if status == "active":
            return self._active
        return []


def _task(scope_tools):
    raw = None if scope_tools is None else json.dumps(scope_tools)
    return {"slug": "t", "status": "active", "scope_paths": None, "scope_tools": raw}


# ---------------------------------------------------------------- safe-core ---


class TestSafeCore:
    def test_task_and_session_prefixes_are_core(self):
        assert is_safe_core("tausik_task_start")
        assert is_safe_core("tausik_task_done")
        assert is_safe_core("tausik_session_open")

    def test_exact_singletons_are_core(self):
        for n in ("tausik_status", "tausik_verify", "tausik_search", "tausik_doctor"):
            assert is_safe_core(n)

    def test_non_core_is_not_core(self):
        assert not is_safe_core("tausik_epic_delete")
        assert not is_safe_core("tausik_gates_disable")

    def test_safe_core_names_exist_in_real_tools(self):
        """AC4 ratchet: safe-core references real tools; a rename fails here
        loudly instead of silently stranding the agent."""
        from tools import TOOLS

        names = {t["name"] for t in TOOLS}
        missing = SAFE_CORE_EXACT - names
        assert not missing, f"safe-core references non-existent tools: {missing}"
        # each prefix family must match at least one real tool
        for prefix in mts.SAFE_CORE_PREFIXES:
            assert any(n.startswith(prefix) for n in names), f"no tool for prefix {prefix}"


# ------------------------------------------------------------ pure filter ---


class TestScopedToolNames:
    def test_union_of_declared_and_core(self):
        allnames = ["tausik_status", "tausik_epic_add", "tausik_gates_disable", "tausik_task_start"]
        allowed = scoped_tool_names(allnames, {"tausik_epic_add"})
        assert allowed == {"tausik_status", "tausik_epic_add", "tausik_task_start"}
        assert "tausik_gates_disable" not in allowed  # hidden

    def test_declared_but_not_offered_is_dropped(self):
        allowed = scoped_tool_names(["tausik_status"], {"tausik_does_not_exist"})
        assert allowed == {"tausik_status"}  # typo never invents a tool


# --------------------------------------------------------- expose_tools ---


class TestExposeFailOpen:
    def test_feature_off_returns_all(self, monkeypatch):
        monkeypatch.setattr(mts, "_feature_enabled", lambda: False)
        tools = _tools("tausik_status", "tausik_epic_add")
        assert expose_tools(tools, _FakeSvc([_task(["tausik_status"])])) == tools

    def test_no_active_task_returns_all(self, monkeypatch):
        monkeypatch.setattr(mts, "_feature_enabled", lambda: True)
        tools = _tools("tausik_status", "tausik_epic_add")
        assert expose_tools(tools, _FakeSvc([])) == tools

    def test_undeclared_active_task_returns_all(self, monkeypatch):
        """AC3: active task with NULL scope_tools → legacy freedom (all tools)."""
        monkeypatch.setattr(mts, "_feature_enabled", lambda: True)
        tools = _tools("tausik_status", "tausik_epic_add")
        assert expose_tools(tools, _FakeSvc([_task(None)])) == tools

    def test_resolver_error_fails_open(self, monkeypatch):
        monkeypatch.setattr(mts, "_feature_enabled", lambda: True)

        class Boom:
            def task_list(self, **_):
                raise RuntimeError("db down")

        tools = _tools("tausik_status", "tausik_epic_add")
        assert expose_tools(tools, Boom()) == tools

    def test_never_returns_empty(self, monkeypatch):
        """A scope with a tool the server does not offer still yields the
        safe-core, never an empty list."""
        monkeypatch.setattr(mts, "_feature_enabled", lambda: True)
        tools = _tools("tausik_epic_add", "tausik_gates_disable")  # no safe-core present
        out = expose_tools(tools, _FakeSvc([_task(["tausik_epic_add"])]))
        assert out  # non-empty


class TestExposeScoped:
    def test_declared_scope_narrows_to_union_plus_core(self, monkeypatch):
        monkeypatch.setattr(mts, "_feature_enabled", lambda: True)
        tools = _tools(
            "tausik_status",  # core
            "tausik_task_done",  # core (prefix)
            "tausik_epic_add",  # declared
            "tausik_gates_disable",  # hidden
            "tausik_role_delete",  # hidden
        )
        out = {t["name"] for t in expose_tools(tools, _FakeSvc([_task(["tausik_epic_add"])]))}
        assert out == {"tausik_status", "tausik_task_done", "tausik_epic_add"}

    def test_solo_empty_declared_list_restricts_to_core_only(self, monkeypatch):
        """scope_tools='[]' is DECLARED (explicit 'no extra tools') → only the
        safe-core is exposed, NOT legacy freedom. Regression guard for the defect
        where '[]' parsed to the same empty list as NULL and leaked all tools."""
        monkeypatch.setattr(mts, "_feature_enabled", lambda: True)
        tools = _tools("tausik_status", "tausik_epic_add")  # status=core, epic_add=not
        out = {t["name"] for t in expose_tools(tools, _FakeSvc([_task([])]))}
        assert out == {"tausik_status"}  # epic_add hidden — declared [] restricts

    def test_solo_null_scope_is_legacy_freedom(self, monkeypatch):
        """scope_tools NULL (never declared) → ALL tools. The '[]' vs NULL
        distinction must be read from the raw value, not the parsed list."""
        monkeypatch.setattr(mts, "_feature_enabled", lambda: True)
        tools = _tools("tausik_status", "tausik_epic_add")
        assert expose_tools(tools, _FakeSvc([_task(None)])) == tools

    def test_union_across_two_active_tasks(self, monkeypatch):
        monkeypatch.setattr(mts, "_feature_enabled", lambda: True)
        tools = _tools(
            "tausik_status", "tausik_epic_add", "tausik_role_create", "tausik_gates_disable"
        )
        svc = _FakeSvc([_task(["tausik_epic_add"]), _task(["tausik_role_create"])])
        out = {t["name"] for t in expose_tools(tools, svc)}
        assert out == {"tausik_status", "tausik_epic_add", "tausik_role_create"}

    def test_mixed_declared_and_undeclared_restricts_to_declared_union(self, monkeypatch):
        """Symmetric to scope_write_gate: an undeclared co-active task does NOT
        grant legacy freedom once a sibling declared a scope."""
        monkeypatch.setattr(mts, "_feature_enabled", lambda: True)
        tools = _tools("tausik_status", "tausik_epic_add", "tausik_gates_disable")
        svc = _FakeSvc([_task(["tausik_epic_add"]), _task(None)])
        out = {t["name"] for t in expose_tools(tools, svc)}
        assert out == {"tausik_status", "tausik_epic_add"}
        assert "tausik_gates_disable" not in out


# ------------------------------------------------------ AC5 measurement ---


class TestTokenMeasurement:
    def test_scoped_surface_is_strictly_smaller(self, monkeypatch):
        """AC5: record the reduction as a number. Uses the REAL TOOLS list and a
        typical single-file task scope (edit + verify)."""
        monkeypatch.setattr(mts, "_feature_enabled", lambda: True)
        from tools import TOOLS

        # typical scope: a task that only needs task lifecycle + one extra tool.
        svc = _FakeSvc([_task(["tausik_memory_add"])])
        full = TOOLS
        scoped = expose_tools(TOOLS, svc)

        full_bytes = len(json.dumps(full, ensure_ascii=False))
        scoped_bytes = len(json.dumps(scoped, ensure_ascii=False))
        reduction = 1 - scoped_bytes / full_bytes

        assert len(scoped) < len(full), "scoped list must hide some tools"
        assert scoped_bytes < full_bytes
        # A meaningful cut for a typical scope (safe-core is a fraction of 150+).
        assert reduction > 0.3, f"only {reduction:.0%} reduction — expected >30%"
        # Emit the measured numbers so the run records them (AC5).
        print(
            f"\n[AC5] full={len(full)} tools/{full_bytes}B  "
            f"scoped={len(scoped)} tools/{scoped_bytes}B  reduction={reduction:.0%}"
        )
