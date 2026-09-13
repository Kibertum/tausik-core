"""The memory routing table bootstrap lays into EVERY project names every store (GitLab #6).

The block is a ROUTING table: the agent decides from it where a piece of
knowledge goes, and a store absent from the table is never chosen. The 1.8
template named two stores under a heading that said "two systems" while the
framework had three — the shared knowledge store, 1.8's headline feature,
was missing from the one document every agent reads as law. So knowledge true
outside the project (a library's gotcha, a platform habit) went into project
memory and stayed there, while the shared store filled only where an agent had
read the release notes instead of the file generated for it.

The count is not restated: it is derived from the code — one project store,
the shared store iff `memory add --global` exists, the host's auto-memory iff
the framework knows foreign sinks — so the shared route vanishing from the
parser, or the sinks list emptying, turns this red instead of ageing the table
silently. What it does NOT guard: a destination reachable by some other command
than `memory add` (the publish-only brain path decision #221 once named) — that
one would need its own row and its own line here.
"""

from __future__ import annotations

import os
import re
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (os.path.join(_ROOT, "bootstrap"), os.path.join(_ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bootstrap_templates as bt  # noqa: E402
import bootstrap_templates_tiers as bt_tiers  # noqa: E402

CROSSCUTTING_SCOPE = ["bootstrap/bootstrap_templates.py"]

_STORE_NAMES = ("Project memory", "Shared knowledge", "Agent auto-memory")


def _table_rows(text: str) -> list[str]:
    """The `| **Name** …` rows of the memory table — one per store."""
    section = text.split("## Memory (", 1)[1].split("\n## ", 1)[0]
    return [ln for ln in section.splitlines() if re.match(r"\|\s*\*\*", ln)]


def _routes_the_code_has() -> int:
    from memory_sinks import DEFAULT_SINKS
    from project_parser import build_parser

    parser = build_parser()
    memory = {a.dest: a for a in parser._actions if hasattr(a, "choices") and a.choices}["command"]
    add = [a for a in memory.choices["memory"]._actions if hasattr(a, "choices") and a.choices][0]
    add_flags = {opt for a in add.choices["add"]._actions for opt in a.option_strings}
    shared = 1 if "--global" in add_flags else 0
    host = 1 if DEFAULT_SINKS else 0
    return 1 + shared + host


class TestTheTableNamesEveryStore:
    def test_the_three_stores_and_their_criteria_are_named(self):
        rows = _table_rows(bt.MEMORY)
        assert [re.search(r"\*\*(.+?)\*\*", r).group(1) for r in rows] == list(_STORE_NAMES)
        assert "`memory add --global`" in bt.MEMORY, "the shared store must say how to reach it"
        assert "Shared knowledge — from other projects" in bt.MEMORY, (
            "the store must be named as the reader sees it come back"
        )
        for criterion in (
            "Here it is done this way",
            "The tool is built this way",
            "This is how I like to work",
        ):
            assert criterion in bt.MEMORY, f"the litmus for a store is missing: {criterion}"

    def test_the_row_count_is_the_number_of_routes_the_code_has(self):
        """NEGATIVE: the table cannot age silently — its size is checked against the code."""
        assert len(_table_rows(bt.MEMORY)) == _routes_the_code_has() == 3

    def test_the_heading_states_no_count(self):
        """A number in a heading ages at the first addition; a stance does not."""
        heading = bt.MEMORY.splitlines()[0]
        assert not re.search(r"\b(two|three|\d+) (systems|stores)\b", heading), heading
        assert "what the fact is about" in heading

    def test_the_litmus_names_both_branches(self):
        """The one 'hard' sentence an agent obeys literally must route to BOTH stores."""
        litmus = bt.MEMORY.split("**Routing litmus (hard).**", 1)[1]
        assert "`memory add`" in litmus and "`memory add --global`" in litmus
        assert "--global" in bt_tiers.MINIMAL_MEMORY.split("**Routing litmus:**", 1)[1]

    def test_the_shared_store_is_named_as_it_is_read_back(self):
        """The heading the block INJECTS into CLAUDE.md is the one the table names."""
        src = open(
            os.path.join(_ROOT, "scripts", "service_knowledge_aggregates.py"), encoding="utf-8"
        ).read()
        assert "Shared knowledge — from other projects" in src


@pytest.mark.parametrize("tier", ["standard", "minimal"])
@pytest.mark.parametrize(
    "ide,agent",
    [
        (None, "an AI agent (Claude Code)"),
        (None, "an AI agent"),
        ("cursor", "Cursor"),
        ("qwen", "Qwen"),
    ],
    ids=["CLAUDE.md", "AGENTS.md", ".cursorrules", "QWEN.md"],
)
def test_every_generated_body_carries_all_three(ide, agent, tier, tmp_path):
    """The ticket lists four outputs; the body is one per tier, so the defect was in all of them."""
    body = bt.build_full_body(
        "demo", ["python"], agent, ".claude", ide=ide, context_tier=tier, project_dir=str(tmp_path)
    )
    for name in _STORE_NAMES:
        assert f"**{name}**" in body, f"{name} missing from the {tier} body for {agent}"
    assert "memory add --global" in body
