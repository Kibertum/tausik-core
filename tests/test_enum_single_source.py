"""Conformance guard: RENAR SPEC/ADAPT enums have ONE source of truth.

The closed lists SPEC_TYPES / SPEC_STATUSES (service_specs) and ADAPT_STATUSES
(service_adapts) are mirrored into the argparse layer and the MCP tool-schema
layer (claude + cursor). The parser now derives from the service constants, so
it cannot drift. The MCP schemas keep literal lists (a JSON schema should be
self-contained) — these tests pin those literals to the service source so any
divergence fails CI instead of shipping silently.
"""

from __future__ import annotations

import filecmp
import importlib.util
import os
import sys

import pytest

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "scripts"))

import project_parser_adapts as ppa  # noqa: E402
import project_parser_specs as pps  # noqa: E402
from service_adapts import ADAPT_STATUSES  # noqa: E402
from service_specs import SPEC_STATUSES, SPEC_TYPES  # noqa: E402

_MCP = os.path.join(REPO, "harness", "claude", "mcp", "project")
_MCP_CURSOR = os.path.join(REPO, "harness", "cursor", "mcp", "project")


def _load(path: str, name: str):
    """Load an MCP tools module by path; return None if the file is absent.

    Returning None (rather than raising) keeps a missing harness mirror from
    failing collection of the whole module — the MCP tests skip instead.
    """
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_tools_spec = _load(os.path.join(_MCP, "tools_spec.py"), "_mcp_tools_spec")
_tools_adapt = _load(os.path.join(_MCP, "tools_adapt.py"), "_mcp_tools_adapt")

_NEED_MCP = pytest.mark.skipif(
    _tools_spec is None or _tools_adapt is None,
    reason="MCP harness tools_spec/tools_adapt not present in this checkout",
)


# --- parser layer derives from service (cannot drift) ---


def test_parser_spec_choices_derive_from_service():
    assert pps.SPEC_TYPE_CHOICES == list(SPEC_TYPES)
    assert pps.SPEC_STATUS_CHOICES == list(SPEC_STATUSES)


def test_parser_adapt_choices_derive_from_service():
    assert ppa.ADAPT_STATUS_CHOICES == list(ADAPT_STATUSES)


# --- MCP schema literals pinned to the service source ---


@_NEED_MCP
def test_mcp_spec_enums_match_service():
    assert _tools_spec._SPEC_TYPES == list(SPEC_TYPES)
    assert _tools_spec._SPEC_STATUSES == list(SPEC_STATUSES)


@_NEED_MCP
def test_mcp_adapt_enums_match_service():
    assert _tools_adapt._ADAPT_STATUSES == list(ADAPT_STATUSES)


# --- the two IDE mirrors must stay byte-identical ---


@_NEED_MCP
def test_mcp_mirrors_identical():
    for fname in ("tools_spec.py", "tools_adapt.py"):
        claude = os.path.join(_MCP, fname)
        cursor = os.path.join(_MCP_CURSOR, fname)
        if not (os.path.isfile(claude) and os.path.isfile(cursor)):
            pytest.skip(f"MCP mirror {fname} not present in this checkout")
        assert filecmp.cmp(claude, cursor, shallow=False), (
            f"MCP mirror drift: {fname} differs between claude and cursor"
        )
