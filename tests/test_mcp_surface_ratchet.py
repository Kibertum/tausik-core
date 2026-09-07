"""The MCP tool surface is a per-turn tax, and it must not grow unwatched.

The MCP protocol sends every tool's name AND schema on each turn unless the
CLIENT defers schemas. Measured in session #229 on the live tree: 145 tools,
56,108 bytes of serialized definitions (~14,027 tokens). Names alone are 3,201
bytes (~800 tokens) — a 17.5x difference between a host that defers and one that
does not. Claude Code defers (observed here: tools arrive as names, schemas
fetched on demand); a host without deferral pays the whole surface before a
single useful call is made.

WHY A TEST AND NOT A LINE IN A DOCUMENT. The task that filed this recorded 117
tools and 44,501 bytes in session #178. By #229 it was 145 and 56,108 — the
surface grew 24% and 26% and nobody noticed, because the number lived in prose.
That is the argument for this file in one sentence: a number a document states
rots, a number a test re-measures cannot.

WHAT THIS DOES NOT DO. It does not shrink the surface. Every one of the 145
declared tools has a handler (asserted below), so there is no free reduction —
cutting the surface means dropping a live capability, merging families, or
splitting the server by area, and all three change the contract for consumers
and interact with `mcp-tools-list-caching-conflicts-with-scope-hiding`. That is
a product decision, not a chore this ratchet may make silently.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

#: Measuring the surface means importing the server's module tree, and this file
#: walks it — so a change anywhere under the MCP package can turn it red.
CROSSCUTTING_SCOPE = ["harness/claude/mcp/project/", "tausik/gates.json"]

_REPO = Path(__file__).resolve().parents[1]
_MCP = _REPO / "harness" / "claude" / "mcp" / "project"

#: Import the surface in a SUBPROCESS. The server package needs `scripts/` and
#: its own directory on sys.path, and importing it into the test interpreter
#: would leave those there for every test that runs afterwards — the same
#: order-dependence that hid a broken hook import for months (memory #645).
_PROBE = """
import json, sys
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[2])
import tools
items = tools.TOOLS if isinstance(tools.TOOLS, list) else list(tools.TOOLS.values())
import handlers
dispatch = None
for attr in dir(handlers):
    v = getattr(handlers, attr)
    if isinstance(v, dict) and any(str(k).startswith("tausik_") for k in v):
        dispatch = v
        break
print(json.dumps({
    "count": len(items),
    "bytes": len(json.dumps(items, ensure_ascii=False).encode("utf-8")),
    "names_bytes": len(json.dumps([x.get("name") for x in items], ensure_ascii=False).encode("utf-8")),
    "declared": sorted(x.get("name") for x in items),
    "dispatched": sorted(dispatch or {}),
}))
"""


def _measure() -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE, str(_REPO / "scripts"), str(_MCP)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(_REPO),
        timeout=120,
    )
    if proc.returncode != 0:
        pytest.fail(f"could not measure the MCP surface:\n{proc.stderr.strip()[-600:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _baseline() -> dict:
    gates = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
    section = gates.get("mcp_surface")
    assert section is not None, (
        "tausik/gates.json has no `mcp_surface` section. A missing baseline must not "
        "silently disable the ratchet — that is how an unwatched number grows."
    )
    return section


def check_surface(measured: dict, baseline: dict) -> tuple[bool, str]:
    """(ok, message). Pure, so the negative case can be exercised without editing
    the repo's own baseline — a guard nobody has watched fail is not evidence."""
    problems = []
    if measured["count"] > baseline["max_tools"]:
        problems.append(f"tool count {measured['count']} exceeds baseline {baseline['max_tools']}")
    if measured["bytes"] > baseline["max_bytes"]:
        problems.append(
            f"serialized surface {measured['bytes']:,} bytes exceeds baseline "
            f"{baseline['max_bytes']:,}"
        )
    if not problems:
        return True, "surface within baseline"
    return False, (
        "MCP surface GREW — every added tool is paid for on every turn by hosts that do "
        "not defer schemas: " + "; ".join(problems) + ". Shrink the surface, or argue the "
        "raise and move the baseline deliberately."
    )


class TestTheSurfaceDoesNotGrowUnwatched:
    def test_surface_is_within_the_baseline(self):
        ok, message = check_surface(_measure(), _baseline())
        assert ok, message

    def test_the_ratchet_goes_red_when_the_surface_grows(self):
        """The negative side, on a baseline lowered by one rather than on hope."""
        measured = _measure()
        tightened = {
            "max_tools": measured["count"] - 1,
            "max_bytes": measured["bytes"] - 1,
        }
        ok, message = check_surface(measured, tightened)
        assert not ok
        assert "tool count" in message
        assert "serialized surface" in message

    def test_a_shrunk_surface_passes_and_is_not_forced_to_match(self):
        """A ratchet permits shrinking; only growth is refused."""
        measured = _measure()
        loose = {"max_tools": measured["count"] + 10, "max_bytes": measured["bytes"] + 10_000}
        ok, _ = check_surface(measured, loose)
        assert ok

    def test_a_missing_baseline_is_an_error_not_a_silent_pass(self):
        gates = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
        assert "mcp_surface" in gates
        assert isinstance(gates["mcp_surface"].get("max_tools"), int)
        assert isinstance(gates["mcp_surface"].get("max_bytes"), int)


class TestEveryDeclaredToolIsReachable:
    """No free reduction exists — and that is a measurement, not an assumption."""

    def test_declared_and_dispatched_are_the_same_set(self):
        measured = _measure()
        declared = set(measured["declared"])
        dispatched = set(measured["dispatched"])
        assert declared - dispatched == set(), (
            f"declared but unreachable: {sorted(declared - dispatched)} — a tool the "
            "protocol advertises and the server cannot run is a per-turn cost with no "
            "capability behind it."
        )
        assert dispatched - declared == set(), (
            f"dispatched but undeclared: {sorted(dispatched - declared)} — a handler no "
            "client can reach."
        )


class TestTheTwoHostPricesAreBothNamed:
    """Promise 2 is about ANY host, and the two hosts differ by 17.5x here."""

    def test_names_only_is_far_cheaper_than_the_full_surface(self):
        measured = _measure()
        assert measured["names_bytes"] < measured["bytes"]
        ratio = measured["bytes"] / measured["names_bytes"]
        assert ratio > 5, (
            "the deferred-schema saving collapsed to under 5x; the two host prices are "
            "no longer far apart and the documented 17.5x is stale"
        )

    def test_the_host_note_states_which_price_was_observed(self):
        note = _baseline().get("_host_note", "")
        assert "observed" in note and "not observed" in note, (
            "the baseline must say which of the two figures was MEASURED here and which "
            "follows from the protocol — presenting a derived number as a measured one "
            "is the defect this release exists to stop (convention #325)."
        )
