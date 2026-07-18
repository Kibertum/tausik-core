"""cq rows in a memory-search result must not masquerade as local memories.

Cross-project `cq` knowledge is appended to the same result list as this
project's own memories. It used to be emitted with ``id: 0`` — an address that
collides across every cq hit and points at a record that does not exist, so a
caller feeding a search result back into ``memory_show``/``memory_link`` got a
confusing miss instead of a clear "not addressable".
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from service_knowledge import CQ_SOURCE, build_cq_row

_UNIT = {
    "insight": {"summary": "prefer grep for short queries", "detail": "long detail"},
    "evidence": {"confidence": 0.85},
    "domain": ["retrieval", "agents"],
}


class TestCqRowShape:
    def test_row_carries_no_address(self):
        """Negative: a cq row must not be addressable. `id: 0` pointed at a
        record that does not exist and collided across every cq hit."""
        row = build_cq_row(_UNIT)
        assert row["id"] is None
        assert row["id"] != 0

    def test_provenance_is_explicit(self):
        row = build_cq_row(_UNIT)
        assert row["source"] == CQ_SOURCE

    def test_type_is_not_a_local_memory_type(self):
        """cq rows must stay distinguishable from this project's own memories —
        borrowing a valid local type would be worse than an out-of-list label."""
        from project_types import VALID_MEMORY_TYPES

        row = build_cq_row(_UNIT)
        assert row["type"] not in VALID_MEMORY_TYPES

    def test_confidence_and_domains_are_rendered(self):
        row = build_cq_row(_UNIT)
        assert "85%" in row["title"]
        assert row["tags"] == "retrieval,agents"
        assert row["content"] == "long detail"

    def test_missing_fields_do_not_raise(self):
        """Negative: a malformed unit from the network must degrade, not crash."""
        row = build_cq_row({})
        assert row["id"] is None
        assert row["content"] == ""

    def test_explicit_nulls_do_not_raise(self):
        """Negative: `"insight": null` is a common network shape and is NOT the
        same as an absent key — a .get() default only applies when the key is
        missing, so the old code handed None to the next .get() and raised."""
        row = build_cq_row({"insight": None, "evidence": None, "domain": None})
        assert row["id"] is None
        assert row["content"] == ""
        assert row["tags"] == ""

    def test_null_confidence_does_not_raise(self):
        row = build_cq_row({"insight": {"summary": "s"}, "evidence": {"confidence": None}})
        assert "0%" in row["title"]


class TestRenderersTolerateMissingAddress:
    def test_mcp_formatter_omits_address_for_cq(self):
        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
        )
        from handlers import _format_memory_hit

        line = _format_memory_hit(build_cq_row(_UNIT))
        assert "#None" not in line
        assert line.startswith("[cq]")

    def test_mcp_formatter_keeps_address_for_local(self):
        from handlers import _format_memory_hit

        local = {"id": 42, "type": "pattern", "title": "T", "content": "C"}
        assert _format_memory_hit(local).startswith("#42 [pattern]")
