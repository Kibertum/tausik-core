"""Conformance guard: RENAR SPEC/ADAPT enums have ONE source of truth.

The closed lists SPEC_TYPES / SPEC_STATUSES (service_specs) and ADAPT_STATUSES /
FINDING_CATEGORIES / SIGNATURE_ROLES / LINK_TARGETS (service_adapts) are
mirrored into the argparse layer, the MCP tool-schema layer AND the database
CHECK constraint. Both the parser and the MCP tool modules now DERIVE from the
service constants, so neither can drift.

THE SENTENCE HERE USED TO SAY "the MCP schemas keep literal lists (a JSON
schema should be self-contained)". That stopped being true for `tools_spec` in
session #200 and for `tools_adapt` in #214, and it was a poor rule while it
lasted: a mirror pinned by a test is still a second literal that has to be
edited in lockstep, and ADR-013 moved the standard under exactly such a mirror.
What the tests below pin now is that the derivation HOLDS — the enum a tool
publishes is the service list, not a copy that happens to agree today.

THE DATABASE MIRROR WAS THE ONE NOBODY WATCHED, and it is the one that decides
what the system will actually ACCEPT: a value the Python domain admits and the
CHECK refuses is not a preference, it is an unreachable state. Until v50 the
two agreed by coincidence rather than by control. The inventory that found this
was taken by the LOWEST PRIMITIVE (what enforces the list) rather than by the
convenient constant that names it.
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
from service_adapts import (  # noqa: E402
    ADAPT_STATUSES,
    FINDING_CATEGORIES,
    LINK_TARGETS,
    SIGNATURE_ROLES,
)
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
    # The categories were the one `choices=` list in this file that was still a
    # literal, while the statuses beside them already derived and said so.
    assert ppa.FINDING_CATEGORY_CHOICES == list(FINDING_CATEGORIES)
    assert ppa.SIGNATURE_ROLE_CHOICES == list(SIGNATURE_ROLES)


# --- the database CHECK is pinned to the service source too ---


def _parse_status_domain(ddl: str) -> tuple[str, ...]:
    """Values an ``adapts.status`` CHECK admits, read out of stored DDL.

    PURE, and split from the database on purpose (memory #484): a reader that
    can only be run against a live schema has no expressible green branch —
    handed a string, it can be shown to report a domain that DIFFERS, which is
    what proves the pin below is measuring the substrate and not itself.
    """
    marker = "CHECK(status IN"
    at = ddl.find(marker)
    if at < 0:
        return ()
    chunk = ddl[at + len(marker) : ddl.find("))", at + len(marker))]
    return tuple(p.strip().strip("'\"") for p in chunk.strip(" (\n").split(",") if p.strip())


def _db_status_domain(conn) -> tuple[str, ...]:
    """The same, read from the DDL the database itself stores."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='adapts'"
    ).fetchone()
    assert row and row[0], "adapts table has no stored DDL"
    return _parse_status_domain(str(row[0]))


def test_db_check_constraint_matches_adapt_statuses(tmp_path):
    """The substrate mirror: what the DB ACCEPTS must equal the Python domain.

    Parsed out of the DDL the database itself stores, never out of a Python
    constant — reading the constant back would assert that a value equals
    itself. A divergence here is not cosmetic: before v50 the CHECK refused
    'approved', so a status §13.3.3 REQUIRES could not be written at all.
    """
    from project_backend import SQLiteBackend

    be = SQLiteBackend(str(tmp_path / "enum_pin.db"))
    try:
        domain = _db_status_domain(be._conn)
    finally:
        be.close()
    assert domain == tuple(ADAPT_STATUSES), (
        "the DB CHECK and ADAPT_STATUSES have drifted: the database admits "
        f"{domain} while the service domain is {tuple(ADAPT_STATUSES)}"
    )


def test_db_check_pin_can_see_a_drift():
    """NEGATIVE for the guard itself: the parser must REPORT a real domain.

    A pin whose reader returned the Python constant, or an empty tuple, would
    pass the test above forever. Handed DDL that admits an extra value, the
    parser must say so — that is what makes the green branch above meaningful
    rather than merely asserted.
    """
    ddl = (
        "CREATE TABLE adapts (status TEXT NOT NULL DEFAULT 'draft' "
        "CHECK(status IN ('draft', 'approved', 'bogus')))"
    )
    assert _parse_status_domain(ddl) == ("draft", "approved", "bogus")
    assert _parse_status_domain(ddl) != tuple(ADAPT_STATUSES)


# --- MCP schema literals pinned to the service source ---


@_NEED_MCP
def test_mcp_spec_enums_match_service():
    assert _tools_spec._SPEC_TYPES == list(SPEC_TYPES)
    assert _tools_spec._SPEC_STATUSES == list(SPEC_STATUSES)


@_NEED_MCP
def test_mcp_adapt_enums_match_service():
    assert _tools_adapt._ADAPT_STATUSES == list(ADAPT_STATUSES)
    assert _tools_adapt._FINDING_CATEGORIES == list(FINDING_CATEGORIES)
    assert _tools_adapt._SIGNATURE_ROLES == list(SIGNATURE_ROLES)
    assert _tools_adapt._LINK_TARGETS == list(LINK_TARGETS)


@_NEED_MCP
def test_the_published_adapt_schema_carries_the_service_list_not_a_copy():
    """Equality is a STATE; identity of source is the property.

    Four literal lists sat in that module agreeing with the service layer, and
    the test above would have gone on passing right up to the amendment that
    made them disagree. The enum a tool PUBLISHES is checked here — schema and
    prose alike — because that is what an agent reads.
    """
    finding = next(t for t in _tools_adapt.TOOLS_ADAPT if t["name"] == "tausik_adapt_finding")
    enum = finding["inputSchema"]["properties"]["category"]["enum"]
    assert enum == list(FINDING_CATEGORIES)
    for value in FINDING_CATEGORIES:
        assert value in finding["description"], (
            f"the prose an agent chooses a category from omits {value!r} — it must be "
            "assembled from the list, never written out"
        )
    assert str(len(FINDING_CATEGORIES)) in finding["description"]


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
