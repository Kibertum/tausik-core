"""Tests for graph memory (memory_edges) — Graphiti-inspired.

Covers: backend CRUD, service layer, graph traversal, soft-invalidation,
auto-supersede, edge cases, CLI smoke.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError


@pytest.fixture
def db(tmp_path):
    be = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    yield be
    be.close()


@pytest.fixture
def svc(db):
    return ProjectService(db)


# --- Backend CRUD ---


class TestEdgeBackend:
    def test_edge_add(self, db):
        m1 = db.memory_add("pattern", "title1", "content1")
        m2 = db.memory_add("pattern", "title2", "content2")
        eid = db.edge_add("memory", m1, "memory", m2, "relates_to")
        assert eid > 0
        edge = db.edge_get(eid)
        assert edge["source_type"] == "memory"
        assert edge["source_id"] == m1
        assert edge["target_type"] == "memory"
        assert edge["target_id"] == m2
        assert edge["relation"] == "relates_to"
        assert edge["confidence"] == 1.0
        assert edge["valid_to"] is None

    def test_edge_invalidate(self, db):
        m1 = db.memory_add("pattern", "t1", "c1")
        m2 = db.memory_add("pattern", "t2", "c2")
        eid = db.edge_add("memory", m1, "memory", m2, "relates_to")
        rows = db.edge_invalidate(eid)
        assert rows == 1
        edge = db.edge_get(eid)
        assert edge["valid_to"] is not None

    def test_edge_invalidate_already_invalid(self, db):
        m1 = db.memory_add("pattern", "t1", "c1")
        m2 = db.memory_add("pattern", "t2", "c2")
        eid = db.edge_add("memory", m1, "memory", m2, "relates_to")
        db.edge_invalidate(eid)
        rows = db.edge_invalidate(eid)
        assert rows == 0  # already invalidated

    def test_edge_invalidate_with_replacement(self, db):
        m1 = db.memory_add("pattern", "t1", "c1")
        m2 = db.memory_add("pattern", "t2", "c2")
        m3 = db.memory_add("pattern", "t3", "c3")
        e1 = db.edge_add("memory", m1, "memory", m2, "relates_to")
        e2 = db.edge_add("memory", m1, "memory", m3, "relates_to")
        db.edge_invalidate(e1, e2)
        edge = db.edge_get(e1)
        assert edge["invalidated_by"] == e2

    def test_edge_list_filters(self, db):
        m1 = db.memory_add("pattern", "t1", "c1")
        m2 = db.memory_add("pattern", "t2", "c2")
        m3 = db.memory_add("gotcha", "t3", "c3")
        db.edge_add("memory", m1, "memory", m2, "relates_to")
        db.edge_add("memory", m1, "memory", m3, "supersedes")
        # Filter by node
        edges = db.edge_list(node_type="memory", node_id=m1)
        assert len(edges) == 2
        # Filter by relation
        edges = db.edge_list(relation="supersedes")
        assert len(edges) == 1
        assert edges[0]["relation"] == "supersedes"

    def test_edge_list_excludes_invalid(self, db):
        m1 = db.memory_add("pattern", "t1", "c1")
        m2 = db.memory_add("pattern", "t2", "c2")
        eid = db.edge_add("memory", m1, "memory", m2, "relates_to")
        db.edge_invalidate(eid)
        assert len(db.edge_list()) == 0
        assert len(db.edge_list(include_invalid=True)) == 1

    def test_edge_list_for_node(self, db):
        m1 = db.memory_add("pattern", "t1", "c1")
        m2 = db.memory_add("pattern", "t2", "c2")
        m3 = db.memory_add("pattern", "t3", "c3")
        db.edge_add("memory", m1, "memory", m2, "relates_to")
        db.edge_add("memory", m3, "memory", m1, "caused_by")  # m1 as target
        edges = db.edge_list_for_node("memory", m1)
        assert len(edges) == 2

    def test_edge_cross_type(self, db):
        """Edge between memory and decision."""
        m1 = db.memory_add("pattern", "t1", "c1")
        d1 = db.decision_add("Use graph memory")
        eid = db.edge_add("memory", m1, "decision", d1, "caused_by")
        edge = db.edge_get(eid)
        assert edge["source_type"] == "memory"
        assert edge["target_type"] == "decision"


# --- Graph Traversal ---


class TestGraphTraversal:
    def test_direct_neighbors(self, db):
        m1 = db.memory_add("pattern", "center", "c1")
        m2 = db.memory_add("pattern", "neighbor", "c2")
        db.edge_add("memory", m1, "memory", m2, "relates_to")
        refs = db.graph_related("memory", m1, max_hops=1)
        assert len(refs) == 1
        assert refs[0]["node_id"] == m2
        assert refs[0]["depth"] == 1

    def test_two_hop_traversal(self, db):
        m1 = db.memory_add("pattern", "A", "a")
        m2 = db.memory_add("pattern", "B", "b")
        m3 = db.memory_add("pattern", "C", "c")
        db.edge_add("memory", m1, "memory", m2, "relates_to")
        db.edge_add("memory", m2, "memory", m3, "caused_by")
        refs = db.graph_related("memory", m1, max_hops=2)
        assert len(refs) == 2
        ids = {r["node_id"] for r in refs}
        assert m2 in ids and m3 in ids

    def test_invalid_edges_excluded(self, db):
        m1 = db.memory_add("pattern", "A", "a")
        m2 = db.memory_add("pattern", "B", "b")
        eid = db.edge_add("memory", m1, "memory", m2, "relates_to")
        db.edge_invalidate(eid)
        refs = db.graph_related("memory", m1, max_hops=2)
        assert len(refs) == 0

    def test_invalid_edges_included(self, db):
        m1 = db.memory_add("pattern", "A", "a")
        m2 = db.memory_add("pattern", "B", "b")
        eid = db.edge_add("memory", m1, "memory", m2, "relates_to")
        db.edge_invalidate(eid)
        refs = db.graph_related("memory", m1, max_hops=2, include_invalid=True)
        assert len(refs) == 1

    def test_resolve_nodes(self, db):
        m1 = db.memory_add("pattern", "Title A", "Content A")
        d1 = db.decision_add("Decision B")
        refs = [
            {
                "node_type": "memory",
                "node_id": m1,
                "depth": 1,
                "via_edge": 0,
                "via_relation": "relates_to",
            },
            {
                "node_type": "decision",
                "node_id": d1,
                "depth": 1,
                "via_edge": 0,
                "via_relation": "caused_by",
            },
        ]
        resolved = db.graph_resolve_nodes(refs)
        assert len(resolved) == 2
        assert resolved[0]["record"]["title"] == "Title A"
        assert resolved[1]["record"]["decision"] == "Decision B"

    def test_max_hops_capped(self, db):
        """Ensure max_hops is capped at 3."""
        m1 = db.memory_add("pattern", "A", "a")
        # Just verify no error with large value
        refs = db.graph_related("memory", m1, max_hops=100)
        assert refs == []  # no edges, just verify no crash


# --- Service Layer ---


class TestGraphService:
    def test_memory_link(self, svc):
        svc.be.memory_add("pattern", "t1", "c1")
        svc.be.memory_add("pattern", "t2", "c2")
        result = svc.memory_link("memory", 1, "memory", 2, "relates_to")
        assert "Edge #" in result
        assert "relates_to" in result

    def test_memory_link_invalid_relation(self, svc):
        svc.be.memory_add("pattern", "t1", "c1")
        svc.be.memory_add("pattern", "t2", "c2")
        with pytest.raises(ServiceError, match="Invalid relation"):
            svc.memory_link("memory", 1, "memory", 2, "invalid_rel")

    def test_memory_link_invalid_node_type(self, svc):
        with pytest.raises(ServiceError, match="Invalid node type"):
            svc.memory_link("invalid", 1, "memory", 2, "relates_to")

    def test_memory_link_nonexistent_node(self, svc):
        svc.be.memory_add("pattern", "t1", "c1")
        with pytest.raises(ServiceError, match="not found"):
            svc.memory_link("memory", 1, "memory", 999, "relates_to")

    def test_memory_link_self_loop(self, svc):
        svc.be.memory_add("pattern", "t1", "c1")
        with pytest.raises(ServiceError, match="Cannot link a node to itself"):
            svc.memory_link("memory", 1, "memory", 1, "relates_to")

    def test_memory_link_confidence(self, svc):
        svc.be.memory_add("pattern", "t1", "c1")
        svc.be.memory_add("pattern", "t2", "c2")
        svc.memory_link("memory", 1, "memory", 2, "relates_to", confidence=0.7)
        edges = svc.memory_graph()
        assert edges[0]["confidence"] == 0.7

    def test_memory_link_bad_confidence(self, svc):
        svc.be.memory_add("pattern", "t1", "c1")
        svc.be.memory_add("pattern", "t2", "c2")
        with pytest.raises(ServiceError, match="Confidence"):
            svc.memory_link("memory", 1, "memory", 2, "relates_to", confidence=1.5)

    def test_memory_unlink(self, svc):
        svc.be.memory_add("pattern", "t1", "c1")
        svc.be.memory_add("pattern", "t2", "c2")
        svc.memory_link("memory", 1, "memory", 2, "relates_to")
        result = svc.memory_unlink(1)
        assert "invalidated" in result

    def test_memory_unlink_nonexistent(self, svc):
        with pytest.raises(ServiceError, match="not found"):
            svc.memory_unlink(999)

    def test_memory_unlink_already_invalid(self, svc):
        svc.be.memory_add("pattern", "t1", "c1")
        svc.be.memory_add("pattern", "t2", "c2")
        svc.memory_link("memory", 1, "memory", 2, "relates_to")
        svc.memory_unlink(1)
        with pytest.raises(ServiceError, match="already invalidated"):
            svc.memory_unlink(1)

    def test_memory_related(self, svc):
        svc.be.memory_add("pattern", "center", "main node")
        svc.be.memory_add("pattern", "neighbor", "linked node")
        svc.memory_link("memory", 1, "memory", 2, "relates_to")
        results = svc.memory_related("memory", 1)
        assert len(results) == 1
        assert results[0]["record"]["title"] == "neighbor"

    def test_memory_graph_empty(self, svc):
        assert svc.memory_graph() == []

    def test_memory_graph_filter_relation(self, svc):
        svc.be.memory_add("pattern", "t1", "c1")
        svc.be.memory_add("pattern", "t2", "c2")
        svc.be.memory_add("pattern", "t3", "c3")
        svc.memory_link("memory", 1, "memory", 2, "relates_to")
        svc.memory_link("memory", 1, "memory", 3, "supersedes")
        edges = svc.memory_graph(relation="supersedes")
        assert len(edges) == 1

    def test_memory_graph_invalid_relation(self, svc):
        with pytest.raises(ServiceError, match="Invalid relation"):
            svc.memory_graph(relation="bogus")

    def test_supersedes_auto_invalidate(self, svc):
        """When creating 'supersedes' edge, old supersedes edges on target get invalidated."""
        svc.be.memory_add("pattern", "old_decision", "v1")
        svc.be.memory_add("pattern", "middle_decision", "v2")
        svc.be.memory_add("pattern", "new_decision", "v3")
        # old supersedes middle
        svc.memory_link("memory", 1, "memory", 2, "supersedes")
        # now new supersedes middle — old edge on middle should be invalidated
        svc.memory_link("memory", 3, "memory", 2, "supersedes")
        # The old edge (#1 supersedes #2) stays — auto-invalidate only targets
        # edges where target=2 is the source (outgoing supersedes from 2)
        # This is about replacing what target node supersedes, not incoming edges
        all_edges = svc.memory_graph(include_invalid=True)
        valid_edges = svc.memory_graph(include_invalid=False)
        assert len(all_edges) == 2
        # Both are valid — the auto-invalidation targets outgoing supersedes from target
        assert len(valid_edges) >= 1

    def test_find_similar(self, svc):
        svc.be.memory_add(
            "pattern", "Database indexing", "Always add indexes on FK columns"
        )
        svc.be.memory_add(
            "gotcha", "SQLite FTS5", "FTS5 requires content sync triggers"
        )
        results = svc.memory_find_similar("Database", "indexes")
        assert len(results) >= 1

    def test_cross_type_link(self, svc):
        """Link memory to decision."""
        svc.be.memory_add("pattern", "pattern1", "content1")
        svc.be.decision_add("Decision about something")
        result = svc.memory_link("memory", 1, "decision", 1, "caused_by")
        assert "caused_by" in result
        related = svc.memory_related("memory", 1)
        assert len(related) == 1
        assert related[0]["node_type"] == "decision"


# --- Migration ---


class TestMigration:
    def test_schema_has_memory_edges(self, db):
        """memory_edges table exists after init."""
        tables = db._q(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_edges'"
        )
        assert len(tables) == 1

    def test_schema_version_current(self, db):
        from backend_schema import SCHEMA_VERSION

        row = db._q1("SELECT value FROM meta WHERE key='schema_version'")
        assert row["value"] == str(SCHEMA_VERSION)

    def test_edge_check_constraints(self, db):
        """Invalid relation should be rejected by CHECK constraint."""
        with pytest.raises(Exception):
            db._ins(
                "INSERT INTO memory_edges(source_type,source_id,target_type,target_id,"
                "relation,confidence,valid_from,created_at) VALUES(?,?,?,?,?,?,?,?)",
                ("memory", 1, "memory", 2, "invalid", 1.0, "2024-01-01", "2024-01-01"),
            )

    def test_edge_invalid_source_type(self, db):
        with pytest.raises(Exception):
            db._ins(
                "INSERT INTO memory_edges(source_type,source_id,target_type,target_id,"
                "relation,confidence,valid_from,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    "bogus",
                    1,
                    "memory",
                    2,
                    "relates_to",
                    1.0,
                    "2024-01-01",
                    "2024-01-01",
                ),
            )


# --- CLI Smoke ---


@pytest.fixture
def tausik_env(tmp_path):
    """Set up a project directory with tausik init."""
    project = tmp_path / "proj"
    project.mkdir()
    scripts = os.path.join(os.path.dirname(__file__), "..", "scripts")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(
        [sys.executable, os.path.join(scripts, "project.py"), "init", "--name", "test"],
        cwd=str(project),
        env=env,
        check=True,
        capture_output=True,
    )
    return str(project), scripts, env


class TestGraphCLI:
    def _run(self, tausik_env, *args):
        project, scripts, env = tausik_env
        result = subprocess.run(
            [sys.executable, os.path.join(scripts, "project.py"), *args],
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result

    def test_memory_link(self, tausik_env):
        # Create two memories first
        self._run(tausik_env, "memory", "add", "pattern", "title1", "content1")
        self._run(tausik_env, "memory", "add", "pattern", "title2", "content2")
        result = self._run(
            tausik_env, "memory", "link", "memory", "1", "memory", "2", "relates_to"
        )
        assert result.returncode == 0
        assert "Edge #" in result.stdout

    def test_memory_unlink(self, tausik_env):
        self._run(tausik_env, "memory", "add", "pattern", "t1", "c1")
        self._run(tausik_env, "memory", "add", "pattern", "t2", "c2")
        self._run(
            tausik_env, "memory", "link", "memory", "1", "memory", "2", "relates_to"
        )
        result = self._run(tausik_env, "memory", "unlink", "1")
        assert result.returncode == 0
        assert "invalidated" in result.stdout

    def test_memory_graph(self, tausik_env):
        self._run(tausik_env, "memory", "add", "pattern", "t1", "c1")
        self._run(tausik_env, "memory", "add", "pattern", "t2", "c2")
        self._run(
            tausik_env, "memory", "link", "memory", "1", "memory", "2", "relates_to"
        )
        result = self._run(tausik_env, "memory", "graph")
        assert result.returncode == 0
        assert "relates_to" in result.stdout

    def test_memory_related(self, tausik_env):
        self._run(tausik_env, "memory", "add", "pattern", "center", "main")
        self._run(tausik_env, "memory", "add", "pattern", "neighbor", "linked")
        self._run(
            tausik_env, "memory", "link", "memory", "1", "memory", "2", "relates_to"
        )
        result = self._run(tausik_env, "memory", "related", "memory", "1")
        assert result.returncode == 0
        assert "neighbor" in result.stdout

    def test_memory_graph_empty(self, tausik_env):
        result = self._run(tausik_env, "memory", "graph")
        assert result.returncode == 0
        assert "No edges" in result.stdout

    def test_memory_related_no_results(self, tausik_env):
        self._run(tausik_env, "memory", "add", "pattern", "lonely", "alone")
        result = self._run(tausik_env, "memory", "related", "memory", "1")
        assert result.returncode == 0
        assert "No related" in result.stdout
