"""graph-mermaid-render: deterministic DB → Mermaid flowchart of the memory graph."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from graph_mermaid import _label, _node_id, render_memory_graph  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "g.db")))
    yield s
    s.be.close()


def _seed(svc):
    a = svc.be.memory_add("pattern", "Alpha mem", "a", None, None)
    b = svc.be.memory_add("gotcha", "Beta mem", "b", None, None)
    d = svc.be.decision_add("Decision one line\nsecond line", None, None)
    svc.be.edge_add("memory", a, "memory", b, "relates_to")
    svc.be.edge_add("memory", a, "decision", d, "caused_by")
    return a, b, d


def test_empty_graph_is_valid_empty_mermaid(svc):
    assert render_memory_graph(svc) == "graph LR\n"


def test_render_is_deterministic(svc):
    _seed(svc)
    assert render_memory_graph(svc) == render_memory_graph(svc)


def test_render_has_header_nodes_and_sorted_edges(svc):
    _seed(svc)
    out = render_memory_graph(svc)
    assert out.startswith("graph LR\n")
    assert '"Alpha mem"' in out and '"Beta mem"' in out
    # decision label = first non-empty line only
    assert '"Decision one line"' in out
    # edges present, sorted by (source, relation, target)
    edge_lines = [ln for ln in out.splitlines() if "-->" in ln]
    assert edge_lines == sorted(edge_lines)
    assert any("|relates_to|" in ln for ln in edge_lines)
    assert any("|caused_by|" in ln for ln in edge_lines)


def test_only_edge_participating_nodes_included(svc):
    _seed(svc)
    svc.be.memory_add("context", "Lonely mem", "x", None, None)  # no edges
    out = render_memory_graph(svc)
    assert "Lonely mem" not in out  # isolated node omitted from the edge view


def test_node_id_sanitises_hyphens_and_digit_start():
    assert _node_id("m", "2026-review") == "m_2026_review"
    assert not _node_id("m", "2026-review").startswith("2")  # never digit-initial


def test_label_sanitises_mermaid_breaking_chars():
    # brackets/pipes/quotes/newlines must not survive to break the diagram
    dirty = 'Bug: [x] | "y" <z>\nsecond'
    clean = _label(dirty, "fallback")
    for ch in '[]|"<>':
        assert ch not in clean
    assert "\n" not in clean


def test_dangling_edge_skipped_not_crash(svc):
    a = svc.be.memory_add("pattern", "Aaa", "a", None, None)
    svc.be.edge_add("memory", a, "memory", 9999, "relates_to")  # target absent
    out = render_memory_graph(svc)  # must not raise
    assert out == "graph LR\n"  # unresolvable edge dropped → empty


def test_archived_memory_excluded(svc):
    a, b, d = _seed(svc)
    svc.be.memory_archive_ids([b])
    out = render_memory_graph(svc)
    assert "Beta mem" not in out  # archived node gone; its edge drops with it
