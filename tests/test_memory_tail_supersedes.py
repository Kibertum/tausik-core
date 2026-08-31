"""The memory tail must not print a retired entry beside the one that retired it.

memory-tail-shows-a-superseded-entry-next-to-its-replacement. Found in session
#191 by reading the dynamic block of this repository's own CLAUDE.md, which
carried two lines about one subject:

    - #441 ADR inventory recounted by machine: thirteen accepted, seven assessed
    - #432 ADR inventory: twelve accepted, three assessed

with `memory#441 --[supersedes]--> memory#432` (edge #5) in the database the
whole time. The tail is the first thing a fresh agent reads, and the expensive
outcome is not "reads the wrong number" but "believes the older one, because the
rest of the history repeats it" — measured: that is why
`four-accepted-adrs-were-never-assessed` treated four ADRs as unassessed instead
of ten.

The real pair is reproduced here by its TEXT rather than its ids (a temp
database numbers its own rows), and the two counts are kept verbatim so a reader
of this file meets the contradiction the way the agent met it.

One class per acceptance criterion:

  AC1/AC2  the retired entry is gone and its replacement says what it replaced
  AC3      the freed line goes to the next live entry — five slots, five facts
  AC5      every section, in BOTH renderers
  AC4      THE NEGATIVE: nothing without an incoming live edge may vanish
  AC6      a three-link chain prints only its head
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

from project_backend import SQLiteBackend  # noqa: E402
from service_knowledge_aggregates import (  # noqa: E402
    build_compact_memory_tail,
    build_memory_block,
)

# The two lines that stood next to each other in CLAUDE.md, kept verbatim.
NEW_COUNT = "Инвентарь ADR RENAR, пересчитанный машиной: принятых тринадцать, оценено семь"
OLD_COUNT = "Инвентарь ADR RENAR: принятых двенадцать, оценивали три"


@pytest.fixture
def be(tmp_path):
    return SQLiteBackend(str(tmp_path / "t.db"))


def _tail(backend) -> str:
    return "\n".join(build_compact_memory_tail(backend))


def _link(backend, newer: int, older: int) -> None:
    """`newer` supersedes `older` — the edge `memory link` writes."""
    backend.edge_add("memory", newer, "memory", older, "supersedes")


class TestTheRealPair:
    """AC1 + AC2 — the pair that was on screen, and the choice made about it."""

    def _pair(self, backend) -> tuple[int, int]:
        old = backend.memory_add("context", OLD_COUNT, "x")
        new = backend.memory_add("context", NEW_COUNT, "x")
        _link(backend, new, old)
        return old, new

    def test_retired_entry_is_not_printed_beside_its_replacement(self, be):
        old, _new = self._pair(be)
        out = _tail(be)
        assert "тринадцать" in out
        assert f"- #{old} " not in out
        assert "двенадцать" not in out

    def test_the_replacement_says_what_it_replaced(self, be):
        """AC2 — hidden, not marked; and the surviving line carries the fact.

        The choice is recorded in `entry_line`: marking the dead entry would
        spend one of five lines on knowledge already known to be wrong, while
        the suffix rides on a line that exists either way. What it must NOT be
        is silent — a vanished entry is indistinguishable from a lost one.
        """
        old, new = self._pair(be)
        out = _tail(be)
        assert f"- #{new} " in out
        assert f"(supersedes #{old})" in out

    def test_an_archived_replacement_gives_the_entry_back(self, be):
        """Liveness of the SOURCE is the condition, not the edge alone.

        A replacement that was itself archived leaves the subject unrepresented
        if the older entry stays hidden, so the older entry comes back.
        """
        old, new = self._pair(be)
        be.memory_archive_ids([new])
        out = _tail(be)
        assert f"- #{old} " in out

    def test_a_retracted_edge_stops_hiding(self, be):
        """`memory unlink` soft-invalidates; an invalid edge retires nothing."""
        old, new = self._pair(be)
        edge = be.edge_list(node_type="memory", node_id=new, relation="supersedes")[0]
        be.edge_invalidate(int(edge["id"]))
        assert f"- #{old} " in _tail(be)


class TestFreedLineIsRefilled:
    """AC3 — five slots must carry five LIVE facts, not four and a hole."""

    def test_next_live_entry_takes_the_freed_slot(self, be):
        ids = [be.memory_add("context", f"host-{i}", "x") for i in range(6)]
        # The newest supersedes the second-newest: without a refill the section
        # would print four of its five entries and silently shrink.
        _link(be, ids[5], ids[4])
        out = _tail(be)
        shown = [i for i in ids if f"- #{i} " in out]
        assert len(shown) == 5
        assert ids[4] not in shown
        assert ids[0] in shown  # the oldest one moved UP into the freed line

    def test_a_section_of_corrections_does_not_shrink_the_tail(self, be):
        """Three retired pairs still leave five live lines — the fetch widens."""
        ids = [be.memory_add("context", f"host-{i}", "x") for i in range(10)]
        for newer, older in ((9, 8), (7, 6), (5, 4)):
            _link(be, ids[newer], ids[older])
        out = _tail(be)
        shown = [i for i in ids if f"- #{i} " in out]
        assert len(shown) == 5
        assert not any(ids[i] in shown for i in (8, 6, 4))


class TestEverySection:
    """AC5 — one repaired section would trade the contradiction for a disagreement."""

    @pytest.mark.parametrize("kind", ["context", "convention", "dead_end"])
    def test_memory_sections_hide_the_retired_entry(self, be, kind):
        old = be.memory_add(kind, "old claim", "x")
        new = be.memory_add(kind, "new claim", "x")
        _link(be, new, old)
        out = _tail(be)
        assert f"- #{new} " in out
        assert f"- #{old} " not in out

    def test_decisions_hide_the_retired_entry(self, be):
        """A decision node is superseded by id in its OWN sequence."""
        old = be.decision_add("old ruling")
        new = be.decision_add("new ruling")
        be.edge_add("decision", new, "decision", old, "supersedes")
        out = _tail(be)
        assert f"- #{new} " in out
        assert f"- #{old} " not in out

    @pytest.mark.parametrize("kind", ["context", "convention", "dead_end"])
    def test_the_memory_block_hides_it_too(self, be, kind):
        """The OTHER renderer. These two drifted apart once over line
        flattening; the repair then was one shared function, and the same
        applies here — a block that still printed the pair would be the old
        defect surviving in the file the agent reads on `/start`."""
        old = be.memory_add(kind, "old claim", "x")
        new = be.memory_add(kind, "new claim", "x")
        _link(be, new, old)
        block = build_memory_block(be)
        assert f"- #{new} " in block
        assert f"- #{old} " not in block

    def test_the_memory_block_hides_a_retired_decision(self, be):
        old = be.decision_add("old ruling")
        new = be.decision_add("new ruling")
        be.edge_add("decision", new, "decision", old, "supersedes")
        block = build_memory_block(be)
        assert f"- #{new} " in block
        assert f"- #{old} " not in block


class TestNothingElseDisappears:
    """AC4 — the filter that eats unrelated entries is worse than the defect.

    Today the agent sees one line too many; a greedy filter would stop it seeing
    a line it needs, and would do so silently. Both halves are asserted: the
    linked pair loses its older half, two unlinked neighbours keep both.
    """

    def test_unlinked_neighbours_of_the_same_kind_both_survive(self, be):
        a = be.memory_add("context", "host A", "x")
        b = be.memory_add("context", "host B", "x")
        out = _tail(be)
        assert f"- #{a} " in out and f"- #{b} " in out

    def test_a_pair_linked_by_another_relation_both_survive(self, be):
        """`relates_to` is not a retirement. Only `supersedes` hides anything."""
        a = be.memory_add("context", "cause", "x")
        b = be.memory_add("context", "effect", "x")
        be.edge_add("memory", b, "memory", a, "relates_to")
        out = _tail(be)
        assert f"- #{a} " in out and f"- #{b} " in out

    def test_the_superseder_is_never_hidden_by_its_own_edge(self, be):
        """Direction matters: `edge_list` answers for both sides of a node."""
        old = be.memory_add("context", "old", "x")
        new = be.memory_add("context", "new", "x")
        _link(be, new, old)
        assert f"- #{new} " in _tail(be)

    def test_a_cross_type_edge_never_retires_its_own_source(self, be):
        """memory#1 supersedes decision#1: the ids collide, the nodes do not.

        Memories and decisions number themselves independently, so an id alone
        does not name a node. `edge_list` returns the edges on BOTH sides, so
        asking about memory#1 hands back this edge with memory#1 as its SOURCE —
        and an identity that compared only the id would read "target 1 is me"
        and hide the entry by the very edge that says it is the replacement.

        Both halves are asserted: the source survives, and the cross-type
        retirement it declares still happens.
        """
        d = be.decision_add("the ruling this memory replaces")
        m = be.memory_add("context", "the fact that replaced it", "x")
        assert m == d, "the fixture must actually collide, or it proves nothing"
        be.edge_add("memory", m, "decision", d, "supersedes")
        out = _tail(be)
        assert "the fact that replaced it" in out
        assert "the ruling this memory replaces" not in out

    def test_an_unlinked_project_renders_exactly_as_before(self, be):
        for i in range(3):
            be.memory_add("context", f"host-{i}", "x")
            be.memory_add("convention", f"rule-{i}", "x")
        out = _tail(be)
        assert out.count("- #") == 6


class TestChains:
    """AC6 — A supersedes B supersedes C prints only A, with no graph walk."""

    def test_only_the_head_of_a_three_link_chain_is_printed(self, be):
        c = be.memory_add("context", "claim C", "x")
        b = be.memory_add("context", "claim B", "x")
        a = be.memory_add("context", "claim A", "x")
        _link(be, b, c)
        _link(be, a, b)
        out = _tail(be)
        assert f"- #{a} " in out
        assert f"- #{b} " not in out
        assert f"- #{c} " not in out

    def test_a_chain_broken_by_archiving_its_head_shows_the_middle(self, be):
        """B is retired by A; archive A and B is the best knowledge left."""
        c = be.memory_add("context", "claim C", "x")
        b = be.memory_add("context", "claim B", "x")
        a = be.memory_add("context", "claim A", "x")
        _link(be, b, c)
        _link(be, a, b)
        be.memory_archive_ids([a])
        out = _tail(be)
        assert f"- #{b} " in out
        assert f"- #{c} " not in out


class TestDegradation:
    """A graph that cannot be read prints what the tail printed before."""

    def test_backend_without_edge_list_still_renders(self):
        class _NoGraph:
            def decision_list(self, n):
                return []

            def memory_list(self, kind, n, include_archived=False):
                return [{"id": 1, "title": "a fact", "type": kind}] if kind == "context" else []

        out = "\n".join(build_compact_memory_tail(_NoGraph()))
        assert "- #1 a fact" in out
