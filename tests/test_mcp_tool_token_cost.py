"""Token-cost measurement + ratchets for the MCP tool definitions (l26-tool-token-cost).

TAUSIK ships its tools over MCP; every tool's name + description + inputSchema is
loaded into the host system prompt (or, under Claude Code deferred loading /
ENABLE_TOOL_SEARCH, its name eagerly and its description on demand, truncated to
2 KB each). This module pins the current cost as a regression guard and enforces
the two properties deferred loading depends on:
  - AC3: no single description exceeds the 2 KB the host keeps — a longer one is
    silently truncated, so the tail would never reach the agent.
  - AC4: names are unique and carry a searchable domain token — the name is all
    the agent sees before fetching the description, so an opaque or colliding
    name defeats name-based dispatch (the SkillResolve-Bench failure).

AC2 (deferred loading actually covers TAUSIK) is confirmed empirically: this very
session loads TAUSIK MCP tools by name through ToolSearch before calling them.
Here we assert the mechanism's precondition — every tool has a non-empty name.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import sys

_HARNESS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp")
)

# Claude Code truncates each MCP tool description to 2 KB under deferred loading.
DEFERRED_LOAD_DESC_LIMIT = 2048
# Regression ceiling for the whole authored surface (bytes of the tool-defs JSON).
# Current measured cost is ~51 KB; a careless doubling should redden CI.
TOTAL_SURFACE_CEILING_BYTES = 65_536

# Domain vocabulary a searchable tool name is expected to contain at least one of.
_DOMAIN_TOKENS = (
    "task",
    "session",
    "status",
    "health",
    "doctor",
    "verify",
    "search",
    "memory",
    "spec",
    "adapt",
    "epic",
    "story",
    "gate",
    "role",
    "skill",
    "stack",
    "metric",
    "explore",
    "audit",
    "dead",
    "decide",
    "decision",
    "reason",
    "event",
    "team",
    "snippet",
    "roadmap",
    "cq",
    "claudemd",
    "self_check",
    "usage",
    "brain",
    "draft",
    "fts",
    "optimize",
    "config",
    "graph",
)


@contextlib.contextmanager
def _isolated_import(pkg_dirs):
    """Make `pkg_dirs` importable for one load, then fully undo it.

    tools.py pulls sibling modules (`tools_extra`, brain handlers) by bare name.
    Leaving the harness dirs on sys.path — or their modules in sys.modules — would
    shadow the `.claude`/other-test copies of `handlers`/`tools_extra` and break a
    sibling MCP test under random ordering. So we restore sys.path and purge every
    module imported during the load.
    """
    added = [d for d in pkg_dirs if d not in sys.path]
    before = set(sys.modules)
    for d in added:
        sys.path.insert(0, d)
    try:
        yield
    finally:
        for d in added:
            with contextlib.suppress(ValueError):
                sys.path.remove(d)
        for name in set(sys.modules) - before:
            del sys.modules[name]


def _load_tools(rel_path: str, mod_name: str, pkg_dir: str) -> list[dict]:
    path = os.path.join(_HARNESS, rel_path)
    with _isolated_import([pkg_dir]):
        spec = importlib.util.spec_from_file_location(mod_name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return list(module.TOOLS)


def _all_tools() -> list[dict]:
    return _load_tools(
        "project/tools.py", "_ptools", os.path.join(_HARNESS, "project")
    ) + _load_tools("brain/tools.py", "_btools", os.path.join(_HARNESS, "brain"))


# ---------------------------------------------------------------- AC1: measure ---


def test_total_surface_cost_is_measured_and_bounded(capsys):
    tools = _all_tools()
    total_bytes = len(json.dumps(tools, ensure_ascii=False).encode("utf-8"))
    est_tokens = total_bytes // 4  # documented heuristic; no LLM tokenizer (stdlib-first)
    with capsys.disabled():
        print(
            f"\n[l26-tool-token-cost] {len(tools)} MCP tools, "
            f"{total_bytes} bytes, ~{est_tokens} est. tokens (bytes/4)"
        )
    assert total_bytes < TOTAL_SURFACE_CEILING_BYTES, (
        f"tool surface grew to {total_bytes}B (ceiling {TOTAL_SURFACE_CEILING_BYTES}B) — "
        "trim descriptions or raise the ceiling deliberately"
    )


# ------------------------------------------------- AC3: 2 KB deferred-load limit ---


def test_no_description_exceeds_deferred_load_limit():
    offenders = [
        (t["name"], len(t["description"].encode("utf-8")))
        for t in _all_tools()
        if len(t.get("description", "").encode("utf-8")) > DEFERRED_LOAD_DESC_LIMIT
    ]
    assert not offenders, (
        f"{len(offenders)} description(s) over {DEFERRED_LOAD_DESC_LIMIT}B would be "
        f"truncated by the host, hiding the tail: {offenders}"
    )


# --------------------------------------- AC2: deferred loading keys on the name ---


def test_every_tool_has_a_nonempty_name():
    for t in _all_tools():
        assert t.get("name"), f"tool without a name cannot be found by search: {t}"
        assert isinstance(t["name"], str)


# ------------------------------------------- AC4: names unique + searchable ---


def test_tool_names_are_unique():
    names = [t["name"] for t in _all_tools()]
    dupes = {n for n in names if names.count(n) > 1}
    assert not dupes, f"duplicate tool names defeat name-based dispatch: {dupes}"


def test_every_name_carries_a_searchable_domain_token():
    """Guards against opaque names (the SkillResolve-Bench failure at scale): the
    name alone must hint at the tool's domain, since that is all the agent sees
    before fetching the description."""
    opaque = [
        t["name"] for t in _all_tools() if not any(tok in t["name"] for tok in _DOMAIN_TOKENS)
    ]
    assert not opaque, f"names with no searchable domain token: {opaque}"


def test_representative_intents_resolve_to_the_right_tool():
    """A small intent→name sample: the expected tool exists and its name contains
    the intent keyword, so a name-only search would surface it."""
    names = {t["name"] for t in _all_tools()}
    samples = {
        "start": "tausik_task_start",
        "verify": "tausik_verify",
        "status": "tausik_status",
        "search": "tausik_search",
        "session": "tausik_session_open",
    }
    for keyword, expected in samples.items():
        assert expected in names, f"expected tool {expected} missing"
        assert keyword in expected
